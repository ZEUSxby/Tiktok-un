import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
from datetime import datetime
import uuid
from telebot import apihelper

# ----------------- AYARLAR -----------------
TOKEN = "8236128766:AAFuZAsV6tSodt1nnegJgmibr3EfStvv2tg"   # -> kendi token'ını koy
ADMIN_ID = 7823668175       # -> kendi telegram id'ni koy
bot = telebot.TeleBot(TOKEN)

# ----------------- DOSYA YAPISI -----------------
DATA_DIR = "data"
RECEIPTS_DIR = os.path.join(DATA_DIR, "receipts")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ILANLAR_FILE = os.path.join(DATA_DIR, "ilanlar.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)
for path in [USERS_FILE, ILANLAR_FILE, ORDERS_FILE]:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
            
# ----------------- YARDIMCI FONKSİYONLAR -----------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_id():
    return str(uuid.uuid4())[:8]

def safe_edit(chat_id, message_id, text, reply_markup=None):
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        return message_id
    except apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            return message_id
        try:
            msg = bot.send_message(chat_id, text, reply_markup=reply_markup)
            return msg.message_id
        except:
            return message_id
    except Exception:
        try:
            msg = bot.send_message(chat_id, text, reply_markup=reply_markup)
            return msg.message_id
        except:
            return message_id
            
# ----------------- MODLAR -----------------
admin_mode = {}   # admin_id -> { message_id, action, ... }
user_mode = {}    # user_id -> { message_id, category, index, ilanlar, awaiting_receipt, buying, ... }

# ----------------- /start -----------------
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    try:
        if chat_id == ADMIN_ID:
            # admin için tek mesaj
            ensure_admin_msg(chat_id)
            show_admin_panel(chat_id)
            return

        # kullanıcı kaydı (dosyaya)
        users = load_json(USERS_FILE)
        if not any(u.get("user_id") == chat_id for u in users):
            users.append({"user_id": chat_id, "user_name": message.from_user.username})
            save_json(USERS_FILE, users)

        # kullanıcı için tek mesaj
        msg_id = ensure_user_msg(chat_id)
        # ilk ana menü
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🛍️ İlanlar", callback_data="show_categories"))
        # güncelle
        user_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "👋 Hoşgeldiniz! Aşağıdan ilanlara bakabilirsiniz.", reply_markup=markup)
    except Exception as e:
        print("start hata:", e)

# ----------------- ADMIN / USER MESAJ ID KONTROL -----------------
def ensure_admin_msg(chat_id):
    if chat_id not in admin_mode:
        admin_mode[chat_id] = {}
    if "message_id" not in admin_mode[chat_id] or admin_mode[chat_id]["message_id"] is None:
        msg = bot.send_message(chat_id, "🛠️ Admin panel yükleniyor...")
        admin_mode[chat_id]["message_id"] = msg.message_id
    return admin_mode[chat_id]["message_id"]

def ensure_user_msg(chat_id):
    if chat_id not in user_mode:
        msg = bot.send_message(chat_id, "👋 Hoşgeldiniz! Aşağıdan ilanlara bakabilirsiniz.")
        user_mode[chat_id] = {"message_id": msg.message_id}
    elif "message_id" not in user_mode[chat_id] or user_mode[chat_id]["message_id"] is None:
        msg = bot.send_message(chat_id, "👋 Hoşgeldiniz! Aşağıdan ilanlara bakabilirsiniz.")
        user_mode[chat_id]["message_id"] = msg.message_id
    return user_mode[chat_id]["message_id"]
    
# ----------------- ADMIN PANEL GÖSTER -----------------
def show_admin_panel(chat_id):
    try:
        msg_id = ensure_admin_msg(chat_id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Onaylanması Bekleyen Siparişler", callback_data="pending_orders"))
        markup.add(InlineKeyboardButton("➕ İlan Ekle", callback_data="add_ilan"))
        markup.add(InlineKeyboardButton("🗂️ İlanları Yönet", callback_data="manage_ilan"))
        text = "🛠️ Hoşgeldin Admin — Panel"
        admin_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, text, reply_markup=markup)
    except Exception as e:
        print("show_admin_panel hata:", e)

# ----------------- CALLBACK HANDLER -----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        chat_id = call.message.chat.id
        if chat_id == ADMIN_ID:
            handle_admin_callbacks(call)
        else:
            handle_user_callbacks(call)
    except Exception as e:
        print("callback_handler genel hata:", e)
        
# ----------------- ADMIN CALLBACKS -----------------
def handle_admin_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data or ""
    try:
        msg_id = ensure_admin_msg(chat_id)

        # Geri
        if data == "admin_back":
            show_admin_panel(chat_id)
            return

        # İlan ekle menüsü
        if data == "add_ilan":
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📱 TikTok", callback_data="add_tiktok"))
            markup.add(InlineKeyboardButton("📸 Instagram", callback_data="add_instagram"))
            markup.add(InlineKeyboardButton("↩️ Geri", callback_data="admin_back"))
            admin_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "📌 Hangi kategoriye ilan ekleyeceksiniz?", reply_markup=markup)
            return

        if data in ("add_tiktok", "add_instagram"):
            category = "tiktok" if data == "add_tiktok" else "instagram"
            admin_mode[chat_id]["action"] = "add_ilan"
            admin_mode[chat_id]["category"] = category
            bot.send_message(chat_id, f"📝 {category.capitalize()} ilan açıklamasını ve fiyatını girin (tek mesaj):")
            return

        # Onay bekleyen siparişler
        if data == "pending_orders":
            orders = load_json(ORDERS_FILE)
            pending = [o for o in orders if o.get("status") == "beklemede"]
            if not pending:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("↩️ Geri", callback_data="admin_back"))
                admin_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "❌ Henüz bekleyen sipariş yok.", reply_markup=markup)
                return

            text_lines = ["📋 Onaylanması Bekleyen Siparişler:\n"]
            markup = InlineKeyboardMarkup()
            for o in pending:
                text_lines.append(f"👤 {o.get('user_name')}  |  {o.get('ilan_info')}\n🕒 {o.get('date')}\n")
                markup.add(InlineKeyboardButton(f"📸 Görüntüle ({o.get('user_name')})", callback_data=f"viewreceipt_{o.get('order_id')}"))
                markup.add(InlineKeyboardButton(f"✅ Onayla ({o.get('user_name')})", callback_data=f"approve_{o.get('order_id')}"))
                markup.add(InlineKeyboardButton(f"❌ Reddet ({o.get('user_name')})", callback_data=f"reject_{o.get('order_id')}"))
            markup.add(InlineKeyboardButton("↩️ Geri", callback_data="admin_back"))
            admin_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "\n".join(text_lines), reply_markup=markup)
            return

        # Görüntüle dekont
        if data.startswith("viewreceipt_"):
            order_id = data.split("viewreceipt_", 1)[1]
            orders = load_json(ORDERS_FILE)
            order = next((x for x in orders if x.get("order_id") == order_id), None)
            if not order:
                bot.send_message(chat_id, "❌ Sipariş bulunamadı.")
                return
            receipt_file = order.get("receipt_file")
            if receipt_file:
                path = os.path.join(RECEIPTS_DIR, receipt_file)
                if os.path.exists(path):
                    try:
                        with open(path, "rb") as photo:
                            bot.send_photo(chat_id, photo, caption=f"📸 Dekont — {order.get('user_name')} / İlan: {order.get('ilan_info')}")
                    except Exception as ex:
                        bot.send_message(chat_id, f"⚠️ Dekont gönderilirken hata: {ex}")
                else:
                    bot.send_message(chat_id, "⚠️ Dekont dosyası bulunamadı.")
            else:
                bot.send_message(chat_id, "ℹ️ Bu siparişte dekont yok.")
            return
 
# Onayla
        if data.startswith("approve_"):
            order_id = data.split("approve_", 1)[1]
            orders = load_json(ORDERS_FILE)
            idx = next((i for i, x in enumerate(orders) if x.get("order_id") == order_id), None)
            if idx is None:
                bot.send_message(chat_id, "❌ Sipariş bulunamadı.")
                return
            orders[idx]["status"] = "onaylandi"
            save_json(ORDERS_FILE, orders)

            # Teslimat bilgisi girişi için admin'e sor
            admin_mode[chat_id]["action"] = "enter_delivery"
            admin_mode[chat_id]["order_id"] = order_id
            bot.send_message(chat_id, "✏️ Teslimat bilgilerini (kullanıcı adı / mail / şifre) tek mesaj olarak girin. Gönderdikten sonra kullanıcıya iletilecek.")
            return

        # Reddet
        if data.startswith("reject_"):
            order_id = data.split("reject_", 1)[1]
            orders = load_json(ORDERS_FILE)
            idx = next((i for i, x in enumerate(orders) if x.get("order_id") == order_id), None)
            if idx is None:
                bot.send_message(chat_id, "❌ Sipariş bulunamadı.")
                return
            user_id = orders[idx].get("user_id")
            orders[idx]["status"] = "reddedildi"
            save_json(ORDERS_FILE, orders)
            try:
                bot.send_message(user_id, f"❌ Siparişiniz reddedildi: {orders[idx].get('ilan_info')}")
            except Exception:
                pass
            bot.send_message(chat_id, "✅ Sipariş reddedildi ve kullanıcı bilgilendirildi.")
            return

        # İlanları yönet
        if data == "manage_ilan":
            ilanlar = load_json(ILANLAR_FILE)
            if not ilanlar:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("↩️ Geri", callback_data="admin_back"))
                admin_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "❌ Henüz ilan yok.", reply_markup=markup)
                return
            text_lines = ["🗂️ Mevcut İlanlar:\n"]
            markup = InlineKeyboardMarkup()
            for i in ilanlar:
                sold_text = " (✅ Satıldı)" if i.get("sold") else ""
                text_lines.append(f"📌 {i.get('ilan_id')} — {i.get('category').capitalize()}{sold_text}\n{i.get('description')}\n")
                markup.add(InlineKeyboardButton(f"🗑️ Sil {i.get('ilan_id')}", callback_data=f"delete_{i.get('ilan_id')}"))
                markup.add(InlineKeyboardButton(f"✏️ Teslimat Gir {i.get('ilan_id')}", callback_data=f"delivery_{i.get('ilan_id')}"))
            markup.add(InlineKeyboardButton("↩️ Geri", callback_data="admin_back"))
            admin_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "\n".join(text_lines), reply_markup=markup)
            return

        # Teslimat bilgisi girme (ilan bazlı)
        if data.startswith("delivery_"):
            ilan_id = data.split("delivery_", 1)[1]
            admin_mode[chat_id]["action"] = "enter_delivery_for_ilan"
            admin_mode[chat_id]["ilan_id"] = ilan_id
            bot.send_message(chat_id, f"✏️ İlan {ilan_id} için teslimat bilgilerini girin (kullanıcı adı / mail / şifre).")
            return

        # İlan silme
        if data.startswith("delete_"):
            ilan_id = data.split("delete_", 1)[1]
            ilanlar = load_json(ILANLAR_FILE)
            ilanlar = [x for x in ilanlar if x.get("ilan_id") != ilan_id]
            save_json(ILANLAR_FILE, ilanlar)
            bot.answer_callback_query(call.id, text="✅ İlan silindi.")
            show_admin_panel(chat_id)
            return

    except Exception as e:
        print("handle_admin_callbacks hata:", e)
        try:
            bot.send_message(chat_id, f"⚠️ Hata: {e}")
        except:
            pass
            
# ----------------- USER CALLBACKS -----------------
def handle_user_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data or ""
    try:
        msg_id = ensure_user_msg(chat_id)

        # Geriye buton (ana menü)
        if data == "back_to_start" or data == "user_back":
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🛍️ İlanlar", callback_data="show_categories"))
            user_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "👋 Hoşgeldiniz! Aşağıdan ilanlara bakabilirsiniz.", reply_markup=markup)
            return

        # Kategori göster
        if data == "show_categories":
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📱 TikTok", callback_data="tiktok_category"))
            markup.add(InlineKeyboardButton("📸 Instagram", callback_data="instagram_category"))
            markup.add(InlineKeyboardButton("↩️ Geri", callback_data="back_to_start"))
            user_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "📌 Hangi kategoriye bakmak istersiniz?", reply_markup=markup)
            return

        # Seçilen kategori ilanlarını yükle
        if data in ("tiktok_category", "instagram_category"):
            category = "tiktok" if data == "tiktok_category" else "instagram"
            ilanlar = [i for i in load_json(ILANLAR_FILE) if i.get("category") == category and not i.get("sold")]
            if not ilanlar:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("↩️ Geri", callback_data="show_categories"))
                user_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "❌ Bu kategoride ilan yok.", reply_markup=markup)
                return
            # kaydet
            user_mode[chat_id].update({"category": category, "ilanlar": ilanlar, "index": 0})
            show_ilan(chat_id)
            return

        # İlan içi gezinme
        if data == "next" or data == "next_ilan":
            if "index" in user_mode.get(chat_id, {}):
                user_mode[chat_id]["index"] = min(user_mode[chat_id]["index"] + 1, len(user_mode[chat_id]["ilanlar"]) - 1)
            show_ilan(chat_id)
            return
        if data == "prev" or data == "prev_ilan":
            if "index" in user_mode.get(chat_id, {}):
                user_mode[chat_id]["index"] = max(user_mode[chat_id]["index"] - 1, 0)
            show_ilan(chat_id)
            return

        # Satın alma başlat
        if data.startswith("buy_"):
            ilan_id = data.split("buy_", 1)[1]
            ilan = next((i for i in load_json(ILANLAR_FILE) if i.get("ilan_id") == ilan_id), None)
            if not ilan:
                bot.send_message(chat_id, "❌ İlan bulunamadı.")
                return
            payment_link = ilan.get("payment_link", "https://papara.com/example")
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("✅ Ödeme Yaptım", callback_data=f"paid_{ilan_id}"))
            markup.add(InlineKeyboardButton("❌ Vazgeç", callback_data="show_categories"))
            user_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id,
                                                        f"💳 Ödeme yapabilirsiniz:\n{payment_link}\n\nÖdeme yaptıktan sonra 'Ödeme Yaptım' butonuna basın ve dekontu gönderin.",
                                                        reply_markup=markup)
            return

        # Ödeme yaptım -> dekont bekleme
        if data.startswith("paid_"):
            ilan_id = data.split("paid_", 1)[1]
            user_mode.setdefault(chat_id, {})
            user_mode[chat_id]["awaiting_receipt"] = ilan_id
            user_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "📸 Lütfen dekont fotoğrafını gönderin (galeriden yükleyin).", reply_markup=None)
            return

    except Exception as e:
        print("handle_user_callbacks hata:", e)
        try:
            bot.send_message(chat_id, f"⚠️ Hata: {e}")
        except:
            pass
  
# ----------------- İLAN GÖSTERME -----------------
def show_ilan(chat_id):
    try:
        mode = user_mode.get(chat_id, {})
        msg_id = ensure_user_msg(chat_id)
        ilanlar = mode.get("ilanlar", [])
        # filtrele (satılmamış)
        ilanlar = [i for i in ilanlar if not i.get("sold")]
        if not ilanlar:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("↩️ Geri", callback_data="show_categories"))
            user_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, "❌ Bu kategoride ilan kalmadı.", reply_markup=markup)
            return
        idx = mode.get("index", 0)
        if idx < 0: idx = 0
        if idx >= len(ilanlar): idx = len(ilanlar) - 1
        user_mode[chat_id]["index"] = idx
        ilan = ilanlar[idx]
        text = f"📌 {ilan.get('description')}\n💰 Fiyat: {ilan.get('price', 'Belirtilmemiş')}\n🆔 ID: {ilan.get('ilan_id')}"
        markup = InlineKeyboardMarkup()
        row = []
        if idx > 0:
            row.append(InlineKeyboardButton("◀️ Geri", callback_data="prev"))
        row.append(InlineKeyboardButton("🛒 Satın Al", callback_data=f"buy_{ilan.get('ilan_id')}"))
        if idx < len(ilanlar) - 1:
            row.append(InlineKeyboardButton("▶️ İleri", callback_data="next"))
        for btn in row:
            markup.add(btn)
        markup.add(InlineKeyboardButton("↩️ Geri", callback_data="show_categories"))
        user_mode[chat_id]["message_id"] = safe_edit(chat_id, msg_id, text, reply_markup=markup)
    except Exception as e:
        print("show_ilan hata:", e)
        try:
            bot.send_message(chat_id, f"⚠️ Hata: {e}")
        except:
            pass

# ----------------- MESAJLAR (TEXT / PHOTO) -----------------
@bot.message_handler(content_types=['text', 'photo'])
def handle_messages(message):
    chat_id = message.chat.id
    try:
        # ---- Admin: ilan ekleme veya teslimat bilgisi girme ----
        if chat_id == ADMIN_ID and chat_id in admin_mode:
            mode = admin_mode.get(chat_id, {})
            # İlan ekleme
            if mode.get("action") == "add_ilan" and message.text:
                category = mode.get("category")
                description = message.text.strip()
                ilanlar = load_json(ILANLAR_FILE)
                ilan_id = generate_id()
                ilanlar.append({
                    "ilan_id": ilan_id,
                    "category": category,
                    "description": description,
                    "price": "Belirtilmemiş",
                    "payment_link": "https://papara.com/example",
                    "sold": False
                })
                save_json(ILANLAR_FILE, ilanlar)
                bot.send_message(chat_id, f"✅ {category.capitalize()} ilanı eklendi! ID: {ilan_id}")
                del admin_mode[chat_id]["action"]
                del admin_mode[chat_id]["category"]
                show_admin_panel(chat_id)
                return

            # Admin teslimat bilgisi girme (sipariş onayında)
            if mode.get("action") == "enter_delivery" and message.text:
                order_id = mode.get("order_id")
                orders = load_json(ORDERS_FILE)
                idx = next((i for i, x in enumerate(orders) if x.get("order_id") == order_id), None)
                if idx is not None:
                    orders[idx]["delivery_info"] = message.text.strip()
                    orders[idx]["status"] = "teslim_edildi"
                    save_json(ORDERS_FILE, orders)
                    try:
                        bot.send_message(orders[idx]["user_id"], f"📦 Hesabınız teslim edildi:\n{orders[idx]['delivery_info']}")
                    except:
                        pass
                    bot.send_message(chat_id, "✅ Teslimat bilgisi kaydedildi ve kullanıcıya iletildi.")
                admin_mode[chat_id].pop("action", None)
                admin_mode[chat_id].pop("order_id", None)
                show_admin_panel(chat_id)
                return

            # Admin teslimat ilan bazlı
            if mode.get("action") == "enter_delivery_for_ilan" and message.text:
                ilan_id = mode.get("ilan_id")
                ilanlar = load_json(ILANLAR_FILE)
                for i in ilanlar:
                    if i.get("ilan_id") == ilan_id:
                        i["delivery_info"] = message.text.strip()
                save_json(ILANLAR_FILE, ilanlar)
                bot.send_message(chat_id, "✅ İlan için teslimat bilgisi kaydedildi.")
                admin_mode[chat_id].pop("action", None)
                admin_mode[chat_id].pop("ilan_id", None)
                show_admin_panel(chat_id)
                return
                
# ---- Kullanıcı: dekont gönderiyorsa ----
        if message.photo:
            umode = user_mode.get(chat_id, {})
            if umode and umode.get("awaiting_receipt"):
                try:
                    ilan_id = umode.get("awaiting_receipt")
                    # fotoğraf dosyasını indir
                    photo = message.photo[-1]
                    file_info = bot.get_file(photo.file_id)
                    data = bot.download_file(file_info.file_path)
                    filename = f"{ilan_id}_{chat_id}.jpg"
                    filepath = os.path.join(RECEIPTS_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(data)
                    # sipariş oluştur
                    orders = load_json(ORDERS_FILE)
                    ilan = next((x for x in load_json(ILANLAR_FILE) if x.get("ilan_id") == ilan_id), None)
                    order = {
                        "order_id": generate_id(),
                        "user_id": chat_id,
                        "user_name": message.from_user.username,
                        "ilan_id": ilan_id,
                        "ilan_info": ilan.get("description") if ilan else "",
                        "receipt_file": filename,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "status": "beklemede"
                    }
                    orders.append(order)
                    save_json(ORDERS_FILE, orders)
                    # dekont geldikten sonra ilan satıldı yap
                    ilan_list = load_json(ILANLAR_FILE)
                    for it in ilan_list:
                        if it.get("ilan_id") == ilan_id:
                            it["sold"] = True
                    save_json(ILANLAR_FILE, ilan_list)
                    # admin'e kısa bildirim
                    try:
                        admin_msg_id = ensure_admin_msg(ADMIN_ID)
                        bot.send_message(ADMIN_ID, f"📸 Yeni dekont geldi: {order.get('user_name')} — İlan: {order.get('ilan_info')}\n'Onaylanması Bekleyen Siparişler' bölümünden görüntüleyebilirsiniz.")
                    except:
                        pass
                    # kullanıcıya geri dönüş
                    bot.send_message(chat_id, "📸 Dekontunuz alındı. Admin onayını bekleyin.")
                    # awaiting_receipt temizle
                    user_mode[chat_id].pop("awaiting_receipt", None)
                    return
                except Exception as e:
                    print("dekont kaydetme hata:", e)
                    bot.send_message(chat_id, f"⚠️ Dekont kaydederken hata: {e}")
                    return

        # ---- Diğer text mesajlar: kullanıcı normal mesaj atarsa ----
        if message.text:
            if chat_id in user_mode:
                bot.send_message(chat_id, "ℹ️ Lütfen butonları kullanın. İlanları görmek için /start veya 'İlanlar' butonuna basınız.")
            else:
                bot.send_message(chat_id, "ℹ️ Başlamak için /start yazın.")
    except Exception as e:
        print("handle_messages genel hata:", e)
        
# ----------------- BOT BAŞLAT -----------------
if __name__ == "__main__":
    print("Bot çalışıyor...")
    # Telebot logger'ı kapatabilirsin log spamını azaltmak için
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Bot kapatıldı (KeyboardInterrupt).")
    except Exception as e:
        print("polling hata:", e)