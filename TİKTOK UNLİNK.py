import telebot
import requests
import time

# ----------------------------[ TikTok Unbind Fonksiyonları ]----------------------------
HOSTS = [
    "api16-normal-c-alisg.tiktokv.com",
    "api16-normal-no1a.tiktokv.eu",
    "api16-normal-c-useast1a.tiktokv.com",
    "api16-normal-c-useast2a.tiktokv.com"
]

def gets(sessionid):
    for h in HOSTS:
        try:
            url = f'https://{h}/passport/web/account/info/'
            headers = {'Cookie': f'sessionid={sessionid}'}
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()
            if "username" in response.text:
                if data.get('message') == 'success':
                    user = data.get('data', {}).get('username')
                    platform = data['data']['connects'][0]['platform']
                    return h, platform, user
        except:
            continue
    return None, None, None

def unbind(sessionid):
    if not sessionid:
        return {"error": "❌ Session ID eksik."}

    host, platform, username = gets(sessionid)
    if not host or not platform:
        return {"error": "❌ Başarısız! Herhangi bir platforma bağlı değilsiniz."}

    unbind_url = f'https://{host}/passport/auth/unbind/?aid=8311&platform={platform}'
    headers = {
        'Host': host,
        'Cookie': f'sessionid={sessionid}',
        'User-Agent': 'Dragon'
    }
    data = {
        'platform': platform,
        'ac': 'wifi',
        'is_sso': 'false',
        'account_sdk_source': 'web',
        'language': 'en',
        'region': 'US',
        'did': '1234567890123456789'
    }
    try:
        response = requests.post(unbind_url, headers=headers, data=data, timeout=5)
        if response.json().get('message') == 'success':
            return {"success": f"✅ Platform kaldırma işlemi başarılı!\nPlatform: {platform}\nKullanıcı: {username}"}
        else:
            return {"error": "❌ Platform kaldırma başarısız oldu."}
    except Exception as e:
        return {"error": f"❌ Hata oluştu: {str(e)}"}

# ----------------------------[ Telegram Bot Fonksiyonları ]----------------------------
bot = telebot.TeleBot("8331229600:AAH8wgJw_MRxkCoD1i-SPtE5njCkkmATq84")

@bot.message_handler(commands=['start'])
def start_command(message):
    """Başlangıç komutu"""
    bot.reply_to(message, "👋 Merhaba! Lütfen Session ID'nizi gönderin:")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Tüm mesajları işle"""
    sessionid = message.text.strip()
    
    # "bağlantılar siliniyor..." mesajını gönder
    status_msg = bot.reply_to(message, "⏳ Bağlantılar siliniyor...")
    
    # İşlemi biraz bekletelim ki kullanıcı mesajı görsün
    time.sleep(1)
    
    # Unbind işlemini yap
    result = unbind(sessionid)
    
    # Mesajı güncelle
    if 'success' in result:
        bot.edit_message_text(chat_id=status_msg.chat.id,
                             message_id=status_msg.message_id,
                             text=result['success'])
    else:
        bot.edit_message_text(chat_id=status_msg.chat.id,
                             message_id=status_msg.message_id,
                             text=result['error'])

# ----------------------------[ Botu Başlat ]----------------------------
if __name__ == "__main__":
    print("Bot çalışıyor...")
    bot.infinity_polling()