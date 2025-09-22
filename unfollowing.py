#مسموح تغير حقوق بس غير مبري الذمة اذا تبعية
#@QQZ99
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import random
import json
import SignerPy
import threading
import queue
import re
import concurrent.futures
import time

BOT_TOKEN = "8269599959:AAGLiUJ-wS7KlOn2Q-OS1xlusQQWEhp7AB8"

bot = telebot.TeleBot(BOT_TOKEN)
DEVELOPER_USERNAME = "@BY_ZeuSx"  


user_states = {}
user_sessions = {}
user_actions = {}
user_threads = {}
device_id = str(random.randint(10**18, 10**19 - 1))
sayid = requests.session()


def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Videoları Gizle", callback_data="make_private"),
        InlineKeyboardButton("Beğenileri Kaldır", callback_data="unlike"),
        InlineKeyboardButton("Takipleri Kaldır", callback_data="unfollow"),
        InlineKeyboardButton("Favori Videoları Kaldır", callback_data="uncollect"),
        InlineKeyboardButton("Session Çek", url="https://vt.tiktok.com/ZSkUaFXQf/"),
        InlineKeyboardButton("Programcı", url=f"https://t.me/{DEVELOPER_USERNAME[1:]}")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    KANAL_ID = "@ByzeusxToolmain"              # Kanal username veya ID
    KANAL_LINK = "https://t.me/ByzeusxToolmain"  # Kullanıcının katılacağı link

    user_id = message.from_user.id

    # Kanal üyeliğini kontrol et
    try:
        member = bot.get_chat_member(KANAL_ID, user_id)
        if member.status in ["left", "kicked"]:
            bot.send_message(
                message.chat.id,
                f"❌ Botu kullanmak için önce kanala katılmanız gerekiyor!\n"
                f"Katılmak için tıklayın: {KANAL_LINK}"
            )
            return  # Üye değilse ana menü gösterme
    except Exception as e:
        bot.send_message(
            message.chat.id,
            "❌ Kanal kontrolü sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin."
        )
        return

    # Eğer kullanıcı kanala üyeyse ana menüyü göster
    bot.send_message(
        message.chat.id,
        "- TikTok Hizmetler Botuna Hoşgeldiniz\nLütfen bir hizmet seçin:",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if call.data == "make_private":
        bot.answer_callback_query(call.id)
        user_actions[user_id] = "make_private"
        bot.send_message(chat_id, "Videolarınızı gizlemek için hesabınızın sessionid bilgisini gönderin.")
    
    elif call.data == "unlike":
        bot.answer_callback_query(call.id)
        user_actions[user_id] = "unlike"
        bot.send_message(chat_id, "Beğenileri kaldırmak için hesabınızın sessionid bilgisini gönderin.")
    
    elif call.data == "unfollow":
        bot.answer_callback_query(call.id)
        user_actions[user_id] = "unfollow"
        bot.send_message(chat_id, "Takipleri kaldırmak için hesabınızın sessionid bilgisini gönderin.")
    
    elif call.data == "uncollect":
        bot.answer_callback_query(call.id)
        user_actions[user_id] = "uncollect"
        bot.send_message(chat_id, "Favori videoları kaldırmak için hesabınızın sessionid bilgisini gönderin.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    session_id = message.text.strip()
    
    if not session_id:
        bot.send_message(chat_id, "Session ID boş olamaz.")
        return
    
    action = user_actions.get(user_id)
    
    if action == "make_private":
        bot.send_message(chat_id, "Hesap verileri alınıyor ve videolar gizleniyor...")
        threading.Thread(target=run_privater, args=(session_id, chat_id)).start()
    
    elif action == "unlike":
        user_states[chat_id] = {
            'state': 'running',
            'cookies': {
                'sid_tt': session_id,
                'sessionid': session_id,
                'sessionid_ss': session_id,
            }
        }
        msg = bot.send_message(chat_id, "Session alındı, işlem başlatılıyor...")
        threading.Thread(target=run_unlike_process, args=(chat_id, msg)).start()
    
    elif action == "unfollow":
        sent = bot.send_message(chat_id, "Takipler kaldırılıyor, lütfen bekleyin...")
        threading.Thread(target=start_unfollow_process, args=(session_id, sent)).start()
    
    elif action == "uncollect":
        if chat_id in user_sessions:
            bot.send_message(chat_id, "İşlem zaten çalışıyor, lütfen bitmesini bekleyin veya botu yeniden başlatın.")
            return
        
        user_sessions[chat_id] = {
            "sessionid": session_id,
            "counter": [0],
            "lock": threading.Lock(),
            "used_aweme_ids": set()
        }
        
        sent_msg = bot.send_message(chat_id, "İşlemler yürütülüyor...")
        user_sessions[chat_id]["msg_id"] = sent_msg.message_id
        
        threads = []
        for _ in range(10):
            t = threading.Thread(
                target=worker_thread,
                args=(
                    chat_id,
                    session_id,
                    user_sessions[chat_id]["counter"],
                    user_sessions[chat_id]["used_aweme_ids"],
                    user_sessions[chat_id]["lock"]
                ),
                daemon=True
            )
            t.start()
            threads.append(t)
        
        user_threads[chat_id] = threads
    
    else:
        bot.send_message(chat_id, "hiçbir işlem seçilmedi,lütfen bir işlem seçin")


def get_info_url(cookies_common):
    headers = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36',
    }

    cookies2 = cookies_common.copy()
    cookies2['_ttp'] = '2vgirjOnuSrSOnprbKT4f6H0h4U'
    cookies2['tt_chain_token'] = 'aI+tyWRBH/hxDwK2jQqVFg=='

    url = "https://www.tiktok.com/passport/web/account/info/?WebIdLastTime=1745948418&aid=1459&app_language=ar&app_name=tiktok_web&device_platform=web_mobile&referer=https%3A%2F%2Fwww.tiktok.com%2F&region=IQ"
    
    response = requests.get(url, headers=headers, cookies=cookies2)
    try:
        data = response.json()
        user_id = data["data"]["user_id"]
        sec_user_id = data["data"]["sec_user_id"]
        return sec_user_id
    except Exception as e:
        print("Veri çekme sırasında hata oluştu:", e)
        return None

def get_favorites_res(sec_user_id, cookies_common):
    if not sec_user_id:
        print("İşlem sec_user_id olmadan tamamlanamaz")
        return None

    url = f"https://api22-normal-c-alisg.tiktokv.com/aweme/v1/aweme/favorite/?invalid_item_count=0&is_hiding_invalid_item=0&max_cursor=0&sec_user_id={sec_user_id}&count=20&device_platform=android&os=android&ssmix=a&_rticket=1753109121957&cdid=95a630da-629a-454f-8669-3de93f7684df&channel=googleplay&aid=1233&app_name=musical_ly&version_code=370104&version_name=37.1.4&manifest_version_code=2023701040&update_version_code=2023701040&ab_version=37.1.4&resolution=900*1600&dpi=300&device_type=ASUS_I003DD&device_brand=Asus&language=ar&os_api=28&os_version=9&ac=wifi&is_pad=0&current_region=IQ&app_type=normal&sys_region=IQ&last_install_time=1752974585&mcc_mnc=41840&timezone_name=Asia%2FShanghai&residence=IQ&app_language=ar&carrier_region=IQ&timezone_offset=28800&host_abi=arm64-v8a&locale=ar&ac2=wifi&uoo=0&op_region=IQ&build_number=37.1.4&region=IQ&ts=1753098321&iid=7528875149459736327&device_id=7528874837760067090&openudid=52eca32979e92633"
    
    sayid.cookies.update(cookies_common)
    params = {"device_id": device_id, "os_version": "9", "app_version": "37.8.5"}
    H = SignerPy.sign(params=params, cookie=cookies_common)

    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023701040 (Linux; U; Android 9; ar; ASUS_I003DD; Build/PI;tt-ok/3.12.13.4-tiktok)",
        'x-ss-req-ticket': H['x-ss-req-ticket'],
        'x-ladon': H['x-ladon'],
        'x-khronos': H['x-khronos'],
        'x-argus': H['x-argus'],
        'x-gorgon': H['x-gorgon'],
    }

    try:
        res = sayid.get(url, headers=headers, cookies=cookies_common)  
        data = res.json()
        aweme_ids = [aweme['aweme_id'] for aweme in data.get('aweme_list', [])]
        unique_ids = list(set(aweme_ids))
        return unique_ids
    except Exception as e:
        print(f"Favoriler alınırken hata oluştu: {e}")
        return None

def digg_aweme_res1(aweme, cookies_common):
    if not aweme:
        return False, "Aweme ID bulunamadı."
        
    url1 = f"https://api22-normal-c-alisg.tiktokv.com/aweme/v1/commit/item/digg/?aweme_id={aweme}&enter_from=personal_homepage&friends_upvote=false&type=0&channel_id=3&iid=7528875149459736327&device_id=7528874837760067090&ac=WIFI&channel=googleplay&aid=1233&app_name=musical_ly&version_code=370104&version_name=37.1.4&device_platform=android&os=android&ab_version=37.1.4&ssmix=a&device_type=ASUS_I003DD&device_brand=Asus&language=ar&os_api=28&os_version=9&openudid=52eca32979e92633&manifest_version_code=2023701040&resolution=1600*900&dpi=300&update_version_code=2023701040&_rticket=1753113560549&is_pad=0&app_type=normal&sys_region=IQ&last_install_time=1753113273&mcc_mnc=41840&timezone_name=Asia%2FShanghai&app_language=ar&carrier_region=IQ&ac2=wifi&uoo=0&op_region=IQ&timezone_offset=28800&build_number=37.1.4&host_abi=arm64-v8a&locale=ar&region=IQ&ts=1753102760&cdid=1e5c1ae9-5cf8-4879-95f0-5edde2352b57"

    sayid.cookies.update(cookies_common)
    params2 = {"device_id": device_id, "os_version": "9", "app_version": "37.8.5"}
    H1 = SignerPy.sign(params=params2, cookie=cookies_common)

    headers2 = {
        'User-Agent': "com.zhiliaoapp.musically/2023701040...",
        'x-ss-req-ticket': H1['x-ss-req-ticket'],
        'x-ladon': H1['x-ladon'],
        'x-khronos': H1['x-khronos'],
        'x-argus': H1['x-argus'],
        'x-gorgon': H1['x-gorgon'],
    }

    try:
        res1 = sayid.get(url1, headers=headers2, cookies=cookies_common)
        res_json = res1.json()
        success = res_json.get("status_code") == 0 and res_json.get("is_digg") == 1
        return success, json.dumps(res_json, indent=2, ensure_ascii=False)
    except Exception as e:
        return False, f"İşlem sırasında hata oluştu: {e}"

def run_unlike_process(chat_id, msg):
    user_data = user_states.get(chat_id)
    if not user_data or 'cookies' not in user_data:
        bot.edit_message_text("Session bulunamadı.", chat_id, msg.message_id)
        return

    cookies_common = user_data['cookies']
    sec_user_id = get_info_url(cookies_common)
    if not sec_user_id:
        bot.edit_message_text("Sec_user_id alınamadı.", chat_id, msg.message_id)
        return

    like_count = [0] 
    like_count_lock = threading.Lock()

    bot.edit_message_text(f"Beğenileri kaldırma işlemi başlatıldı\nKaldırılan beğeni sayısı: {like_count[0]}", chat_id, msg.message_id)

    while True:
        aweme_ids = get_favorites_res(sec_user_id, cookies_common)
        if not aweme_ids:
            break

        aweme_queue = queue.Queue()
        for aweme in aweme_ids:
            aweme_queue.put(aweme)

        threads = []
        for _ in range(20):  
            t = threading.Thread(target=worker, args=(aweme_queue, cookies_common, chat_id, msg, like_count_lock, like_count))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    bot.edit_message_text(f"İşlem başarıyla tamamlandı.\nKaldırılan beğeni sayısı: {like_count[0]}", chat_id, msg.message_id)

def worker(aweme_queue, cookies_common, chat_id, msg, like_count_lock, like_count):
    while True:
        try:
            aweme = aweme_queue.get_nowait()
        except queue.Empty:
            break

        success, _ = digg_aweme_res1(aweme, cookies_common)
        if success:
            with like_count_lock:
                like_count[0] += 1
    try:
    	bot.edit_message_text(f"Beğenileri kaldırma işlemi başlatıldı\nKaldırılan beğeni sayısı: {like_count[0]}", chat_id, msg.message_id)
    except:
    	pass
    finally:
    	aweme_queue.task_done()


def generate_signed_headers(device_id, cookies):
    params = {
        "device_id": device_id,
        "os_version": "9",
        "app_version": "37.8.5"
    }
    signed = SignerPy.sign(params=params, cookie=cookies)
    return {
        'User-Agent': 'com.zhiliaoapp.musically/2023701040 (Linux; U; Android 9; ar; ASUS_I003DD; Build/PI;tt-ok/3.12.13.4-tiktok)',
        'x-ss-req-ticket': signed['x-ss-req-ticket'],
        'x-ladon': signed['x-ladon'],
        'x-khronos': signed['x-khronos'],
        'x-argus': signed['x-argus'],
        'x-gorgon': signed['x-gorgon'],
    }

def get_account_info(cookies):
    url = "https://www.tiktok.com/passport/web/account/info/?WebIdLastTime=1745948418&aid=1459&app_language=ar&app_name=tiktok_web&device_platform=web_mobile&referer=https%3A%2F%2Fwww.tiktok.com%2F&region=IQ"
    headers = {'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36'}
    res = requests.get(url, headers=headers, cookies=cookies, timeout=10)
    data = res.json()["data"]
    return data["user_id"], data["sec_user_id"]

def get_following(user_id, sec_user_id, headers, session):
    url = f"https://api22-normal-c-alisg.tiktokv.com/aweme/v1/user/following/list/?user_id={user_id}&sec_user_id={sec_user_id}&max_time=0&count=40&offset=0&source_type=1&address_book_access=1&page_token&live_sort_by=1&device_platform=android&os=android&ssmix=a&_rticket=1753184870041&cdid=1e5c1ae9-5cf8-4879-95f0-5edde2352b57&channel=googleplay&aid=1233&app_name=musical_ly&version_code=370104&version_name=37.1.4&manifest_version_code=2023701040&update_version_code=2023701040&ab_version=37.1.4&resolution=900*1600&dpi=300&device_type=ASUS_I003DD&device_brand=Asus&language=ar&os_api=28&os_version=9&ac=wifi&is_pad=0&current_region=IQ&app_type=normal&sys_region=IQ&last_install_time=1753113273&mcc_mnc=41840&timezone_name=Asia%2FShanghai&residence=IQ&app_language=ar&carrier_region=IQ&timezone_offset=28800&host_abi=arm64-v8a&locale=ar&ac2=wifi&uoo=0&op_region=IQ&build_number=37.1.4&region=IQ&ts=1753174069&iid=7528875149459736327&device_id=7528874837760067090&openudid=52eca32979e92633"
    response = session.get(url, headers=headers)
    return re.findall(r'"sec_uid":"(.*?)".*?"uid":"(.*?)"', response.text)

def unfollow_user(uid, sec_uid, headers, cookies):
    url = f"https://api22-normal-c-alisg.tiktokv.com/aweme/v1/commit/follow/user/?user_id={uid}&sec_user_id={sec_uid}&type=0&channel_id=-1&from=0&from_pre=31&action_time=1753185504510&is_network_available=true&device_platform=android&os=android&ssmix=a&_rticket=1753185504517&cdid=1e5c1ae9-5cf8-4879-95f0-5edde2352b57&channel=googleplay&aid=1233&app_name=musical_ly&version_code=370104&version_name=37.1.4&manifest_version_code=2023701040&update_version_code=2023701040&ab_version=37.1.4&resolution=900*1600&dpi=300&device_type=ASUS_I003DD&device_brand=Asus&language=ar&os_api=28&os_version=9&ac=wifi&is_pad=0&current_region=IQ&app_type=normal&sys_region=IQ&last_install_time=1753113273&mcc_mnc=41840&timezone_name=Asia%2FShanghai&residence=IQ&app_language=ar&carrier_region=IQ&timezone_offset=28800&host_abi=arm64-v8a&locale=ar&ac2=wifi&uoo=0&op_region=IQ&build_number=37.1.4&region=IQ&ts=1753174704&iid=7528875149459736327&device_id=7528874837760067090&openudid=52eca32979e92633"
    try:
        requests.get(url, headers=headers, cookies=cookies, timeout=10)
        return True
    except:
        return False

def start_unfollow_process(session_id, message):
    device_id = str(random.randint(10**18, 10**19 - 1))
    cookies = {
        'sid_tt': session_id,
        'sessionid': session_id,
        'sessionid_ss': session_id,
    }
    session = requests.Session()
    session.cookies.update(cookies)

    try:
        user_id, sec_user_id = get_account_info(cookies)
    except:
        bot.edit_message_text("Hesap verileri alınamadı, lütfen sessionid bilgisini kontrol edin", message.chat.id, message.message_id)
        return

    headers = generate_signed_headers(device_id, cookies)
    count = 0
    while True:
        matches = get_following(user_id, sec_user_id, headers, session)
        if not matches:
            bot.edit_message_text(f"{count} hesabın takibi başarıyla kaldırıldı", message.chat.id, message.message_id)
            break

        with concurrent.futures.ThreadPoolExecutor(max_workers=35) as executor:
            futures = []
            for sec_uid, uid in matches:
                futures.append(executor.submit(unfollow_user, uid, sec_uid, headers, cookies))

            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    count += 1
                    try:
                        bot.edit_message_text(f"{count} hesabın takibi kaldırıldı", message.chat.id, message.message_id)
                    except:
                        pass


def get_aweme_id(session, cookie):
    device_id = str(random.randint(10**18, 10**19 - 1))
    url = "https://api22-normal-c-alisg.tiktokv.com/aweme/v1/aweme/listcollection/?sov_client_enable=1&cursor=0&count=20&device_platform=android&os=android&ssmix=a&_rticket=1753228150910&cdid=1e5c1ae9-5cf8-4879-95f0-5edde2352b57&channel=googleplay&aid=1233&app_name=musical_ly&version_code=370104&version_name=37.1.4&manifest_version_code=2023701040&update_version_code=2023701040&ab_version=37.1.4&resolution=1600*900&dpi=300&device_type=ASUS_I003DD&device_brand=Asus&language=ar&os_api=28&os_version=9&ac=wifi&is_pad=0&current_region=IQ&app_type=normal&sys_region=IQ&last_install_time=1753113273&mcc_mnc=41840&timezone_name=Asia%2FShanghai&residence=IQ&app_language=ar&carrier_region=IQ&timezone_offset=28800&host_abi=arm64-v8a&locale=ar&ac2=wifi&uoo=0&op_region=IQ&build_number=37.1.4&region=IQ&ts=1753221731&iid=7528875149459736327&device_id=7528874837760067090&openudid=52eca32979e92633"
    params = {"device_id": device_id, "os_version": "9", "app_version": "37.8.5"}
    H = SignerPy.sign(params=params, cookie=cookie)
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023701040 (Linux; U; Android 9; ar; ASUS_I003DD; Build/PI;tt-ok/3.12.13.4-tiktok)",
        'x-ss-req-ticket': H['x-ss-req-ticket'],
        'x-ladon': H['x-ladon'],
        'x-khronos': H['x-khronos'],
        'x-argus': H['x-argus'],
        'x-gorgon': H['x-gorgon'],
    }
    response = session.get(url, headers=headers)
    data = response.json()
    aweme_list = data.get('aweme_list', [])
    if not aweme_list:
        raise ValueError("Listede video bulunamadı.")
    aweme_ids = [item['aweme_id'] for item in aweme_list]
    return aweme_ids, headers

def uncollect_aweme(aweme_id, session, headers):
    url = f"https://api22-normal-c-alisg.tiktokv.com/aweme/v1/aweme/collect/?aweme_id={aweme_id}&action=0&collect_privacy_setting=0&device_platform=android&os=android&ssmix=a&_rticket=1753230028147&cdid=1e5c1ae9-5cf8-4879-95f0-5edde2352b57&channel=googleplay&aid=1233&app_name=musical_ly&version_code=370104&version_name=37.1.4&manifest_version_code=2023701040&update_version_code=2023701040&ab_version=37.1.4&resolution=1600*900&dpi=300&device_type=ASUS_I003DD&device_brand=Asus&language=ar&os_api=28&os_version=9&ac=wifi&is_pad=0&current_region=IQ&app_type=normal&sys_region=IQ&last_install_time=1753113273&mcc_mnc=41840&timezone_name=Asia%2FShanghai&residence=IQ&app_language=ar&carrier_region=IQ&timezone_offset=28800&host_abi=arm64-v8a&locale=ar&ac2=wifi&uoo=0&op_region=IQ&build_number=37.1.4&region=IQ&ts=1753223608&iid=7528875149459736327&device_id=7528874837760067090&openudid=52eca32979e92633"
    response = session.get(url, headers=headers)
    return response.text

def worker_thread(chat_id, sessionid, counter, used_aweme_ids, lock):
    cookie = {
        "sid_tt": sessionid,
        "sessionid": sessionid,
        "sessionid_ss": sessionid,
    }
    session = requests.session()
    session.cookies.update(cookie)

    while True:
        try:
            aweme_ids, headers = get_aweme_id(session, cookie)

            aweme_id = None
            with lock:
                for aid in aweme_ids:
                    if aid not in used_aweme_ids:
                        aweme_id = aid
                        used_aweme_ids.add(aid)
                        break

            if aweme_id is None:
                try:
                    bot.edit_message_text(chat_id=chat_id,
                                      message_id=user_sessions[chat_id]['msg_id'],
text=f"Favorilere eklenen {counter[0]} video kaldırıldı")
                except Exception:
                    pass
                break

            uncollect_aweme(aweme_id, session, headers)

            with lock:
                counter[0] += 1
                current_count = counter[0]

            if current_count % 10 == 0:
                try:
                    bot.edit_message_text(chat_id=chat_id,
                                      message_id=user_sessions[chat_id]['msg_id'],
                                      text= f"{current_count} video favorilerden kaldırıldı")
                except Exception:
                    pass

            time.sleep(0.5)

        except ValueError as ve:
            if str(ve) =="Hesapta video bulunamadı.":
                try:
                    bot.edit_message_text(chat_id=chat_id,
message_id=user_sessions[chat_id]['msg_id'],
    text=f"Favorilerden {counter[0]} video kaldırıldı"
)
                except Exception:
                    pass
                break
            else:
                try:
                    bot.edit_message_text(chat_id=chat_id,
                                      message_id=user_sessions[chat_id]['msg_id'],
                                      text=f"Hata: {ve}")
                except Exception:
                    pass
                break

        except Exception as e:
            try:
                bot.edit_message_text(chat_id=chat_id,
                                  message_id=user_sessions[chat_id]['msg_id'],
                                  text=f"Beklenmeyen hata: {e}")
            except Exception:
                pass
            break


def safe_edit(bot, chat_id, message_id, new_text):
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text)
    except Exception as e:
        if "message is not modified" in str(e):
            pass

def run_privater(sessionid, chat_id):
    headers = {
        'User-Agent': 'com.zhiliaoapp.musically.go/370402 (Linux; Android 13; ar; RMO-NX1; Build/HONORRMO-N21;tt-ok/3.12.13.27-ul)',
    }
    cookies = {
        'sessionid': sessionid,
        'sessionid_ss': sessionid,
        'sid_tt': sessionid,
        'sid_guard': f"{sessionid}%7C1748273431%7C15552000%7CSat%2C+22-Nov-2025+15%3A30%3A31+GMT",
    }

    try:
        r = requests.get("https://www.tiktok.com/passport/web/account/info/", headers=headers, cookies=cookies)
        r.raise_for_status()
        data = r.json().get("data", {})
        sec_user_id = data.get("sec_user_id")
        user_id_api = data.get("user_id")
        if not sec_user_id or not user_id_api:
            bot.send_message(chat_id, " لم يتم العثور على user_id أو sec_user_id.")
            return
    except Exception as e:
        bot.send_message(chat_id, f"Hesap verileri alınırken hata oluştu: {e}")
        return

    converted_total = 0
    cursor = 0

    status_message = bot.send_message(chat_id, f"0 video gizli moda geçirildi")

    while True:
        url = f'https://api16-normal-c-alisg.tiktokv.com/lite/v2/public/item/list/?source=0&sec_user_id={sec_user_id}&user_id={user_id_api}&count=100&filter_private=1&lite_flow_schedule=new&cdn_cache_is_login=1&cdn_cache_strategy=v0&manifest_version_code=370402&_rticket=1748288467350&app_language=ar&app_type=normal&iid=7508467361403537168&app_package=com.zhiliaoapp.musically.go&channel=googleplay&device_type=RMO-NX1&language=ar&host_abi=arm64-v8a&locale=ar&resolution=1080*2316&openudid=cdb37c989aff6fff&update_version_code=370402&ac2=0&cdid=cb9b5af7-4256-45ab-a24d-e471a7f46569&sys_region=IQ&os_api=33&timezone_name=Asia%2FBaghdad&dpi=480&carrier_region=IQ&ac=mobile&device_id=7384884129483900421&os_version=13&timezone_offset=10800&version_code=370402&app_name=musically_go&ab_version=37.4.2&version_name=37.4.2&device_brand=HONOR&op_region=IQ&ssmix=a&device_platform=android&build_number=37.4.2&region=IQ&aid=1340&ts=1748252427'

        try:
            r = requests.get(url, headers=headers, cookies=cookies)
            r.raise_for_status()
            json_data = r.json()
            aweme_list = json_data.get("aweme_list", [])
            has_more = json_data.get("has_more", False)
            cursor = json_data.get("cursor", 0)

            if not aweme_list:
                break  

            aweme_ids = [item.get("aweme_id") for item in aweme_list if item.get("aweme_id")]

            for aweme_id in aweme_ids:
                mod_url = f'https://api19-normal-c-alisg.tiktokv.com/aweme/v1/aweme/modify/visibility/?aweme_id={aweme_id}&type=2'
                mod_res = requests.get(mod_url, headers=headers, cookies=cookies)

                if mod_res.status_code == 200:
                    converted_total += 1
                    new_text = f"{converted_total} video gizli moda geçirildi"
                    safe_edit(bot, chat_id, status_message.message_id, new_text)

            if not has_more:
                break

        except Exception as e:
            bot.send_message(chat_id, f"İşlem sırasında hata oluştu: {e}")
            break
    
    try:
        final_text = f"{converted_total} video gizli moda geçirildi"
        bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=final_text)
    except:
        bot.delete_message(chat_id, status_message.message_id)
        bot.send_message(chat_id, f"{converted_total} video gizli moda geçirildi")

bot.infinity_polling()
