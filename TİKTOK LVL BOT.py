import re, os, urllib.parse, random, binascii, uuid, time, secrets, string
try:
    import requests, telebot
    from MedoSigner import Argus, Gorgon, Ladon, md5
except ImportError:
    os.system('pip install requests telebot pycryptodome MedoSigner')

token = "8493218885:AAFlNgbX1h195r-kSMkkFUVi9URbUo53Er8"
bot = telebot.TeleBot(token)
kullanicilar = {}

def bilgi(username):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Android 10; Pixel 3 Build/QKQ1.200308.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.0.6394.70 Mobile Safari/537.36 trill_350402 JsSdk/1.0 NetType/MOBILE Channel=googleplay AppName/trill app_version/35.3.1 ByteLocale/en ByteFullLocale/en Region/IN AppId/1180 Spark/1.5.9.1 AppVersion/35.3.1 BytedanceWebview/d8a21c6"
    }
    try:
        tikinfo = requests.get(f'https://www.tiktok.com/@{username}', headers=headers, timeout=10).text
        info = tikinfo.split('webapp.user-detail"')[1].split('"RecommenUserList"')[0]
        id = info.split('id":"')[1].split('",')[0]
        return id
    except:
        return 'h'

def sign(params, payload: str = None, sec_device_id: str = "", cookie: str or None = None, aid: int = 1233, license_id: int = 1611921764, sdk_version_str: str = "2.3.1.i18n", sdk_version: int = 2, platform: int = 19, unix: int = None):
    x_ss_stub = md5(payload.encode('utf-8')).hexdigest() if payload is not None else None
    if not unix:
        unix = int(time.time())
    return Gorgon(params, unix, payload, cookie).get_value() | {
        "x-ladon": Ladon.encrypt(unix, license_id, aid),
        "x-argus": Argus.get_sign(params, x_ss_stub, unix, platform=platform, aid=aid, license_id=license_id, sec_device_id=sec_device_id, sdk_version=sdk_version_str, sdk_version_int=sdk_version)
    }        

def seviye_al(username):
    id = bilgi(username)
    if id == 'h':
        return 'h'
    url = f"https://webcast16-normal-no1a.tiktokv.eu/webcast/user/?request_from=profile_card_v2&request_from_scene=1&target_uid={id}&iid={random.randint(1, 10**19)}&device_id={random.randint(1, 10**19)}&ac=wifi&channel=googleplay&aid=1233&app_name=musical_ly&version_code=300102&version_name=30.1.2&device_platform=android&os=android&ab_version=30.1.2&ssmix=a&device_type=RMX3511&device_brand=realme&language=ar&os_api=33&os_version=13&openudid={binascii.hexlify(os.urandom(8)).decode()}&manifest_version_code=2023001020&resolution=1080*2236&dpi=360&update_version_code=2023001020&_rticket={round(random.uniform(1.2, 1.6) * 100000000) * -1}4632&current_region=IQ&app_type=normal&sys_region=IQ&mcc_mnc=41805&timezone_name=Asia%2FBaghdad&carrier_region_v2=418&residence=IQ&app_language=ar&carrier_region=IQ&ac2=wifi&uoo=0&op_region=IQ&timezone_offset=10800&build_number=30.1.2&host_abi=arm64-v8a&locale=ar&region=IQ&content_language=gu%2C&ts={round(random.uniform(1.2, 1.6) * 100000000) * -1}&cdid={uuid.uuid4()}&webcast_sdk_version=2920&webcast_language=ar&webcast_locale=ar_IQ"
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023001020 (Linux; U; Android 13; ar; RMX3511; Build/TP1A.220624.014; Cronet/TTNetVersion:06d6a583 2023-04-17 QuicVersion:d298137e 2023-02-13)"
    }
    headers.update(sign(url.split('?')[1], '', "AadCFwpTyztA5j9L" + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(9)), None, 1233))
    try:
        response = requests.get(url, headers=headers)
        level = re.search(r'"default_pattern":"(.*?)"', response.text).group(1)
        return int(level.split('المستوى رقم ')[1])
    except:
        return 'h'

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, """
Canlı yayın destek seviyesini öğrenme botuna hoş geldiniz

Kullanıcı adını gönderin
""")
    kullanicilar[message.chat.id] = True

@bot.message_handler(func=lambda message: True)
def hh(message):
    if kullanicilar.get(message.chat.id) == True:
        username = message.text.strip().replace("@", "")
        bot.send_message(message.chat.id, f"@{username} için arama yapılıyor")
        level = seviye_al(username)
        if level is not None and level != 'h':
            bot.send_message(message.chat.id, f"Canlı yayın destek seviyesi: {level}")
        else:
            bot.send_message(message.chat.id, "Bilgi bulunamadı, lütfen tekrar deneyin")
    else:
        bot.send_message(message.chat.id, "Başlamak için /start yazın.")

bot.polling()