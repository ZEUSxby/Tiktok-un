import re
import time
import requests
from datetime import datetime
import telebot
from telebot.types import InputFile

# ========== AYARLAR ==========
BOT_TOKEN = "8358589431:AAE_c-0nK3y07dCJEBfk6xJT_sOVWDRJLLU"  # <--- Token'ı buraya yapıştır
bot = telebot.TeleBot(BOT_TOKEN)
RATE_LIMIT = 1  # saniye
RESULT_FILE = "results.txt"


# ========== YARDIMCI FONKSİYONLAR ==========
def mask_phone(phone: str) -> str:
    if not phone:
        return None
    phone = str(phone).strip()
    cleaned = re.sub(r"[^\d+]", "", phone)
    if len(cleaned) <= 4:
        return cleaned
    last4 = cleaned[-4:]
    return ("*" * (len(cleaned) - 4)) + last4

def extract_phone_info(data: dict):
    if not data or not isinstance(data, dict):
        return None, None
    phone_keys = ["phone", "phone_number", "mobile", "phone_md5", "mobile_phone"]
    verified_keys = ["phone_verified", "is_phone_verified", "mobile_verified", "is_mobile_verified"]

    phone = None
    for k in phone_keys:
        v = data.get(k)
        if v:
            phone = v
            break

    if not phone:
        for parent in ["user", "account", "profile"]:
            p = data.get(parent, {})
            if isinstance(p, dict):
                for k in phone_keys:
                    if p.get(k):
                        phone = p.get(k)
                        break
            if phone:
                break

    phone_verified = None
    for vk in verified_keys:
        if vk in data:
            phone_verified = bool(data.get(vk))
            break
    if phone_verified is None:
        for parent in ["user", "account", "profile"]:
            p = data.get(parent, {})
            if isinstance(p, dict):
                for vk in verified_keys:
                    if vk in p:
                        phone_verified = bool(p.get(vk))
                        break
            if phone_verified is not None:
                break

    return phone, phone_verified


# ========== TIKTOK BİLGİ ALMA ==========
def get_tiktok_user_info(sessionid=None, username=None, index=None):
    data = {}
    # Passport sorgusu (session varsa)
    if sessionid:
        cookies = {"sessionid": sessionid}
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile Safari/537.36)",
            "Referer": "https://www.tiktok.com/"
        }
        info_url = "https://www.tiktok.com/passport/web/account/info/"
        try:
            resp = requests.get(info_url, cookies=cookies, headers=headers, timeout=10)
            if resp.status_code == 200:
                try:
                    data = resp.json().get("data", {}) or {}
                    username = username or data.get("username")
                except Exception:
                    return f"❌ #{index} JSON okunamadı veya sessionid geçersiz. ({sessionid})"
            else:
                return f"❌ #{index} İstek başarısız, kod: {resp.status_code}"
        except requests.RequestException as e:
            return f"❌ #{index} Session sorgusu başarısız: {e}"

    if not username:
        return f"❌ #{index} Kullanıcı adı bulunamadı."

    # Profil sayfası
    url = f"https://www.tiktok.com/@{username}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"❌ #{index} Profil bilgileri alınamadı. ({username})"
    except requests.RequestException as e:
        return f"❌ #{index} Profil isteği başarısız: {e}"

    html = response.text
    followers = re.search(r'"followerCount":(\d+)', html)
    following = re.search(r'"followingCount":(\d+)', html)
    videos = re.search(r'"videoCount":(\d+)', html)
    name = re.search(r'"nickname":"(.*?)"', html)
    bio = re.search(r'"signature":"(.*?)"', html)
    first_video_timestamp = re.search(r'"createTime":(\d+)', html)
    location = re.search(r'"region":"(.*?)"', html)
    verified = re.search(r'"verified":(true|false)', html)
    likes = re.search(r'"likeCount":(\d+)', html)

    if first_video_timestamp:
        try:
            account_creation_date = datetime.utcfromtimestamp(
                int(first_video_timestamp.group(1))
            ).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            account_creation_date = None
    else:
        account_creation_date = None

    location_text = location.group(1) if location else "Bilinmiyor"
    location_type = "Hesap Iraklı" if "IQ" in location_text or "Iraq" in location_text else "Hesap Yabancı"
    verified_status = "Doğrulanmış ✅" if verified and verified.group(1) == "true" else "Doğrulanmamış ❌"

    # Telefon bilgisi (passport data içinden)
    phone_raw, phone_verified = extract_phone_info(data)
    phone_masked = mask_phone(phone_raw) if phone_raw else None
    if phone_masked:
        phone_status_text = f"{phone_masked} ({'Doğrulanmış' if phone_verified else 'Doğrulanmamış' if phone_verified is not None else 'Doğrulama bilinmiyor'})"
    else:
        phone_status_text = "Kayıtlı değil veya görünmüyor"

    # Sonuç formatı (session ID artık HİÇ bir şekilde maskelenmiyor)
    result = f"\n============ 🎯 #{index} TİKTOK USER INFO ==============\n"
    result += f"🔐 Session ID: {sessionid if sessionid else 'N/A'}\n"
    result += f"👤 Kullanıcı Adı / Username: {username}\n"
    if name:
        result += f"📝 İsim / Name: {name.group(1)}\n"
    if data.get('email'):
        result += f"📧 Email / Email: {data.get('email')}\n"
    if data.get('user_id'):
        result += f"🆔 Kullanıcı ID / User ID: {data.get('user_id')}\n"
    if data.get('country_code'):
        result += f"🌍 Ülke Kodu / Country Code: {data.get('country_code')}\n"
    # Telefon hattı
    result += f"📞 Telefon / Phone: {phone_status_text}\n"
    if followers:
        result += f"👥 Takipçi / Followers: {followers.group(1)}\n"
    if following:
        result += f"➡️ Takip Edilen / Following: {following.group(1)}\n"
    if videos:
        result += f"🎥 Video Sayısı / Videos: {videos.group(1)}\n"
    if likes:
        result += f"❤️ Beğeni Sayısı / Likes: {likes.group(1)}\n"
    if bio:
        result += f"📄 Biyografi / Bio: {bio.group(1)}\n"

    result += f"🔑 Şifre Durumu / Password Set: {'Evet / Yes' if data.get('has_password') else 'Hayır / No'}\n"
    if account_creation_date:
        result += f"📅 Hesap Oluşturma Tarihi / Account Creation Date: {account_creation_date}\n"

    result += f"📌 Konum Türü / Location Type: {location_type}\n"
    result += f"✔️ Doğrulama Durumu / Verified Status: {verified_status}\n"
    result += "=" * 48
    return result


# ========== MESAJ / DOSYA YÖNETİCİLERİ ==========
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "👋 Hoş geldin!\n\n📂 Bana .txt dosyası veya alt alta session ID gönder.\nHer satırda 1 tane session ID olsun.\n\n⏱️ Rate limit: 1 saniye.")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    sessions = [s.strip() for s in message.text.splitlines() if s.strip()]
    if not sessions:
        return bot.reply_to(message, "⚠️ Geçerli session ID bulunamadı.")

    bot.reply_to(message, f"🔍 {len(sessions)} session işleniyor...")

    all_results = []
    for i, sessionid in enumerate(sessions, start=1):
        result = get_tiktok_user_info(sessionid=sessionid, index=i)
        all_results.append(result)
        # Çok uzun mesajlar için ilk 4000 karakteri gönderiyoruz
        bot.send_message(message.chat.id, result[:4000])
        time.sleep(RATE_LIMIT)

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_results))

    with open(RESULT_FILE, "rb") as doc:
        bot.send_document(message.chat.id, doc, caption="📄 Tüm sonuçlar burada!")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open("sessions.txt", "wb") as f:
        f.write(downloaded_file)

    with open("sessions.txt", "r", encoding="utf-8") as f:
        sessions = [x.strip() for x in f.readlines() if x.strip()]

    bot.reply_to(message, f"📂 Dosyada {len(sessions)} session bulundu, işleniyor...")

    all_results = []
    for i, sessionid in enumerate(sessions, start=1):
        result = get_tiktok_user_info(sessionid=sessionid, index=i)
        all_results.append(result)
        bot.send_message(message.chat.id, result[:4000])
        time.sleep(RATE_LIMIT)

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_results))

    with open(RESULT_FILE, "rb") as doc:
        bot.send_document(message.chat.id, doc, caption="✅ İşlem tamamlandı!")


# ========== ANA ==========
print("✅ Bot çalışıyor...")
bot.infinity_polling()
