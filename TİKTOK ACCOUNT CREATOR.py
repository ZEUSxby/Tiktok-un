import requests
import SignerPy
import secrets
import logging
import telebot
from telebot.types import ReplyKeyboardRemove
from telebot.handler_backends import State, StatesGroup
from telebot import custom_filters
from typing import Dict, Any

# Logging ayarı - Sadece hataları göster
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)

# Özel log seviyeleri ayarla
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('telebot').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Durumları tanımla
class UserStates(StatesGroup):
    email = State()
    password = State()
    code = State()

class TikTokBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.user_sessions = {}
        self.setup_handlers()

    def setup_handlers(self):
        # Komut handler'ları
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            self.start(message)

        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            self.help_command(message)

        @self.bot.message_handler(commands=['create'])
        def create_account_command(message):
            self.create_account(message)

        @self.bot.message_handler(commands=['cancel'])
        def cancel_command(message):
            self.cancel(message)

        # Durum handler'ları
        @self.bot.message_handler(state=UserStates.email)
        def get_email(message):
            self.get_email(message)

        @self.bot.message_handler(state=UserStates.password)
        def get_password(message):
            self.get_password(message)

        @self.bot.message_handler(state=UserStates.code)
        def get_verification_code(message):
            self.get_verification_code(message)

    def start(self, message):
        """Botu başlatan komut"""
        user = message.from_user
        welcome_text = f"""
🤖 Merhaba {user.first_name}!

TikTok hesabı oluşturma botuna hoş geldiniz.

📝 Özellikler:
• TikTok hesabı oluşturma
• E-posta doğrulama
• Otomatik kayıt

🛠 Komutlar:
/start - Botu başlat
/help - Yardım mesajı
/create - Yeni hesap oluştur
/cancel - İşlemi iptal et

Hesap oluşturmak için /create komutunu kullanın.
        """
        self.bot.send_message(message.chat.id, welcome_text)

    def help_command(self, message):
        """Yardım mesajı"""
        help_text = """
📖 TikTok Account Creator Bot Kullanımı:

1. /create komutu ile başlayın
2. E-posta adresinizi girin
3. Şifrenizi girin
4. E-postanıza gelen doğrulama kodunu girin
5. Hesabınız oluşturulacak!

⚠️ Notlar:
• E-posta adresinin geçerli olduğundan emin olun
• Şifre en az 8 karakter olmalı
• Doğrulama kodu 10 dakika içinde geçerlidir
        """
        self.bot.send_message(message.chat.id, help_text)

    def create_account(self, message):
        """Hesap oluşturma işlemini başlat"""
        user_id = message.from_user.id
        
        # Kullanıcı için session oluştur
        self.user_sessions[user_id] = {
            'stage': 'email',
            'creator': TikTokAccountCreator()
        }
        
        self.bot.set_state(user_id, UserStates.email, message.chat.id)
        self.bot.send_message(
            message.chat.id,
            "📧 Lütfen TikTok hesabı için kullanmak istediğiniz e-posta adresini girin:"
        )

    def get_email(self, message):
        """E-posta adresini al"""
        user_id = message.from_user.id
        email = message.text.strip()
        
        # Basit e-posta validasyonu
        if '@' not in email or '.' not in email:
            self.bot.send_message(message.chat.id, "❌ Geçersiz e-posta formatı. Lütfen tekrar deneyin:")
            return
        
        self.user_sessions[user_id]['email'] = email
        self.user_sessions[user_id]['stage'] = 'password'
        
        self.bot.set_state(user_id, UserStates.password, message.chat.id)
        self.bot.send_message(
            message.chat.id,
            "🔐 Lütfen hesap şifresini girin (en az 8 karakter):"
        )

    def get_password(self, message):
        """Şifreyi al"""
        user_id = message.from_user.id
        password = message.text.strip()
        
        if len(password) < 8:
            self.bot.send_message(message.chat.id, "❌ Şifre en az 8 karakter olmalı. Lütfen tekrar deneyin:")
            return
        
        self.user_sessions[user_id]['password'] = password
        
        # Doğrulama kodu gönder
        self.bot.send_message(message.chat.id, "⏳ Doğrulama kodu gönderiliyor...")
        
        try:
            creator = self.user_sessions[user_id]['creator']
            email = self.user_sessions[user_id]['email']
            
            response = creator.send_code_request(email, password)
            
            if "email_ticket" in str(response):
                self.bot.set_state(user_id, UserStates.code, message.chat.id)
                self.bot.send_message(
                    message.chat.id,
                    "✅ Doğrulama kodu e-posta adresinize gönderildi!\n\n"
                    "📨 Lütfen e-postanızı kontrol edin ve doğrulama kodunu girin:"
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    f"❌ Doğrulama kodu gönderilemedi: {response}\n\n"
                    "Lütfen /create komutu ile tekrar deneyin."
                )
                self.bot.delete_state(user_id, message.chat.id)
                if user_id in self.user_sessions:
                    del self.user_sessions[user_id]
                
        except Exception as e:
            logger.error(f"Error sending code: {e}")
            self.bot.send_message(
                message.chat.id,
                f"❌ Bir hata oluştu: {str(e)}\n\n"
                "Lütfen daha sonra tekrar deneyin."
            )
            self.bot.delete_state(user_id, message.chat.id)
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]

    def get_verification_code(self, message):
        """Doğrulama kodunu al ve hesabı oluştur"""
        user_id = message.from_user.id
        code = message.text.strip()
        
        if not code.isdigit() or len(code) != 6:
            self.bot.send_message(message.chat.id, "❌ Geçersiz kod formatı. 6 haneli kodu girin:")
            return
        
        self.bot.send_message(message.chat.id, "⏳ Hesap oluşturuluyor...")
        
        try:
            creator = self.user_sessions[user_id]['creator']
            email = self.user_sessions[user_id]['email']
            password = self.user_sessions[user_id]['password']
            
            response = creator.verify_code(email, code, password)
            
            if response.get('data') and 'session_key' in response['data']:
                # Hesap başarıyla oluşturuldu
                session_id = response['data']['session_key']
                username = response['data'].get('name', 'Bilinmiyor')
                
                # Dosyalara kaydet
                creator.save_account(email, password, response)
                
                # Kullanıcıya bilgi ver
                success_message = f"""
✅ TikTok Hesabı Başarıyla Oluşturuldu!

📧 E-posta: {email}
🔐 Şifre: {password}
👤 Kullanıcı Adı: {username}
🔑 Session ID: {session_id[:20]}...

                """
                
                self.bot.send_message(message.chat.id, success_message)
                
            else:
                error_msg = response.get('message', 'Bilinmeyen hata')
                self.bot.send_message(
                    message.chat.id,
                    f"❌ Hesap oluşturma başarısız: {error_msg}\n\n"
                    "Lütfen /create komutu ile tekrar deneyin."
                )
                
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            self.bot.send_message(
                message.chat.id,
                f"❌ Bir hata oluştu: {str(e)}\n\n"
                "Lütfen daha sonra tekrar deneyin."
            )
        
        # Session'ı temizle
        self.bot.delete_state(user_id, message.chat.id)
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]

    def cancel(self, message):
        """İşlemi iptal et"""
        user_id = message.from_user.id
        
        # Session'ı temizle
        self.bot.delete_state(user_id, message.chat.id)
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            
        self.bot.send_message(
            message.chat.id,
            "❌ İşlem iptal edildi. Tekrar başlamak için /create komutunu kullanın.",
            reply_markup=ReplyKeyboardRemove()
        )

    def run(self):
        """Botu başlat"""
        print("🤖 TikTok Account Creator Bot başlatılıyor...")
        print("✅ Bot aktif! Şimdi Telegram'dan komut gönderebilirsiniz.")
        
        # State middleware'ini ekle
        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))
        
        self.bot.infinity_polling()

# Orijinal TikTokAccountCreator sınıfı (değişmeden)
class TikTokAccountCreator:
    def __init__(self):
        self.csrf = secrets.token_hex(16)
        self.session = requests.Session()
        self.base_params = {
            "passport-sdk-version": "6031990",
            "device_platform": "android",
            "os": "android",
            "ssmix": "a",
            "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00",
            "channel": "googleplay",
            "aid": "1233",
            "app_name": "musical_ly",
            "version_code": "370805",
            "version_name": "37.8.5",
            "manifest_version_code": "2023708050",
            "update_version_code": "2023708050",
            "ab_version": "37.8.5",
            "resolution": "900*1600",
            "dpi": "240",
            "device_type": "NE2211",
            "device_brand": "OnePlus",
            "language": "en",
            "os_api": "28",
            "os_version": "9",
            "ac": "wifi",
            "is_pad": "0",
            "current_region": "TW",
            "app_type": "normal",
            "sys_region": "US",
            "last_install_time": "1752871588",
            "mcc_mnc": "46692",
            "timezone_name": "Asia/Baghdad",
            "carrier_region_v2": "466",
            "residence": "TW",
            "app_language": "en",
            "carrier_region": "TW",
            "timezone_offset": "10800",
            "host_abi": "arm64-v8a",
            "locale": "en-GB",
            "ac2": "wifi",
            "uoo": "0",
            "op_region": "TW",
            "build_number": "37.8.5",
            "region": "GB",
            "iid": "7528525992324908807",
            "device_id": "7528525775047132680",
            "openudid": "7a59d727a58ee91e",
            "support_webview": "1",
            "reg_store_region": "tw",
            "user_selected_region": "0",
            "okhttp_version": "4.2.210.6-tiktok",
            "use_store_region_cookie": "1",
            "app_version": "37.8.5"
        }
        
        self.base_headers = {
            'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211; Build/SKQ1.220617.001;tt-ok/3.12.13.16)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'x-tt-pba-enable': "1",
            'x-bd-kmsv': "0",
            'x-tt-dm-status': "login=1;ct=1;rt=8",
            'x-tt-passport-csrf-token': self.csrf,
            'sdk-version': "2",
            'passport-sdk-settings': "x-tt-token",
            'passport-sdk-sign': "x-tt-token",
            'x-tt-bypass-dp': "1",
            'oec-vc-sdk-version': "3.0.5.i18n",
            'x-vc-bdturing-sdk-version': "2.3.8.i18n",
            'x-tt-request-tag': "n=0;nr=011;bg=0"
        }
        
        self.cookies = {
            "install_id": "7528525992324908807",
            "passport_csrf_token": self.csrf,
            "passport_csrf_token_default": self.csrf,
        }
        self.session.cookies.update(self.cookies)
    
    @staticmethod
    def xor_encrypt(string: str) -> str:
        return "".join([hex(ord(c) ^ 5)[2:] for c in string])
    
    def update_timestamps(self, params: Dict[str, Any]) -> Dict[str, Any]:
        import time
        current_time = int(time.time() * 1000)
        params["_rticket"] = str(current_time)
        params["ts"] = str(current_time // 1000)
        return params
    
    def send_code_request(self, email: str, password: str) -> Dict[str, Any]:
        url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
        
        params = self.update_timestamps(self.base_params.copy())
        payload = {
            'rules_version': "v2",
            'password': self.xor_encrypt(password),
            'account_sdk_source': "app",
            'mix_mode': "1",
            'multi_login': "1",
            'type': "34",
            'email': self.xor_encrypt(email),
            'email_theme': "2"
        }
        
        signature = SignerPy.sign(params=params, payload=payload, cookie=self.cookies)
        
        headers = self.base_headers.copy()
        headers.update({
            'X-SS-STUB': signature['x-ss-stub'],
            'X-SS-REQ-TICKET': signature['x-ss-req-ticket'],
            'X-Ladon': signature['x-ladon'],
            'X-Khronos': signature['x-khronos'],
            'X-Argus': signature['x-argus'],
            'X-Gorgon': signature['x-gorgon'],
        })
        
        response = self.session.post(url, data=payload, headers=headers, params=params)
        return response.json()
    
    def verify_code(self, email: str, code: str, password: str) -> Dict[str, Any]:
        url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/register_verify_login/"
        
        params = self.update_timestamps(self.base_params.copy())
        payload = {
            'birthday': "2002-02-24",
            'fixed_mix_mode': "1",
            'code': self.xor_encrypt(code),
            'account_sdk_source': "app",
            'mix_mode': "1",
            'multi_login': "1",
            'type': "34",
            'email': self.xor_encrypt(email),
            'password': self.xor_encrypt(password)
        }
        
        signature = SignerPy.sign(params=params, payload=payload, cookie=self.cookies)
        
        headers = self.base_headers.copy()
        headers.update({
            'X-SS-STUB': signature['x-ss-stub'],
            'X-SS-REQ-TICKET': signature['x-ss-req-ticket'],
            'X-Ladon': signature['x-ladon'],
            'X-Khronos': signature['x-khronos'],
            'X-Argus': signature['x-argus'],
            'X-Gorgon': signature['x-gorgon'],
        })
        response = self.session.post(url, data=payload, headers=headers, params=params)
        return response.json()
    
    def save_account(self, email: str, password: str, response_data: Dict[str, Any]):
        try:
            session_id = response_data['data']['session_key']
            username = response_data['data']['name']
            
            with open("account.txt", "a", encoding="utf-8") as f:
                f.write(f"email: {email} | password: {password} | sessionid: {session_id} | username: {username}\n")
            
            with open("session.txt", "a", encoding="utf-8") as f:
                f.write(session_id + "\n")
                
        except Exception as e:
            print(f"❌ Error saving account: {e}")

def main():
    # Bot token'ını buraya girin
    BOT_TOKEN = "8163787323:AAG74v-QmBibvTDdLrVmKnWvAd_nEaoOjwQ"
    
    # Botu başlat
    bot = TikTokBot(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()