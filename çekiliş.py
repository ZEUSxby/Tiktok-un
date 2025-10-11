import telebot
from telebot import types
import random
import time
import threading
import json
import os

# === AYARLAR ===
BOT_TOKEN = "8287112229:AAFdG513eap1ueLyeNkTqcFKVDAt11Hsmcw"
KANAL_ADI = "@ByzeusxToolmain"
ADMIN_IDS = [7823668175, 7038895537]

bot = telebot.TeleBot(BOT_TOKEN)

# === VERİ VE DEĞİŞKENLER ===
cekilisler = {}  # {cekilis_id: {"katilanlar": [], "mesaj_id": int, "admin_msg_id": int}}
DATA_FILE = "cekilisler.json"

def kaydet_veri():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cekilisler, f, ensure_ascii=False, indent=2)

def yukle_veri():
    global cekilisler
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            cekilisler = json.load(f)

# === ADMIN KONTROL ===
def admin_only(func):
    def wrapper(message):
        if message.from_user.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, "🚫 Bu komut sadece adminler için.")
            return
        func(message)
    return wrapper

# === DM İÇİN ANA BUTONLAR ===
def admin_inline_markup(cekilis_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if cekilis_id:
        katilan_btn = types.InlineKeyboardButton("🎁 Katılımcılar", callback_data=f"katilan_{cekilis_id}")
        bitir_btn = types.InlineKeyboardButton("🛑 Çekilişi Bitir", callback_data=f"bitir_{cekilis_id}")
        aktif_btn = types.InlineKeyboardButton("🟢 Aktif Çekiliş Var mı", callback_data=f"aktif_{cekilis_id}")
        markup.add(katilan_btn, bitir_btn, aktif_btn)
    else:
        baslat_btn = types.InlineKeyboardButton("🚀 Çekiliş Başlat", callback_data="baslat")
        markup.add(baslat_btn)
    return markup

# === /start ===
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "🚫 Bu bot sadece adminler için.")
        return
    msg = bot.send_message(
        message.chat.id,
        "🎉 Hoş geldin! Admin paneli aşağıda:",
        reply_markup=admin_inline_markup()
    )
    # Kaydet admin mesaj id (sadece tek admin DM mesajı)
    # Eğer çoklu admin varsa bunu ayrı tutabilirsin
    bot.chat_data = {message.from_user.id: msg.message_id}

# === CALLBACK İŞLEMLERİ ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    # Baslat çekiliş
    if call.data == "baslat":
        cekilis_id = str(time.time())
        # Kanal mesajı
        markup = types.InlineKeyboardMarkup()
        katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data=f"katil_{cekilis_id}")
        markup.add(katil_btn)
        msg = bot.send_message(
            KANAL_ADI,
            f"🎉 Yeni çekiliş başladı!\n👥 Katılan: 0",
            reply_markup=markup
        )
        # Kaydet çekiliş
        cekilisler[cekilis_id] = {
            "katilanlar": [],
            "mesaj_id": msg.message_id,
            "admin_msg_id": bot.chat_data.get(user_id)
        }
        kaydet_veri()
        bot.answer_callback_query(call.id, "✅ Çekiliş başlatıldı!")
        # Admin DM mesajını güncelle
        guncelle_admin_msg(user_id)
        return

    # Katılımcıları göster
    elif call.data.startswith("katilan_"):
        cekilis_id = call.data.split("_")[1]
        cekilis = cekilisler.get(cekilis_id)
        if not cekilis:
            bot.answer_callback_query(call.id, "⚠️ Çekiliş bulunamadı.")
            return
        katilanlar = cekilis["katilanlar"]
        text = "🎁 Katılımcılar:\n" + ("\n".join(katilanlar) if katilanlar else "Henüz yok")
        bot.edit_message_text(text, chat_id=chat_id, message_id=cekilis["admin_msg_id"], reply_markup=admin_inline_markup(cekilis_id))
        bot.answer_callback_query(call.id)

    # Aktif çekiliş var mı
    elif call.data.startswith("aktif_"):
        cekilis_id = call.data.split("_")[1]
        cekilis = cekilisler.get(cekilis_id)
        if not cekilis:
            bot.answer_callback_query(call.id, "⚠️ Çekiliş bulunamadı.")
            return
        count = len(cekilis["katilanlar"])
        text = f"🟢 Aktif çekiliş! Katılan kişi sayısı: {count}"
        bot.edit_message_text(text, chat_id=chat_id, message_id=cekilis["admin_msg_id"], reply_markup=admin_inline_markup(cekilis_id))
        bot.answer_callback_query(call.id)

    # Çekilişi bitir
    elif call.data.startswith("bitir_"):
        cekilis_id = call.data.split("_")[1]
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "🚫 Sadece admin bitirebilir.")
            return
        bitir_cekilis(cekilis_id)
        bot.answer_callback_query(call.id, "🛑 Çekiliş bitirildi!")
        guncelle_admin_msg(user_id)

    # Katıl butonu (kanal)
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

# === ÇEKİLİŞ MESAJI GÜNCELLE ===
def guncelle_cekilis_mesaj(cekilis_id):
    cekilis = cekilisler.get(cekilis_id)
    if not cekilis:
        return
    text = f"🎉 Yeni çekiliş!\n👥 Katılan: {len(cekilis['katilanlar'])}"
    markup = types.InlineKeyboardMarkup()
    katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data=f"katil_{cekilis_id}")
    markup.add(katil_btn)
    try:
        bot.edit_message_text(text, chat_id=KANAL_ADI, message_id=cekilis["mesaj_id"], reply_markup=markup)
    except Exception as e:
        print("Güncelleme hatası:", e)

# === ADMIN DM MESAJI GÜNCELLE ===
def guncelle_admin_msg(user_id):
    text = "🎛️ Admin Paneli\nAktif Çekilişler:\n"
    for cid, cekilis in cekilisler.items():
        text += f"ID: {cid} | Katılan: {len(cekilis['katilanlar'])}\n"
    msg_id = bot.chat_data.get(user_id)
    if msg_id:
        bot.edit_message_text(text, chat_id=user_id, message_id=msg_id, reply_markup=admin_inline_markup(list(cekilisler.keys())[0] if cekilisler else None))

# === ÇEKİLİŞİ BİTİR ===
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

# === BOT BAŞLANGICI ===
yukle_veri()
print("🤖 Bot aktif (tüm admin kontrolleri DM'de, mesaj güncelleniyor)!")
bot.polling(none_stop=True)