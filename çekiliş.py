import telebot
from telebot import types
import random
import time
import threading
import json
import os

# === AYARLAR ===
BOT_TOKEN = "8180247520:AAFw-UVXLjO5S_YP8vJQFOIYWPHyGczjy2g"
KANAL_ADI = "@ByzeusxToolmain"
ADMIN_IDS = [7823668175, 7038895537]  # admin ID'leri

bot = telebot.TeleBot(BOT_TOKEN)

# === VERİ VE DEĞİŞKENLER ===
cekilisler = {}  # {cekilis_id: {"katilanlar": [], "mesaj_id": int, "limit": int, "bitis_suresi": timestamp}}
DATA_FILE = "cekilisler.json"

# === JSON DOSYASI İLE KAYDETME VE YÜKLEME ===
def kaydet_veri():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cekilisler, f, ensure_ascii=False, indent=2)


def yukle_veri():
    global cekilisler
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            cekilisler = json.load(f)
        # Süreleri thread ile yeniden başlat
        for cekilis_id, cekilis in cekilisler.items():
            cekilis["bitis_suresi"] = float(cekilis["bitis_suresi"])
            threading.Thread(target=sureli_bitir, args=(cekilis_id,)).start()


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
            bot.send_message(message.chat.id, "🚫 Bu komut sadece adminler tarafından kullanılabilir.")
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
    if cekilisler:
        bot.send_message(message.chat.id, f"🟢 Şu anda {len(cekilisler)} aktif çekiliş var.")
    else:
        bot.send_message(message.chat.id, "🔴 Şu anda aktif çekiliş yok.")


@bot.message_handler(func=lambda m: m.text == "🎁 Katılımcılar")
@admin_only
def katilanlari_goster(message):
    if not cekilisler:
        bot.send_message(message.chat.id, "Henüz aktif çekiliş yok 😅")
        return
    text = "🎁 Aktif Çekilişler ve Katılımcılar:\n"
    for cid, cekilis in cekilisler.items():
        katilanlar = "\n".join(cekilis["katilanlar"]) if cekilis["katilanlar"] else "Henüz yok"
        text += f"\nÇekiliş ID: {cid}\nKatılanlar ({len(cekilis['katilanlar'])}):\n{katilanlar}\n"
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "⏱️ Otomatik Bitirme")
@admin_only
def otomatik_bitir_ayarla(message):
    bot.send_message(message.chat.id, "Kaç kişi olunca çekiliş otomatik bitsin?")
    bot.register_next_step_handler(message, otomatik_belirle)


def otomatik_belirle(message):
    try:
        limit = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Geçerli bir sayı girmeniz lazım.")
        return
    for cekilis in cekilisler.values():
        cekilis["limit"] = limit
    kaydet_veri()
    bot.send_message(message.chat.id, f"✅ Limit {limit} kişi olarak ayarlandı.")


# === ÇEKİLİŞ BAŞLAT - MESAJ ALTI SÜRE BUTONLARI ===
@bot.message_handler(func=lambda m: m.text == "🚀 Çekiliş Başlat")
@admin_only
def cekilis_baslat(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("30 Dakika", callback_data="sure_1800"),
        types.InlineKeyboardButton("1 Saat", callback_data="sure_3600"),
        types.InlineKeyboardButton("2 Saat", callback_data="sure_7200")
    )
    bot.send_message(message.chat.id, "Çekiliş süresini seçin:", reply_markup=markup)


# === SÜRE SEÇİMİ CALLBACK ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("sure_"))
def sure_secimi(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "🚫 Bu buton sadece adminler için.")
        return
    
    sure = int(call.data.split("_")[1])
    cekilis_id = str(time.time())

    # Inline katıl butonu
    markup = types.InlineKeyboardMarkup()
    katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data=f"katil_{cekilis_id}")
    markup.add(katil_btn)

    # Çekiliş mesajını kanalda oluştur
    msg = bot.send_message(
        KANAL_ADI,
        f"🎉 Yeni çekiliş başladı! Süre: {sure//60} dakika\nKatılmak için tıkla 👇\n👥 Katılan: 0",
        reply_markup=markup
    )

    cekilisler[cekilis_id] = {
        "katilanlar": [],
        "mesaj_id": msg.message_id,
        "limit": None,
        "bitis_suresi": time.time() + sure
    }
    kaydet_veri()

    # Callback mesajını cevapla (buton basıldı mesajı)
    bot.answer_callback_query(call.id, f"✅ Çekiliş başlatıldı! ID: {cekilis_id}")

    # Süre sonunda çekilişi bitir
    threading.Thread(target=sureli_bitir, args=(cekilis_id,)).start()


# === KATIL BUTONU ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("katil_"))
def katil_callback(call):
    cekilis_id = call.data.split("_")[1]
    cekilis = cekilisler.get(cekilis_id)
    if not cekilis:
        bot.answer_callback_query(call.id, "⚠️ Bu çekiliş sona ermiş.")
        return

    user = f"@{call.from_user.username}" if call.from_user.username else f"{call.from_user.first_name}_{call.from_user.id}"
    if user in cekilis["katilanlar"]:
        bot.answer_callback_query(call.id, "Zaten katıldın 🎁")
    else:
        cekilis["katilanlar"].append(user)
        kaydet_veri()
        bot.answer_callback_query(call.id, "✅ Katıldın!")
        guncelle_katilim(cekilis_id)

        # Limit varsa otomatik bitir
        if cekilis["limit"] and len(cekilis["katilanlar"]) >= cekilis["limit"]:
            bitir_cekilis(cekilis_id)


# === KATIL SAYISI GÜNCELLEME ===
def guncelle_katilim(cekilis_id):
    cekilis = cekilisler.get(cekilis_id)
    if not cekilis:
        return
    yeni_text = f"🎉 Yeni çekiliş başladı!\nKatılmak için tıkla 👇\n👥 Katılan: {len(cekilis['katilanlar'])}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎁 Katıl", callback_data=f"katil_{cekilis_id}"))
    try:
        bot.edit_message_text(
            yeni_text, chat_id=KANAL_ADI, message_id=cekilis["mesaj_id"], reply_markup=markup
        )
    except Exception as e:
        print("Güncelleme hatası:", e)


# === ÇEKİLİŞİ BİTİR ===
def bitir_cekilis(cekilis_id):
    cekilis = cekilisler.pop(cekilis_id, None)
    kaydet_veri()
    if not cekilis:
        return
    if not cekilis["katilanlar"]:
        bot.edit_message_text(
            f"Çekiliş {cekilis_id}: Kimse katılmadı 😅",
            chat_id=KANAL_ADI,
            message_id=cekilis["mesaj_id"]
        )
        return
    kazanan = random.choice(cekilis["katilanlar"])
    bot.edit_message_text(
        f"🎉 Çekiliş {cekilis_id} sona erdi!\n🏆 Kazanan: {kazanan}",
        chat_id=KANAL_ADI,
        message_id=cekilis["mesaj_id"]
    )


# === SÜRELİ ÇEKİLİŞ BİTİRME THREAD ===
def sureli_bitir(cekilis_id):
    cekilis = cekilisler.get(cekilis_id)
    if not cekilis:
        return
    kalan = cekilis["bitis_suresi"] - time.time()
    if kalan > 0:
        time.sleep(kalan)
    bitir_cekilis(cekilis_id)


# === BOT BAŞLANGICI ===
yukle_veri()
print("🤖 Bot aktif (çoklu çekiliş, süre ve JSON destekli) ve komut bekliyor...")
bot.polling(none_stop=True)