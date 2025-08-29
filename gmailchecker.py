from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests

# Telegram Bot Token
TOKEN = "7488416267:AAFJYwF7_Y_78DPWisD3plAuOsJ0UDqyw3s"
# ZeroBounce API key
API_KEY = "fc58f137bc5d46c6bd0786b7c1d7400c"

# Kullanıcıların start komutunu kullanıp kullanmadığını saklamak için
started_users = set()

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in started_users:
        update.message.reply_text("Merhaba! Bana bir e-posta gönder, Gmail olup olmadığını söyleyeyim.")
        started_users.add(user_id)
    else:
        update.message.reply_text("Zaten başlattınız, şimdi bir e-posta gönderebilirsiniz.")

def check_email(email):
    url = f"https://api.zerobounce.net/v2/validate?api_key={API_KEY}&email={email}"
    response = requests.get(url)
    data = response.json()
    status = data.get('status', 'unknown')

    if status == 'valid':
        if "@gmail.com" in email.lower():
            return "Gmail var ✅"
        else:
            return "Gmail yok ❌"
    else:
        return "Geçersiz e-posta ❌"

def handle_message(update: Update, context: CallbackContext):
    email = update.message.text.strip()
    result = check_email(email)
    update.message.reply_text(result)

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()