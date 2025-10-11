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


@bot.message_handler(func=lambda m: m.text == "🚀 Çekiliş Başlat")
@admin_only
def cekilis_baslat(message):
    bot.send_message(message.chat.id, "Çekiliş başlatmak için süreyi (saniye) girin:")
    bot.register_next_step_handler(message, baslat_sure_al)


def baslat_sure_al(message):
    try:
        sure = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Geçerli bir sayı girin.")
        return
    
    cekilis_id = str(time.time())
    markup = types.InlineKeyboardMarkup()
    katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data=f"katil_{cekilis_id}")
    markup.add(katil_btn)
    
    msg = bot.send_message(
        KANAL_ADI,
        f"🎉 Yeni çekiliş başladı! Süre: {sure} saniye\nKatılmak için tıkla 👇\n👥 Katılan: 0",
        reply_markup=markup
    )
    
    cekilisler[cekilis_id] = {
        "katilanlar": [],
        "mesaj_id": msg.message_id,
        "limit": None,
        "bitis_suresi": time.time() + sure
    }
    kaydet_veri()
    
    threading.Thread(target=sureli_bitir, args=(cekilis_id,)).start()
    bot.send_message(message.chat.id, f"✅ Çekiliş başlatıldı! ID: {cekilis_id}")


def sureli_bitir(cekilis_id):
    cekilis = cekilisler.get(cekilis_id)
    if not cekilis:
        return
    kalan = cekilis["bitis_suresi"] - time.time()
    if kalan > 0:
        time.sleep(kalan)
    bitir_cekilis(cekilis_id)


@bot.message_handler(func=lambda m: m.text == "🛑 Çekiliş Bitir")
@admin_only
def cekilis_bitir(message):
    if not cekilisler:
        bot.send_message(message.chat.id, "Aktif çekiliş yok 😅")
        return
    text = "Hangi çekilişi bitirelim? Çekiliş ID girin:\n"
    for cid in cekilisler.keys():
        text += f"{cid}\n"
    bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(message, manuel_bitir)


def manuel_bitir(message):
    cid = message.text
    if cid in cekilisler:
        bitir_cekilis(cid)
        bot.send_message(message.chat.id, f"✅ Çekiliş {cid} bitirildi!")
    else:
        bot.send_message(message.chat.id, "❌ Geçersiz çekiliş ID.")


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

        if cekilis["limit"] and len(cekilis["katilanlar"]) >= cekilis["limit"]:
            bitir_cekilis(cekilis_id)


# === KATIL SAYISINI GÜNCELLE ===
def guncelle_katilim(cekilis_id):
    cekilis = cekilisler.get(cekilis_id)
    if not cekilis:
        return
    yeni_text = f"🎉 Yeni çekiliş başladı!\nKatılmak için tıkla 👇\n👥 Katılan: {len(cekilis['katilanlar'])}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎁 Katıl", callback_data=f"katil_{cekilis_id}"))
    bot.edit_message_text(
        yeni_text, chat_id=KANAL_ADI, message_id=cekilis["mesaj_id"], reply_markup=markup
    )


# === ÇEKİLİŞİ BİTİR ===
def bitir_cekilis(cekilis_id):
    cekilis = cekilisler.pop(cekilis_id, None)
    kaydet_veri()
    if not cekilis:
        return
    if not cekilis["katilanlar"]:
        bot.send_message(KANAL_ADI, f"Çekiliş {cekilis_id}: Kimse katılmadı 😅")
        return
    kazanan = random.choice(cekilis["katilanlar"])
    bot.send_message(KANAL_ADI, f"🎉 Çekiliş {cekilis_id} sona erdi!\n🏆 Kazanan: {kazanan}")


# === BOT BAŞLANGICI ===
yukle_veri()
print("🤖 Bot aktif (çoklu çekiliş, süre ve JSON destekli) ve komut bekliyor...")
bot.polling(none_stop=True)