import telebot
from telebot import types
import random
import time
import threading
import json
import os

# ================== AYARLAR ==================
BOT_TOKEN = "8180247520:AAFw-UVXLjO5S_YP8vJQFOIYWPHyGczjy2g"
KANAL_ADI = "@ByzeusxToolmain"
ADMIN_IDS = [7823668175, 7038895537]

bot = telebot.TeleBot(BOT_TOKEN)

# ================== VERİ VE DEĞİŞKENLER ==================
cekilisler = {}  # {cekilis_id: {"katilanlar": [], "mesaj_id": int, "admin_msg_id": int, "sure": None}}
DATA_FILE = "cekilisler.json"

def kaydet_veri():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cekilisler, f, ensure_ascii=False, indent=2)

def yukle_veri():
    global cekilisler
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            cekilisler = json.load(f)

# ================== ADMIN KONTROL ==================
def admin_only(func):
    def wrapper(message):
        if message.from_user.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, "🚫 Bu komut sadece adminler için.")
            return
        func(message)
    return wrapper

# ================== ADMIN DM İÇİN MARKUP ==================
def admin_inline_markup(cekilis_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if cekilis_id:
        # Çekiliş başladıktan sonra
        sure_btn = types.InlineKeyboardButton("⏱️ Süre Seç (Opsiyonel)", callback_data=f"sure_{cekilis_id}")
        katilim_btn = types.InlineKeyboardButton("👥 Katılımcı Sayısı", callback_data=f"say_{cekilis_id}")
        bitir_btn = types.InlineKeyboardButton("🛑 Çekilişi Bitir", callback_data=f"bitir_{cekilis_id}")
        markup.add(bitir_btn, sure_btn, katilim_btn)
    else:
        # Başlangıçta sadece başlat
        baslat_btn = types.InlineKeyboardButton("🚀 ÇEKİLİŞ BAŞLAT", callback_data="baslat")
        markup.add(baslat_btn)
    return markup

# ================== /START ==================
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "🚫 Bu bot sadece adminler için.")
        return
    msg = bot.send_message(
        message.chat.id,
        "🎉 Admin Paneli\nAşağıdan seçim yapabilirsiniz:",
        reply_markup=admin_inline_markup()
    )
    # Admin mesaj id kaydı
    bot.chat_data = {message.from_user.id: msg.message_id}

# ================== CALLBACK İŞLEMLERİ ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    # ÇEKİLİŞ BAŞLAT
    if call.data == "baslat":
        cekilis_id = str(time.time())
        markup = types.InlineKeyboardMarkup()
        katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data=f"katil_{cekilis_id}")
        markup.add(katil_btn)

        # Kanal mesajı
        msg = bot.send_message(
            KANAL_ADI,
            f"🎉 Çekiliş başladı!\n👥 Katılan: 0",
            reply_markup=markup
        )

        # Çekiliş kaydı
        cekilisler[cekilis_id] = {
            "katilanlar": [],
            "mesaj_id": msg.message_id,
            "admin_msg_id": bot.chat_data.get(user_id),
            "sure": None
        }
        kaydet_veri()
        bot.answer_callback_query(call.id, "✅ Çekiliş başlatıldı!")

        # Admin mesajını güncelle
        guncelle_admin_msg(user_id, cekilis_id)
        return

    # ÇEKİLİŞİ BİTİR
    elif call.data.startswith("bitir_"):
        cekilis_id = call.data.split("_")[1]
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "🚫 Sadece admin bitirebilir.")
            return
        bitir_cekilis(cekilis_id)
        bot.answer_callback_query(call.id, "🛑 Çekiliş bitirildi!")
        guncelle_admin_msg(user_id)

    # Katılımcı sayısı göster
    elif call.data.startswith("say_"):
        cekilis_id = call.data.split("_")[1]
        cekilis = cekilisler.get(cekilis_id)
        if not cekilis:
            bot.answer_callback_query(call.id, "⚠️ Çekiliş bulunamadı.")
            return
        text = f"👥 Katılımcılar: {len(cekilis['katilanlar'])}\n" + "\n".join(cekilis['katilanlar'])
        bot.edit_message_text(text, chat_id=chat_id, message_id=cekilis["admin_msg_id"], reply_markup=admin_inline_markup(cekilis_id))
        bot.answer_callback_query(call.id)

    # Süre seç (opsiyonel)
    elif call.data.startswith("sure_"):
        cekilis_id = call.data.split("_")[1]
        bot.send_message(chat_id, "⏱️ Süreyi dakika olarak girin (opsiyonel, boş geçebilirsiniz):")
        bot.register_next_step_handler_by_chat_id(chat_id, sure_ayarla, cekilis_id)

    # Kanalda katıl butonu
    elif call.data.startswith("katil_"):
        cekilis_id = call.data.split("_")[1]
        cekilis = cekilisler.get(cekilis_id)
        if not cekilis:
            bot.answer_callback_query(call.id, "⚠️ Çekiliş sona ermiş.")
            return
        user = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
        if user in cekilis["katilanlar"]:
            bot.answer_callback_query(call.id, "Zaten katıldın 🎁")
        else:
            cekilis["katilanlar"].append(user)
            kaydet_veri()
            bot.answer_callback_query(call.id, "✅ Katıldın!")
            guncelle_cekilis_mesaj(cekilis_id)

# ================== SÜRE AYARLAMA ==================
def sure_ayarla(message, cekilis_id):
    try:
        sure = int(message.text)
        cekilisler[cekilis_id]["sure"] = sure
        kaydet_veri()
        bot.send_message(message.chat.id, f"⏱️ Süre {sure} dakika olarak ayarlandı.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Geçerli bir sayı girilmedi, süre opsiyonel olarak ayarlanmadı.")

# ================== KANAL MESAJINI GÜNCELLE ==================
def guncelle_cekilis_mesaj(cekilis_id):
    cekilis = cekilisler.get(cekilis_id)
    if not cekilis:
        return
    text = f"🎉 Çekiliş başladı!\n👥 Katılan: {len(cekilis['katilanlar'])}"
    markup = types.InlineKeyboardMarkup()
    katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data=f"katil_{cekilis_id}")
    markup.add(katil_btn)
    try:
        bot.edit_message_text(text, chat_id=KANAL_ADI, message_id=cekilis["mesaj_id"], reply_markup=markup)
    except Exception as e:
        print("Güncelleme hatası:", e)

# ================== ADMIN DM MESAJINI GÜNCELLE ==================
def guncelle_admin_msg(user_id, cekilis_id=None):
    text = "🎛️ Admin Paneli\n"
    if cekilis_id:
        cekilis = cekilisler.get(cekilis_id)
        if cekilis:
            text += f"ÇEKİLİŞ BAŞLADI\nKatılımcılar: {len(cekilis['katilanlar'])}\n"
            text += "\n".join(cekilis['katilanlar'])
    msg_id = bot.chat_data.get(user_id)
    if msg_id:
        bot.edit_message_text(text, chat_id=user_id, message_id=msg_id, reply_markup=admin_inline_markup(cekilis_id))

# ================== ÇEKİLİŞİ BİTİR ==================
def bitir_cekilis(cekilis_id):
    cekilis = cekilisler.pop(cekilis_id, None)
    if not cekilis:
        return
    kazanan = random.choice(cekilis["katilanlar"]) if cekilis["katilanlar"] else "Kimse yok 😅"
    try:
        bot.edit_message_text(f"🎉 Çekiliş sona erdi!\n🏆 Kazanan: {kazanan}", chat_id=KANAL_ADI, message_id=cekilis["mesaj_id"])
    except Exception as e:
        print("Bitirme hatası:", e)
    kaydet_veri()

# ================== BOT BAŞLANGICI ==================
yukle_veri()
print("🤖 Bot aktif! Admin DM üzerinden yönetilebilir ve mesaj sürekli güncellenir.")
bot.polling(none_stop=True)