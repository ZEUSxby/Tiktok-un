import telebot
from telebot import types
import random
import time
import threading
from datetime import datetime

# === AYARLAR ===
BOT_TOKEN = "8361686094:AAE9FQzmw053xgGvISLnQ3h4di_wDLMg47E"

# Kanallar
KANALLAR = {
    "acik_kanal": "@ByzeusxToolmain",    # Açık kanal
    "gizli_kanal": "-1002530564544"      # Gizli kanal ID'si
}

# Admin ID
ADMIN_IDS = [7823668175, 7038895537]

bot = telebot.TeleBot(BOT_TOKEN)

# === DEĞİŞKENLER ===
cekilis_aktif = False
katilanlar = []
cekilis_mesaj_ids = {}
katilim_limiti = None
cekilis_baslangic_zamani = None
otomatik_bitirme_suresi = None
timer_thread = None
aktif_kanallar = []
secim_asamasi = None  # "kanal_secimi", "katilim_limiti", "sure"

# === BASIT MENÜ ===
def ana_menu():
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    menu.add("🚀 Başlat", "🛑 Bitir", "👥 Katılımcılar")
    return menu

# === ADMIN KONTROL ===
def admin_only(func):
    def wrapper(message):
        if message.from_user.id not in ADMIN_IDS:
            bot.send_message(message.chat.id, "🚫 Yetkiniz yok.")
            return
        func(message)
    return wrapper

# === KANAL KONTROL ===
def kanal_kontrol(kanal_adi):
    try:
        chat = bot.get_chat(kanal_adi)
        return True, chat.title
    except:
        return False, None

def bot_kanalda_yonetici_mi(kanal_adi):
    try:
        chat_member = bot.get_chat_member(kanal_adi, bot.get_me().id)
        return chat_member.status in ['administrator', 'creator']
    except:
        return False

# === ZAMAN FORMATI ===
def zaman_formatı(saniye):
    saat = saniye // 3600
    dakika = (saniye % 3600) // 60
    saniye = saniye % 60
    return f"{saat:02d}:{dakika:02d}:{saniye:02d}"

# === OTOMATİK BİTİRME ===
def otomatik_bitir_timer(sure_dakika):
    global cekilis_aktif
    time.sleep(sure_dakika * 60)
    if cekilis_aktif:
        bitir_cekilis(None)

# === /start KOMUTU ===
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = """🤖 Çekiliş Botu

Komutlar:
🚀 Başlat - Çekilişi başlat
🛑 Bitir - Çekilişi bitir  
👥 Katılımcılar - Listeyi göster"""
    
    bot.send_message(message.chat.id, text, reply_markup=ana_menu())

# === ÇEKİLİŞ BAŞLAT ===
@bot.message_handler(func=lambda m: m.text == "🚀 Başlat")
@admin_only
def cekilis_baslat(message):
    global secim_asamasi
    
    if cekilis_aktif:
        bot.send_message(message.chat.id, "⚠️ Zaten çekiliş var!")
        return

    secim_asamasi = "kanal_secimi"
    
    # Kanal seçim butonları
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Kanal durumlarını kontrol et ve butonları oluştur
    for kanal_key, kanal_adi in KANALLAR.items():
        durum, isim = kanal_kontrol(kanal_adi)
        yonetici = bot_kanalda_yonetici_mi(kanal_adi) if durum else False
        
        if kanal_key == "acik_kanal":
            btn_text = "📢 main1"
        else:
            btn_text = "🔒 main2"
            
        if durum and yonetici:
            btn_text = "✅ " + btn_text
        else:
            btn_text = "❌ " + btn_text
            
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"kanal_{kanal_key}"))
    
    markup.add(types.InlineKeyboardButton("🎯 Her İki Kanal", callback_data="kanal_hepsi"))
    
    bot.send_message(message.chat.id, "📡 **Hangi kanal(lar)da çekiliş yapılsın?**", 
                    reply_markup=markup, parse_mode="Markdown")

# === KANAL SEÇİMİ ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("kanal_"))
def kanal_secimi_callback(call):
    global aktif_kanallar, secim_asamasi
    
    if call.data == "kanal_hepsi":
        # Tüm uygun kanalları seç
        aktif_kanallar = []
        for kanal_adi in KANALLAR.values():
            durum, isim = kanal_kontrol(kanal_adi)
            yonetici = bot_kanalda_yonetici_mi(kanal_adi) if durum else False
            if durum and yonetici:
                aktif_kanallar.append(kanal_adi)
        
        if aktif_kanallar:
            bot.answer_callback_query(call.id, "✅ Tüm kanallar seçildi!")
            secim_asamasi = "katilim_limiti"
            katilim_limiti_sor(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Hiçbir kanal kullanılamıyor!")
            
    else:
        kanal_key = call.data.replace("kanal_", "")
        if kanal_key in KANALLAR:
            kanal_adi = KANALLAR[kanal_key]
            durum, isim = kanal_kontrol(kanal_adi)
            yonetici = bot_kanalda_yonetici_mi(kanal_adi) if durum else False
            
            if durum and yonetici:
                aktif_kanallar = [kanal_adi]
                bot.answer_callback_query(call.id, "✅ Kanal seçildi!")
                secim_asamasi = "katilim_limiti"
                katilim_limiti_sor(call.message)
            else:
                bot.answer_callback_query(call.id, "❌ Bu kanal kullanılamaz!")

def katilim_limiti_sor(message):
    global secim_asamasi
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔢 Katılım Sınırı Belirle", callback_data="katilim_evet"),
        types.InlineKeyboardButton("❌ Katılım Sınırı Yok", callback_data="katilim_hayir")
    )
    
    bot.send_message(message.chat.id, "👥 **Katılım sınırı olsun mu?**\n\nBelirli sayıda kişi katılınca otomatik bitsin?", 
                    reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("katilim_"))
def katilim_limiti_callback(call):
    global secim_asamasi
    
    if call.data == "katilim_evet":
        bot.answer_callback_query(call.id, "Katılım sınırı seçildi")
        secim_asamasi = "katilim_limiti_deger"
        bot.send_message(call.message.chat.id, "🔢 **Kaç kişi katılınca çekiliş otomatik bitsin?**\n\nSayı yazın:")
    else:
        bot.answer_callback_query(call.id, "Katılım sınırı yok")
        secim_asamasi = "sure_secimi"
        sure_sor(call.message)

def sure_sor(message):
    global secim_asamasi
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⏱️ Süre Belirle", callback_data="sure_evet"),
        types.InlineKeyboardButton("❌ Süre Yok", callback_data="sure_hayir")
    )
    
    bot.send_message(message.chat.id, "⏰ **Süre sınırı olsun mu?**\n\nBelirli süre sonra otomatik bitsin?", 
                    reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sure_"))
def sure_callback(call):
    global secim_asamasi
    
    if call.data == "sure_evet":
        bot.answer_callback_query(call.id, "Süre seçildi")
        secim_asamasi = "sure_deger"
        bot.send_message(call.message.chat.id, "⏱️ **Kaç dakika sonra çekiliş otomatik bitsin?**\n\nSayı yazın:")
    else:
        bot.answer_callback_query(call.id, "Süre yok")
        secim_asamasi = None
        cekilisi_baslat_final(call.message)

# === KATILIM LİMİTİ VE SÜRE DEĞERLERİ ===
@bot.message_handler(func=lambda message: secim_asamasi in ["katilim_limiti_deger", "sure_deger"])
def deger_al(message):
    global katilim_limiti, otomatik_bitirme_suresi, secim_asamasi
    
    try:
        deger = int(message.text)
        if deger < 1:
            bot.send_message(message.chat.id, "❌ 1'den büyük bir sayı girin!")
            return
            
        if secim_asamasi == "katilim_limiti_deger":
            katilim_limiti = deger
            bot.send_message(message.chat.id, f"✅ Katılım sınırı: {deger} kişi")
            secim_asamasi = "sure_secimi"
            sure_sor(message)
            
        elif secim_asamasi == "sure_deger":
            otomatik_bitirme_suresi = deger
            bot.send_message(message.chat.id, f"✅ Süre: {deger} dakika")
            secim_asamasi = None
            cekilisi_baslat_final(message)
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ Geçerli bir sayı girin!")

# === ÇEKİLİŞİ BAŞLAT (FİNAL) ===
def cekilisi_baslat_final(message):
    global cekilis_aktif, katilanlar, cekilis_mesaj_ids, cekilis_baslangic_zamani, timer_thread
    
    cekilis_aktif = True
    katilanlar = []
    cekilis_baslangic_zamani = datetime.now()
    cekilis_mesaj_ids = {}

    # Çekiliş mesajını hazırla
    limit_text = f"\n🎁 Katılım Sınırı: {katilim_limiti} kişi" if katilim_limiti else ""
    sure_text = f"\n⏰ Süre: {otomatik_bitirme_suresi} dakika" if otomatik_bitirme_suresi else ""
    
    if not limit_text and not sure_text:
        kosul_text = "\n⏳ Manuel olarak bitirilecek"
    else:
        kosul_text = limit_text + sure_text

    cekilis_text = f"""🎉 ÇEKİLİŞ BAŞLADI!{kosul_text}

👇 Katılmak için butona tıkla!
👥 Katılanlar: 0 kişi"""

    markup = types.InlineKeyboardMarkup()
    katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data="katil")
    markup.add(katil_btn)

    # Tüm kanallarda başlat
    basarili_kanallar = []
    for kanal_adi in aktif_kanallar:
        try:
            msg = bot.send_message(kanal_adi, cekilis_text, reply_markup=markup)
            cekilis_mesaj_ids[kanal_adi] = msg.message_id
            basarili_kanallar.append(kanal_adi)
        except Exception as e:
            print(f"Hata: {e}")

    if basarili_kanallar:
        # Timer başlat (eğer süre varsa)
        if otomatik_bitirme_suresi:
            timer_thread = threading.Thread(target=otomatik_bitir_timer, args=(otomatik_bitirme_suresi,))
            timer_thread.daemon = True
            timer_thread.start()
        
        # Başarı mesajı
        kanal_sayisi = len(basarili_kanallar)
        kosul_bilgisi = []
        if katilim_limiti:
            kosul_bilgisi.append(f"{katilim_limiti} kişi")
        if otomatik_bitirme_suresi:
            kosul_bilgisi.append(f"{otomatik_bitirme_suresi} dakika")
        
        if kosul_bilgisi:
            kosul_text = f" ({' + '.join(kosul_bilgisi)})"
        else:
            kosul_text = " (Manuel bitirme)"
            
        bot.send_message(message.chat.id, f"✅ Çekiliş başlatıldı! {kanal_sayisi} kanal{kosul_text}")
    else:
        cekilis_aktif = False
        bot.send_message(message.chat.id, "❌ Hiçbir kanalda başlatılamadı!")

# === KATILIM GÜNCELLE ===
def guncelle_katilim():
    global cekilis_mesaj_ids
    
    try:
        limit_text = f"\n🎁 Katılım Sınırı: {katilim_limiti} kişi" if katilim_limiti else ""
        sure_text = f"\n⏰ Süre: {otomatik_bitirme_suresi} dakika" if otomatik_bitirme_suresi else ""
        
        if not limit_text and not sure_text:
            kosul_text = "\n⏳ Manuel olarak bitirilecek"
        else:
            kosul_text = limit_text + sure_text

        yeni_text = f"""🎉 ÇEKİLİŞ BAŞLADI!{kosul_text}

👇 Katılmak için butona tıkla!
👥 Katılanlar: {len(katilanlar)} kişi"""

        markup = types.InlineKeyboardMarkup()
        katil_btn = types.InlineKeyboardButton("🎁 Katıl", callback_data="katil")
        markup.add(katil_btn)
        
        for kanal_adi, mesaj_id in cekilis_mesaj_ids.items():
            try:
                bot.edit_message_text(yeni_text, chat_id=kanal_adi, message_id=mesaj_id, reply_markup=markup)
            except:
                pass
    except:
        pass

# === KATIL BUTONU ===
@bot.callback_query_handler(func=lambda call: call.data == "katil")
def katil_callback(call):
    global katilanlar, cekilis_aktif
    
    if not cekilis_aktif:
        bot.answer_callback_query(call.id, "❌ Çekiliş bitti!")
        return

    user_name = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    user_id = call.from_user.id
    
    user_unique = f"{user_name} ({user_id})"
    
    if any(str(user_id) in katilimci for katilimci in katilanlar):
        bot.answer_callback_query(call.id, "❌ Zaten katıldın!")
    else:
        katilanlar.append(user_unique)
        bot.answer_callback_query(call.id, "✅ Katıldın!")
        guncelle_katilim()

        if katilim_limiti and len(katilanlar) >= katilim_limiti:
            bitir_cekilis(None)

# === KATILIMCILARI GÖSTER ===
@bot.message_handler(func=lambda m: m.text == "👥 Katılımcılar")
@admin_only
def katilanlari_goster(message):
    if not katilanlar:
        bot.send_message(message.chat.id, "❌ Henüz katılım yok!")
    else:
        liste = "\n".join([f"• {k}" for k in katilanlar])
        bot.send_message(message.chat.id, f"👥 Katılımcılar ({len(katilanlar)}):\n{liste}")

# === ÇEKİLİŞ BİTİR ===
@bot.message_handler(func=lambda m: m.text == "🛑 Bitir")
@admin_only
def cekilis_bitir(message):
    if not cekilis_aktif:
        bot.send_message(message.chat.id, "❌ Aktif çekiliş yok!")
        return
    bitir_cekilis(message.chat.id)

def bitir_cekilis(chat_id=None):
    global cekilis_aktif, katilanlar, timer_thread, aktif_kanallar, katilim_limiti, otomatik_bitirme_suresi
    
    if not cekilis_aktif:
        return
        
    cekilis_aktif = False
    
    # Kazananı belirle
    if katilanlar:
        kazanan = random.choice(katilanlar)
        sonuc_text = f"""🎉 ÇEKİLİŞ BİTTİ!

🏆 Kazanan: {kazanan}
👥 Toplam: {len(katilanlar)} kişi

Tebrikler! 🎊"""
    else:
        sonuc_text = "🎉 ÇEKİLİŞ BİTTİ!\n\n❌ Katılım olmadı!"
        kazanan = None
    
    # Sonucu kanallara gönder
    for kanal_adi in aktif_kanallar:
        try:
            bot.send_message(kanal_adi, sonuc_text)
        except:
            pass
    
    # Admin'e bildir
    if chat_id:
        bot.send_message(chat_id, "✅ Çekiliş bitti!", reply_markup=ana_menu())
    
    # Timer temizle
    if timer_thread and timer_thread.is_alive():
        timer_thread = None

    # Değişkenleri sıfırla
    aktif_kanallar = []
    katilim_limiti = None
    otomatik_bitirme_suresi = None

# === BOTU BAŞLAT ===
print("🤖 Çekiliş Botu Aktif!")
bot.polling(none_stop=True)
