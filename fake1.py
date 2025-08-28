import requests, random, string, json, os
from datetime import datetime
import telebot
from telebot import types

TOKEN = "7222141307:AAFWQb9i1z-zrm2NzSP-f8KQqVsz0p3HPaY"  # Telegram bot tokeni
bot = telebot.TeleBot(TOKEN)

USER_FILE = "user_data.json"
LOG_FILE = "bot.log"

# RAM’de tutulan veriler
user_data = {}       # chat_id -> [ {email, password, token, sent_ids}, ... ]
selected_mail = {}   # chat_id -> index
awaiting_input = {}  # chat_id -> True (kendi mail girişi bekleniyor)

# ---------------- LOG ----------------
def write_log(user_id, action, mail=None, message_count=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {user_id} | {action}"
    if mail:
        line += f" | {mail}"
    if message_count is not None:
        line += f" | {message_count} mesaj"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ---------------- JSON KAYIT ----------------
def save_user_data():
    data = {"user_data": user_data, "selected_mail": selected_mail}
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_user_data():
    global user_data, selected_mail
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_data = data.get("user_data", {})
            selected_mail = data.get("selected_mail", {})

# ---------------- MAIL FONKSİYONLARI ----------------
def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def create_temp_email(local=None):
    try:
        domains = requests.get("https://api.mail.tm/domains", timeout=10).json()["hydra:member"]
        domain = domains[0]["domain"]
        if local is None:
            local = random_string()
        email = f"{local}@{domain}"
        password = random_string(12)
        r = requests.post("https://api.mail.tm/accounts", json={"address": email, "password": password}, timeout=10)
        if r.status_code == 201:
            token_r = requests.post("https://api.mail.tm/token", json={"address": email, "password": password}, timeout=10)
            if token_r.status_code == 200:
                token = token_r.json()["token"]
                return {"email": email, "password": password, "token": token, "sent_ids": []}
        write_log("SYSTEM", f"Mail oluşturulamadı: {r.status_code} {r.text}")
    except Exception as e:
        write_log("SYSTEM", f"Mail oluşturma hatası: {e}")
    return None

def get_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get("https://api.mail.tm/messages", headers=headers, timeout=10)
    if r.status_code == 200:
        return r.json()["hydra:member"]
    return []

def read_message(token, message_id):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"https://api.mail.tm/messages/{message_id}", headers=headers, timeout=10)
    if r.status_code == 200:
        return r.json()
    return {}

def send_first_10(chat_id, content):
    body = content.get("text", "") or str(content.get("html", ""))
    lines = body.splitlines()
    first10 = "\n".join(lines[:10])
    bot.send_message(chat_id, f"✉️ {content.get('subject','(Konu Yok)')}\n\n{first10}")

# ---------------- MENÜ ----------------
def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📩 Yeni Mail Al", callback_data="newmail"),
        types.InlineKeyboardButton("📂 Mail Seç", callback_data="choosemail"),
        types.InlineKeyboardButton("🔄 Posta Kutusunu Yenile", callback_data="refresh")
    )
    return markup

def newmail_options(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Rastgele Mail Oluştur", callback_data="randommail"),
        types.InlineKeyboardButton("✏️ Kendi Mailimi Gireceğim", callback_data="ownmail")
    )
    bot.send_message(chat_id, "Yeni mail almak istiyor musun?", reply_markup=markup)

# ---------------- BOT HANDLER ----------------
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = str(message.chat.id)
    if chat_id not in user_data:
        user_data[chat_id] = []
    bot.send_message(chat_id, "📬 Menüden seçim yap:", reply_markup=main_menu())
    write_log(chat_id, "Bot Başlatıldı")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = str(call.message.chat.id)

    if call.data == "newmail":
        newmail_options(chat_id)

    elif call.data == "randommail":
        data = create_temp_email()
        if data:
            if chat_id not in user_data:
                user_data[chat_id] = []
            user_data[chat_id].append(data)
            selected_mail[chat_id] = len(user_data[chat_id]) - 1
            save_user_data()
            bot.send_message(chat_id, f"✅ Yeni Mail Alındı: {data['email']}", reply_markup=main_menu())
            write_log(chat_id, "Yeni Mail Alındı (Rastgele)", data['email'])
        else:
            bot.send_message(chat_id, "❌ Mail oluşturulamadı.", reply_markup=main_menu())
            write_log(chat_id, "Yeni Mail Alınamadı (Rastgele)")

    elif call.data == "ownmail":
        awaiting_input[chat_id] = True
        bot.send_message(chat_id, "Lütfen mail adresinin '@' öncesini yaz, domain otomatik eklenecek.\nSadece a-z, 0-9, ., _, - karakterlerini kullanabilirsin.")

    elif call.data == "choosemail":
        if chat_id not in user_data or not user_data[chat_id]:
            bot.send_message(chat_id, "📭 Henüz hiç mailin yok.", reply_markup=main_menu())
            write_log(chat_id, "Mail Seçme İsteği Ama Mail Yok")
            return
        markup = types.InlineKeyboardMarkup()
        for idx, acc in enumerate(user_data[chat_id]):
            text = acc["email"]
            if chat_id in selected_mail and selected_mail[chat_id] == idx:
                text = f"✅ {text}"
            markup.add(types.InlineKeyboardButton(text, callback_data=f"sel_{idx}"))
        bot.send_message(chat_id, "Hangi maili kullanmak istersin?", reply_markup=markup)
        write_log(chat_id, "Mail Seçim Menüsü Açıldı")

    elif call.data.startswith("sel_"):
        idx = int(call.data.split("_")[1])
        selected_mail[chat_id] = idx
        save_user_data()
        bot.send_message(chat_id, f"📌 Seçilen mail: {user_data[chat_id][idx]['email']}", reply_markup=main_menu())
        write_log(chat_id, "Mail Seçildi", user_data[chat_id][idx]['email'])

    elif call.data == "refresh":
        if chat_id not in selected_mail:
            bot.send_message(chat_id, "⚠️ Önce bir mail seçmelisin!", reply_markup=main_menu())
            write_log(chat_id, "Posta Kutusu Yenileme İsteği Ama Mail Seçilmemiş")
            return

        idx = selected_mail[chat_id]
        data = user_data[chat_id][idx]
        if "sent_ids" not in data:
            data["sent_ids"] = []

        messages = get_messages(data["token"])
        new_count = 0

        for msg in messages:
            if msg["id"] not in data["sent_ids"]:
                content = read_message(data["token"], msg["id"])
                send_first_10(chat_id, content)
                data["sent_ids"].append(msg["id"])
                new_count += 1

        save_user_data()

        if new_count == 0:
            bot.send_message(chat_id, "📭 Yeni mail yok.", reply_markup=main_menu())
        else:
            bot.send_message(chat_id, f"✅ {new_count} yeni mail gönderildi.", reply_markup=main_menu())

        write_log(chat_id, "Posta Kutusu Yenilendi", data['email'], new_count)

    bot.answer_callback_query(call.id)

# ---------------- MESAJ YAKALAMA ----------------
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = str(message.chat.id)
    if chat_id in awaiting_input and awaiting_input[chat_id]:
        local = message.text.strip().lower()
        local = "".join(c for c in local if c.isalnum() or c in ['.', '_', '-'])
        local = local[:32]

        if len(local) == 0:
            bot.send_message(chat_id, "❌ Geçersiz giriş. Lütfen sadece a-z, 0-9, ., _, - karakterlerini kullan ve boş bırakma.")
            return

        data = create_temp_email(local)
        if data:
            if chat_id not in user_data:
                user_data[chat_id] = []
            user_data[chat_id].append(data)
            selected_mail[chat_id] = len(user_data[chat_id]) - 1
            save_user_data()
            bot.send_message(chat_id, f"✅ Mail oluşturuldu: {data['email']}", reply_markup=main_menu())
            write_log
            write_log(chat_id, "Yeni Mail Alındı (Kullanıcı Girişi)", data['email'])
        else:
            bot.send_message(chat_id, "❌ Mail oluşturulamadı. Başka bir isim deneyin.", reply_markup=main_menu())
            write_log(chat_id, "Yeni Mail Alınamadı (Kullanıcı Girişi)")

        awaiting_input[chat_id] = False

# ---------------- BOT BAŞLAT ----------------
if __name__ == "__main__":
    load_user_data()
    print("🤖 Bot çalışıyor...")
    bot.infinity_polling(skip_pending=True)
