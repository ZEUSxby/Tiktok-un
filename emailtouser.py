import requests, SignerPy, json, secrets, uuid, binascii, os, time, random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = "8258521702:AAHgvEvDCWvzfu1_-nFotp9Qalj9wfAY0Bs"

user_started = set()  # Kullanıcı ID'lerini saklayacağız

def xor(string):
    return "".join([hex(ord(c) ^ 5)[2:] for c in string])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_started:
        await update.message.reply_text("❌ Zaten başlatıldı! Bana sadece e-posta gönder.")
    else:
        user_started.add(user_id)
        await update.message.reply_text("🎉 Merhaba! Bana e-posta gönder, TikTok kullanıcı adını bulayım.")

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_started:
        await update.message.reply_text("⚠️ Önce /start komutunu kullanmalısın!")
        return

    es = update.message.text
    xor_email = xor(es)
    await update.message.reply_text(f"📩 E-posta alındı: {es}\n⏳ Kullanıcı adı aranıyor...")

    params={'request_tag_from':'h5','fixed_mix_mode':'1','mix_mode':'1','account_param':xor_email,'scene':'1','device_platform':'android','os':'android','ssmix':'a','type':'3736','_rticket':str(round(random.uniform(1.2,1.6)*100000000)*-1)+'4632','cdid':str(uuid.uuid4()),'channel':'googleplay','aid':'1233','app_name':'musical_ly','version_code':'370805','version_name':'37.8.5','manifest_version_code':'2023708050','update_version_code':'2023708050','ab_version':'37.8.5','resolution':'1600*900','dpi':'240','device_type':'SM-G998B','device_brand':'samsung','language':'en','os_api':'28','os_version':'9','ac':'wifi','is_pad':'0','current_region':'TR','app_type':'normal','sys_region':'TR','last_install_time':'1754073240','mcc_mnc':'28602','timezone_name':'Europe/Istanbul','carrier_region_v2':'286','residence':'TR','app_language':'en','carrier_region':'TR','timezone_offset':'10800','host_abi':'arm64-v8a','locale':'tr-TR','ac2':'wifi','uoo':'1','op_region':'TR','build_number':'37.8.5','region':'TR','ts':str(round(random.uniform(1.2,1.6)*100000000)*-1),'iid':str(random.randint(1,10**19)),'device_id':str(random.randint(1,10**19)),'openudid':str(binascii.hexlify(os.urandom(8)).decode()),'support_webview':'1','okhttp_version':'4.2.210.6-tiktok','use_store_region_cookie':'1','app_version':'37.8.5'}

    s = requests.session()
    cookies = {'_ga_3DVKZSPS3D':'GS2.1.s1754435486$o1$g0$t1754435486$j60$l0$h0','_ga':'GA1.1.504663773.1754435486'}
    headers = {'accept':'*/*','accept-language':'en,ar;q=0.9,en-US;q=0.8','application-name':'web','application-version':'4.0.0','content-type':'application/json','origin':'https://temp-mail.io','referer':'https://temp-mail.io/','user-agent':'Mozilla/5.0'}
    json_data = {'min_name_length':10,'max_name_length':10}
    
    response = requests.post('https://api.internal.temp-mail.io/api/v3/email/new', cookies=cookies, headers=headers, json=json_data)
    name = response.json()["email"]
    
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/account_lookup/email/"
    s.cookies.update(cookies)
    m = SignerPy.sign(params=params, cookie=cookies)
    headers={'User-Agent':"com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; SM-G998B)","x-ss-stub":m['x-ss-stub'],'x-ss-req-ticket':m['x-ss-req-ticket'],'x-ladon':m['x-ladon'],'x-khronos':m['x-khronos'],'x-argus':m['x-argus'],'x-gorgon':m['x-gorgon'],'content-type':"application/x-www-form-urlencoded",'content-length':m['content-length']}
    response = requests.post(url, headers=headers, params=params, cookies=cookies)

    passport_ticket = response.json()["data"]["accounts"][0]["passport_ticket"]
    name_xor = xor(name)
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
    params.update({"not_login_ticket":passport_ticket,"email":name_xor})
    m = SignerPy.sign(params=params, cookie=cookies)
    headers.update({'x-ss-stub': m['x-ss-stub'],'x-ss-req-ticket': m['x-ss-req-ticket'],'x-ladon': m['x-ladon'],'x-khronos': m['x-khronos'],'x-argus': m['x-argus'],'x-gorgon': m['x-gorgon']})
    response = s.post(url, headers=headers, params=params, cookies=cookies)
    time.sleep(5)

    response = requests.get(f'https://api.internal.temp-mail.io/api/v3/email/{name}/messages', cookies=cookies, headers=headers)
    try:
        text = response.text.split('This email was generated for')[1]
        username = text.split('\\n')[0].strip().rstrip('.')
        await update.message.reply_text(
            f"✅ Kullanıcı adı bulundu!\n\n✨ Kullanıcı Adı: {username}\n🌐 Hesap Linki: tiktok.com/@{username}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Kullanıcı adı alınamadı! Hata: {e}")

# --------------------------- Bot Başlat -------------------------- #
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email))
app.run_polling()