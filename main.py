import logging
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import os

# ===== Tokens =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY") or "67a4030b4cmshb79b66aac0fbe25p124f92jsn81e79164041a"

# Channel username (force join required)
CHANNEL_USERNAME = "@equation_x"  

# ===== New RapidAPI endpoint =====
API_URL = "https://insta-reels-downloader-the-fastest-hd-reels-fetcher-api.p.rapidapi.com/unified/index"
HEADERS = {
    "x-rapidapi-host": "insta-reels-downloader-the-fastest-hd-reels-fetcher-api.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY
}

# ===== Logging =====
logging.basicConfig(level=logging.INFO)

# ==================== Dummy HTTP Server for Render ====================
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading

PORT = int(os.environ.get("PORT", 10000))

def run_dummy_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ==================== Helper ====================
async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ==================== Handlers ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    first_name = update.message.from_user.first_name

    if not await is_subscribed(user_id, context):
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
             [InlineKeyboardButton("🔄 I have joined", callback_data="check_sub")]]
        )
        await update.message.reply_text(
            f"⚠️ Hello {first_name}!\n\nYou must join our channel to use this bot:\n👉 {CHANNEL_USERNAME}",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        f"👋 Welcome {first_name}!\n\nSend me any Instagram reel link, and I’ll download it for you instantly 🚀"
    )

# ==================== Subscription Check ====================
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    first_name = query.from_user.first_name

    if await is_subscribed(user_id, context):
        await query.message.delete()
        await query.message.reply_text(
            f"🎉 Welcome {first_name}!\n\nNow you can send me Instagram reel links 🚀"
        )
    else:
        await query.answer("❌ You still haven't joined the channel!", show_alert=True)

# ==================== Reel Downloader ====================
async def download_reel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not await is_subscribed(user_id, context):
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
             [InlineKeyboardButton("🔄 I have joined", callback_data="check_sub")]]
        )
        await update.message.reply_text(
            f"⚠️ To use this bot, please join 👉 {CHANNEL_USERNAME}",
            reply_markup=keyboard
        )
        return

    user_text = update.message.text.strip()
    if "instagram.com" not in user_text:
        await update.message.reply_text("⚠️ Please send a valid Instagram reel link.")
        return

    try:
        waiting_msg = await update.message.reply_text("⏳ Processing your reel, please wait...")

        response = requests.get(API_URL, headers=HEADERS, params={"url": user_text})
        if response.status_code != 200:
            await waiting_msg.edit_text(f"⚠️ API returned status {response.status_code}")
            print("Response:", response.text)
            return

        data = response.json()
        print("API Response:", data)

        reel_url = None
        if "data" in data and isinstance(data["data"], dict):
            reel_url = data["data"].get("url")

        if reel_url:
            await waiting_msg.delete()
            await update.message.reply_video(video=reel_url, caption="✅ Here’s your reel!")
        else:
            await waiting_msg.edit_text("❌ Could not fetch reel, try another link.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# ==================== Main ====================
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_reel))

    print("Bot is running 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
