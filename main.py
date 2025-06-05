from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler, ContextTypes, filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import os

import httpx

client_httpx = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    timeout=30.0
)


# Environment o‘zgaruvchilar
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
HR_GROUP_CHAT_ID = -1002519174347  # HR guruhi ID

# Google Sheets sozlamalari
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("HR bot data").sheet1

# Flask va Application
app_flask = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).http_client(client_httpx).build()

# Bosqichlar
PHOTO, FULLNAME, POSITION, STUDENT, MARITAL, REGION, EXPERIENCE, STRENGTHS = range(8)

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Iltimos, o'zingizning rasmingizni yuboring:")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1]
    context.user_data["photo_file_id"] = photo_file.file_id
    await update.message.reply_text("Ism familyangizni kiriting:")
    return FULLNAME

async def get_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fullname"] = update.message.text
    await update.message.reply_text("Telefon raqamingizni kiriting: (+9989********)")
    return POSITION

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Siz talabamisiz? (Ha/Yoq):")
    return STUDENT

async def get_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student"] = update.message.text
    await update.message.reply_text("Oilaviy holatingiz (Uylangan, Bo'ydoq va h.k.):")
    return MARITAL

async def get_marital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["marital"] = update.message.text
    await update.message.reply_text("Qaysi viloyatdan siz?")
    return REGION

async def get_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["region"] = update.message.text
    await update.message.reply_text("Oldin ishlagan joylaringizni yozing:")
    return EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["experience"] = update.message.text
    await update.message.reply_text("O'zingizdagi ustun hislatlaringizni yozing:")
    return STRENGTHS

async def get_strengths(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["strengths"] = update.message.text
    username = update.message.from_user.username or "Noma'lum"
    context.user_data["username"] = username

    # Sheetsga yozish
    sheet.append_row([
        context.user_data["fullname"],
        context.user_data["phone"],
        context.user_data["student"],
        context.user_data["marital"],
        context.user_data["region"],
        context.user_data["experience"],
        context.user_data["strengths"],
        f"@{username}"
    ])

    caption = (
        f"👤 Ism: {context.user_data['fullname']}\n"
        f"📞 Telefon: {context.user_data['phone']}\n"
        f"🎓 Talaba: {context.user_data['student']}\n"
        f"👪 Oilaviy holat: {context.user_data['marital']}\n"
        f"🌍 Viloyat: {context.user_data['region']}\n"
        f"💼 Ish joylari: {context.user_data['experience']}\n"
        f"🌟 Ustun hislatlari: {context.user_data['strengths']}\n"
        f"🆔 Telegram: @{username}"
    ).strip()[:1000]

    buttons = InlineKeyboardMarkup([[  # Tugmalar
        InlineKeyboardButton("✅ Qabul qilindi", callback_data=f"accepted:{update.message.from_user.id}"),
        InlineKeyboardButton("❌ Qilinmadi", callback_data=f"rejected:{update.message.from_user.id}")
    ]])

    await context.bot.send_photo(
        chat_id=HR_GROUP_CHAT_ID,
        photo=context.user_data["photo_file_id"],
        caption=caption,
        reply_markup=buttons
    )

    await update.message.reply_text("Ma'lumotlaringiz saqlandi. Rahmat!")
    return ConversationHandler.END

# Bekor qilish
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Jarayon bekor qilindi.")
    return ConversationHandler.END

# Qabul qilindi/qilinmadi tugmalarini ishlovchi
async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id = query.data.split(":")
    user_id = int(user_id)

    if action == "accepted":
        await context.bot.send_message(chat_id=user_id, text="✅ Tabriklaymiz! Arizangiz qabul qilindi.")
        await query.edit_message_caption(caption=query.message.caption + "\n\n🟢 Holat: Qabul qilindi")
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ Afsuski, arizangiz rad etildi.")
        await query.edit_message_caption(caption=query.message.caption + "\n\n🔴 Holat: Rad etildi")

# Handlerlar
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
        FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fullname)],
        POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        STUDENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_student)],
        MARITAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_marital)],
        REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_region)],
        EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)],
        STRENGTHS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_strengths)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(conv_handler)
application.add_handler(CallbackQueryHandler(handle_decision))

# Webhook endpoint
@app_flask.route("/webhook", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, application.bot)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
        loop.close()
    except Exception as e:
        print("Error processing update:", e)
        return "Internal Server Error", 500

    return "OK", 200



@app_flask.route("/", methods=["GET"])
def index():
    return "Bot ishlayapti!", 200

# Asosiy ishga tushirish
if __name__ == "__main__":
    # Webhookni set qilishni 1 marta tashqi terminalda qo‘lda bajarish tavsiya
    import threading
    async def setup():
        await application.initialize()
        await application.bot.set_webhook(url=WEBHOOK_URL)
    threading.Thread(target=lambda: asyncio.run(setup())).start()
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
