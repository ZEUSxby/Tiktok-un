import re
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

BOT_TOKEN = "7488416267:AAFJYwF7_Y_78DPWisD3plAuOsJ0UDqyw3s"

# 🔎 TikTok verilerini al
def get_tiktok_user_info(sessionid=None, username=None):
    data = {}
    if sessionid:
        cookies = {"sessionid": sessionid}
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile Safari/537.36)",
            "Referer": "https://www.tiktok.com/"
        }
        info_url = "https://www.tiktok.com/passport/web/account/info/"
        resp = requests.get(info_url, cookies=cookies, headers=headers)
        if resp.status_code == 200:
            try:
                data = resp.json().get("data", {})
                username = data.get("username")
            except:
                return "❌ JSON okunamadı veya sessionid geçersiz."
        else:
            return f"❌ İstek başarısız, kod: {resp.status_code}"

    if not username:
        return "❌ Kullanıcı adı bulunamadı."

    url = f"https://www.tiktok.com/@{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return "❌ Profil bilgileri alınamadı."

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
        account_creation_date = datetime.utcfromtimestamp(
            int(first_video_timestamp.group(1))
        ).strftime('%Y-%m-%d %H:%M:%S')
    else:
        account_creation_date = None

    location = location.group(1) if location else "Bilinmiyor"
    location_type = "Hesap Iraklı" if "IQ" in location or "Iraq" in location else "Hesap Yabancı"
    verified_status = "Doğrulanmış ✅" if verified and verified.group(1) == "true" else "Doğrulanmamış ❌"

    result = "\n============ 🎯 TİKTOK USER INFO ==============\n"
    result += f"👤 Kullanıcı Adı / Username: {username}\n"
    if name: 
        result += f"📝 İsim / Name: {name.group(1)}\n"
    if data.get('email'): 
        result += f"📧 Email / Email: {data.get('email')}\n"
    if data.get('user_id'): 
        result += f"🆔 Kullanıcı ID / User ID: {data.get('user_id')}\n"
    if data.get('country_code'): 
        result += f"🌍 Ülke Kodu / Country Code: {data.get('country_code')}\n"
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
    result += "=" * 44
    return result


# 🚀 Telegram bot akışı
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Merhaba! 🎯\nBana istediğin zaman *Session ID* veya *TikTok kullanıcı adını* gönder, bilgilerini getireyim.",
        parse_mode="Markdown"
    )

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()

    msg = update.message.reply_text("⌛ Kullanıcı bilgileri alınıyor...")

    if len(text) > 20 and text.isalnum():
        result = get_tiktok_user_info(sessionid=text)
    else:
        result = get_tiktok_user_info(username=text)

    msg.edit_text(result)


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    print("🤖 Bot çalışıyor...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
