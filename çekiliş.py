import telebot
from telebot import types
import random

# === AYARLAR ===
BOT_TOKEN = "8180247520:AAFw-UVXLjO5S_YP8vJQFOIYWPHyGczjy2g"
KANAL_ADI = "@ByzeusxToolmain"

# 🔹 Birden fazla admin ID'si
ADMIN_IDS = [7823668175, 7038895537]  # kendi ve 2. adminin ID’sini yaz buraya

bot = telebot.TeleBot(BOT_TOKEN)

# === DEĞİŞKENLER ===
cekilis_aktif = False
katilanlar = []
cekilis_mesaj_id = None
katilim_limiti = None


# === ANA MENÜ ===
def ana_menu():
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    menu.add("🚀 Çekiliş Başlat", "🛑 Çekiliş Bitir",
             "🎁 Katılımcılar", "🟢 Aktif Çekiliş Var mı",
             "⏱️ Otomatik Bitirme")
    return menu


# === SADECE ADMIN FONKSIYONU ===
def admin_only(func):
    def wrapper(message):
        if message.from_user.id not in ADMIN_IDS:
            return
        func(message)
    return wrapper


# === /start KOMUTU ===
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "🚫 Bu bot sadece yöneticiler tarafından kullanılabilir.")
        return

    user_adi = message.from_user.first_name
    text = f"🎉 Hoş geldin {user_adi}!\n\nAşağıdaki menüden seçim yap 👇"
    bot.send_message(message.chat.id, text, reply_markup=ana_menu())


# === MENÜ KOMUTLARI ===
@bot.message_handler(func=lambda m: m.text == "🟢 Aktif Çekiliş Var mı")
@admin_only
def aktif_varmi(message):
    if cekilis_aktif:
        bot.send_message(message.chat.id, f"🟢 Evet! Şu anda {len(katilanlar)} kişi katıldı.")
    else:
        bot.send_message(message.chat.id, "🔴 Şu anda aktif bir çekiliş yok.")


@bot.message_handler(func=lambda m: m.text == "🎁 Katılımcılar")
@admin_only
def katilanlari_goster(message):
    if not katilanlar:
        bot.send_message(message.chat.id, "Henüz kimse katılmadı 😅")
    else:
        liste = "\n".join(katilanlar)
        bot.send_message(message.chat.id, f"🎁 Katılımcılar ({len(katilanlar)} kişi):\n{liste}")


@bot.message_handler(func=lambda m: m.text == "⏱️ Otomatik Bitirme")
@admin_only
def otomatik_bitir_ayarla(message):
    bot.send_message(message.chat.id, "Kaç kişi olunca çekiliş otomatik bitsin?")
    bot.register_next_step_handler(message, otomatik_belirle)


def otomatik_belirle(message):
    global katilim_limiti
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        katilim_limiti = int(message.text)
        bot.send_message(message.chat.id, f"✅ Limit {katilim_limiti} kişi olarak ayarlandı.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Geçerli bir sayı girmen lazım.")


@bot.message_handler(func=lambda m: m.text == "🚀 Çekiliş Başlat")
@admin_only
def cekilis_baslat(message):
    global cekilis_aktif, katilanlar, cekilis_mesaj_id
    if cekilis_aktif:
        bot.send_message(message.chat.id, "⚠️ Zaten aktif bir çekiliş var!")
        return

    cekilis_aktif = True
    katilanlar = []

    markup = types.InlineKeyboardMarkup()
    katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data="katil")
    markup.add(katil_btn)

    msg = bot.send_message(
        KANAL_ADI,
        "🎉 **Yeni çekiliş başladı!**\nKatılmak için aşağıdaki butona tıkla 👇\n👥 Katılan: 0 kişi",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    cekilis_mesaj_id = msg.message_id
    bot.send_message(message.chat.id, "✅ Çekiliş kanalda başlatıldı!")


@bot.message_handler(func=lambda m: m.text == "🛑 Çekiliş Bitir")
@admin_only
def cekilis_bitir(message):
    if not cekilis_aktif:
        bot.send_message(message.chat.id, "Aktif çekiliş yok 😅")
        return
    bitir_cekilis(message.chat.id)


# === KATIL BUTONU ===
@bot.callback_query_handler(func=lambda call: call.data == "katil")
def katil_callback(call):
    global katilanlar, cekilis_aktif
    if not cekilis_aktif:
        bot.answer_callback_query(call.id, "⚠️ Şu anda aktif çekiliş yok.")
        return

    user = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    if user in katilanlar:
        bot.answer_callback_query(call.id, "Zaten katıldın 🎁")
    else:
        katilanlar.append(user)
        bot.answer_callback_query(call.id, "✅ Katıldın!")
        guncelle_katilim()

        # Otomatik bitirme
        if katilim_limiti and len(katilanlar) >= katilim_limiti:
            bitir_cekilis(None)


# === KATIL SAYISINI GÜNCELLE ===
def guncelle_katilim():
    global cekilis_mesaj_id
    try:
        yeni_text = f"🎉 **Yeni çekiliş başladı!**\nKatılmak için aşağıdaki butona tıkla 👇\n👥 Katılan: {len(katilanlar)} kişi"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎁 Katıl", callback_data="katil"))
        bot.edit_message_text(
            yeni_text, chat_id=KANAL_ADI, message_id=cekilis_mesaj_id,
            reply_markup=markup, parse_mode="Markdown"
        )
    except Exception as e:
        print("Güncelleme hatası:", e)


# === ÇEKİLİŞİ BİTİR ===
def bitir_cekilis(chat_id=None):
    global cekilis_aktif
    cekilis_aktif = False
    if not katilanlar:
        if chat_id:
            bot.send_message(chat_id, "Kimse katılmadı 😅")
        return
    kazanan = random.choice(katilanlar)
    sonuc = f"🎉 Çekiliş sona erdi!\n🏆 Kazanan: {kazanan}"
    bot.send_message(KANAL_ADI, sonuc)
    if chat_id:
        bot.send_message(chat_id, sonuc)


print("🤖 Bot aktif (çoklu admin destekli) ve komut bekliyor...")
bot.polling(none_stop=True)