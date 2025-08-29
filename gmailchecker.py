from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram import filters
import requests

# Telegram Bot Token
TOKEN = "8451583637:AAEPo_dDgFLVJxWjD1Lx5srFMSAKdOTsZws"
# ZeroBounce API key
API_KEY = "fc58f137bc5d46c6bd0786b7c1d7400c"

# Kullanıcıların start komutunu kullanıp kullanmadığını saklamak için
started_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in started_users:
        await update.message.reply_text("Merhaba! Bana bir e-posta gönder, Gmail olup olmadığını söyleyeyim.")
        started_users.add(user_id)
    else:
        await update.message.reply_text("Zaten başlattınız, şimdi bir e-posta gönderebilirsiniz.")

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:  # None kontrolü
        email = update.message.text.strip()
        result = check_email(email)
        await update.message.reply_text(result)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()