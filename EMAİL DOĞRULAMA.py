import telebot
import requests, secrets, user_agent
import time  # opsiyonel gecikme için

# --- Gm sınıfı aynı ---
class Gm:
    def __init__(self, email):
        self.email = email
        if "@" in self.email:
            self.email = self.email.split("@")[0]
        self.TL = None
        self.__Host_GAPS = None
        self.base_url = 'https://accounts.google.com/_/signup'
        self.headers = {
            'user-agent': user_agent.generate_user_agent(),
            'google-accounts-xsrf': '1',
        }

    def check(self):
        try:
            url = self.base_url + '/validatepersonaldetails'
            params = {'hl': "ar", '_reqid': "74404", 'rt': "j"}
            payload = {
                'f.req': "[\"AEThLlymT9V_0eW9Zw42mUXBqA3s9U9ljzwK7Jia8M4qy_5H3vwDL4GhSJXkUXTnPL_roS69KYSkaVJLdkmOC6bPDO0jy5qaBZR0nGnsWOb1bhxEY_YOrhedYnF3CldZzhireOeUd-vT8WbFd7SXxfhuWiGNtuPBrMKSLuMomStQkZieaIHlfdka8G45OmseoCfbsvWmoc7U\",\"L7N\",\"ToPython\",\"L7N\",\"ToPython\",0,0,null,null,null,0,null,1,[],1]",
                'deviceinfo': "[null,null,null,null,null,\"IQ\",null,null,null,\"GlifWebSignIn\",null,[],null,null,null,null,1,null,0,1,\"\",null,null,1,1,2]",
            }

            __Host_GAPS = ''.join(secrets.choice("qwertyuiopasdfghjklzxcvbnm") for _ in range(secrets.randbelow(16) + 15))
            cookies = {'__Host-GAPS': __Host_GAPS}

            response = requests.post(url, cookies=cookies, params=params, data=payload, headers=self.headers, timeout=10)
            if response.status_code != 200 or '",null,"' not in response.text:
                return None

            self.TL = str(response.text).split('",null,"')[1].split('"')[0]
            self.__Host_GAPS = response.cookies.get_dict().get('__Host-GAPS')

            url = self.base_url + '/usernameavailability'
            cookies = {'__Host-GAPS': self.__Host_GAPS}
            params = {'TL': self.TL}
            data = {
                'continue': 'https://mail.google.com/mail/u/0/',
                'ddm': '0',
                'flowEntry': 'SignUp',
                'service': 'mail',
                'theme': 'mn',
                'f.req': f'["TL:{self.TL}","{self.email}",0,0,1,null,0,5167]',
                'azt': 'AFoagUUtRlvV928oS9O7F6eeI4dCO2r1ig:1712322460888',
                'cookiesDisabled': 'false',
                'deviceinfo': '[null,null,null,null,null,"NL",null,null,null,"GlifWebSignIn",null,[],null,null,null,null,2,null,0,1,"",null,null,2,2]',
                'gmscoreversion': 'undefined',
                'flowName': 'GlifWebSignIn'
            }

            response = requests.post(url, params=params, cookies=cookies, headers=self.headers, data=data, timeout=10)

            if response.status_code == 200:
                if '"gf.uar",1' in response.text:
                    return {"available": True}
                else:
                    return {"available": False}
            else:
                return None

        except:
            return None

# --- Telegram Bot ---
API_TOKEN = "7292398041:AAH-hJFA37ECAumrQEoHLkv42nzcdqO25hs"
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def start_msg(message):
    bot.reply_to(message, "Merhaba! Bana sadece Gmail adresini gönder, açılmış mı değil mi kontrol edeyim.")

@bot.message_handler(func=lambda message: True)
def check_email(message):
    email = message.text.strip()
    
    # Önce kontrol ediliyor mesajı gönder
    msg = bot.send_message(message.chat.id, f"📩 {email} kontrol ediliyor...")
    
    # Gmail kontrolü
    result = Gm(email=email).check()
    
    # Mesajı güncelle
    if result is not None:
        if result['available']:
            status = "✖ Açılmamış"
        else:
            status = "✔ Açılmış"
    else:
        status = "⚠ Hata! Kontrol yapılamadı."
    
    bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                          text=f"📧 {email}\nDurum: {status}")

bot.polling()