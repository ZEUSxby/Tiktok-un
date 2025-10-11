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


bot = telebot.TeleBot(BOT_TOKEN, threaded=True, skip_pending=True, parse_mode="Markdown")

# === DEĞİŞKENLER ===
cekilis_aktif = False
katilanlar = []
cekilis_mesaj_id = None
cekilis_chat_id = None
cekilis_sure = None
sure_thread = None

# === ADMIN KONTROL ===
def admin_only(func):
    def wrapper(message):
        if message.from_user.id not in ADMIN_IDS:
            return
        func(message)
    return wrapper

# === ANA MENÜ ===
def ana_menu():
    markup = types.InlineKeyboardMarkup()
    baslat_btn = types.InlineKeyboardButton("🚀 Çekiliş Başlat", callback_data="baslat")
    markup.add(baslat_btn)
    return markup

# === /start KOMUTU ===
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "🎉 Aşağıdan seçim yapabilirsiniz:", reply_markup=ana_menu())

# === ÇEKİLİŞ BAŞLAT CALLBACK ===
@bot.callback_query_handler(func=lambda call: call.data == "baslat")
def baslat_callback(call):
    global cekilis_aktif, katilanlar, cekilis_mesaj_id, cekilis_chat_id, cekilis_sure, sure_thread

    if cekilis_aktif:
        bot.answer_callback_query(call.id, "⚠️ Zaten aktif bir çekiliş var!")
        return

    cekilis_aktif = True
    katilanlar = []
    cekilis_chat_id = call.message.chat.id

    # Süre ve bitirme tuşları
    markup = types.InlineKeyboardMarkup(row_width=3)
    katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data="katil")
    bitir_btn = types.InlineKeyboardButton("🛑 Çekilişi Bitir", callback_data="bitir")
    sure_btn = types.InlineKeyboardButton("⏱️ Süre Seç (Opsiyonel)", callback_data="sure")
    markup.add(katil_btn, bitir_btn, sure_btn)

    msg = bot.send_message(cekilis_chat_id,
        f"🎉 Çekiliş başladı!\n👥 Katılan: 0\nKatılanlar: -",
        reply_markup=markup
    )
    cekilis_mesaj_id = msg.message_id
    bot.answer_callback_query(call.id, "✅ Çekiliş başlatıldı!")

# === CALLBACKLAR ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global katilanlar, cekilis_aktif, cekilis_sure, sure_thread

    if call.data == "katil":
        if not cekilis_aktif:
            bot.answer_callback_query(call.id, "⚠️ Şu anda aktif çekiliş yok.")
            return
        user = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
        if user in katilanlar:
            bot.answer_callback_query(call.id, "Zaten katıldın 🎁")
        else:
            katilanlar.append(user)
            bot.answer_callback_query(call.id, "✅ Katıldın!")
            guncelle_mesaj()

    elif call.data == "bitir":
        bitir_cekilis()

    elif call.data == "sure":
        bot.answer_callback_query(call.id, "⌛ Süreyi dakika olarak yaz (örn: 30)")

        def sure_iste(message):
            global cekilis_sure, sure_thread
            try:
                cekilis_sure = int(message.text)
                bot.send_message(cekilis_chat_id, f"⏱️ Çekiliş {cekilis_sure} dakika sonra otomatik bitecek.")
                sure_thread = threading.Thread(target=sure_thread_func, daemon=True)
                sure_thread.start()
            except:
                bot.send_message(cekilis_chat_id, "❌ Geçerli sayı girin.")
        bot.register_next_step_handler_by_chat_id(cekilis_chat_id, sure_iste)

# === SÜRE THREAD ===
def sure_thread_func():
    global cekilis_sure
    time.sleep(cekilis_sure * 60)
    if cekilis_aktif:
        bitir_cekilis()

# === MESAJ GÜNCELLE ===
def guncelle_mesaj():
    try:
        bot.edit_message_text(
            f"🎉 Çekiliş başladı!\n👥 Katılan: {len(katilanlar)}\nKatılanlar: {', '.join(katilanlar) if katilanlar else '-'}",
            chat_id=cekilis_chat_id,
            message_id=cekilis_mesaj_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🎁 Katıl", callback_data="katil"),
                types.InlineKeyboardButton("🛑 Çekilişi Bitir", callback_data="bitir"),
                types.InlineKeyboardButton("⏱️ Süre Seç (Opsiyonel)", callback_data="sure")
            )
        )
    except Exception as e:
        print("Mesaj güncelleme hatası:", e)

# === ÇEKİLİŞİ BİTİR ===
def bitir_cekilis():
    global cekilis_aktif
    if not cekilis_aktif:
        return
    cekilis_aktif = False
    if katilanlar:
        kazanan = random.choice(katilanlar)
        bot.edit_message_text(f"🎉 Çekiliş sona erdi!\n🏆 Kazanan: {kazanan}",
                              chat_id=cekilis_chat_id, message_id=cekilis_mesaj_id)
    else:
        bot.edit_message_text("⚠️ Çekiliş sona erdi. Katılan olmadı.",
                              chat_id=cekilis_chat_id, message_id=cekilis_mesaj_id)

# === BOTU ÇALIŞTIR ===
print("🤖 Bot aktif! Admin DM üzerinden yönetilebilir ve mesaj sürekli güncellenir.")
bot.infinity_polling(timeout=20, long_polling_timeout=20)