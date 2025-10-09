import logging
import requests
import asyncio
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading
import moviepy.editor as mp  # <-- new import for MP3 conversion

# ===== Tokens =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY") or "67a4030b4cmshb79b66aac0fbe25p124f92jsn81e79164041a"

# ===== Channel username (force join required) =====
CHANNEL_USERNAME = "@equation_x"

# ===== RapidAPI Endpoint =====
API_URL = "https://insta-reels-downloader-the-fastest-hd-reels-fetcher-api.p.rapidapi.com/unified/index"
HEADERS = {
    "x-rapidapi-host": "insta-reels-downloader-the-fastest-hd-reels-fetcher-api.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY
}

# ===== Logging =====
logging.basicConfig(level=logging.INFO)

# ===== Dummy HTTP Server for Render =====
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

# ==================== /start Command ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    first_name = update.message.from_user.first_name

    if not await is_subscribed(user_id, context):
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                [InlineKeyboardButton("🔄 I have joined", callback_data="check_sub")]
            ]
        )
        await update.message.reply_text(
            f"⚠️ Hello {first_name}!\n\nYou must join our channel to use this bot:\n👉 {CHANNEL_USERNAME}",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        f"👋 Welcome {first_name}!\n\nSend me any Instagram reel link, and I’ll download it for you instantly 🚀"
    )

# ==================== Check Subscription ====================
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
            [
                [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                [InlineKeyboardButton("🔄 I have joined", callback_data="check_sub")]
            ]
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

        # ✅ Extract reel URL
        reel_url = None
        if "data" in data and isinstance(data["data"], dict):
            content = data["data"].get("content", {})
            if isinstance(content, dict):
                reel_url = content.get("media_url")
                if not reel_url and "items" in content:
                    items = content.get("items", [])
                    if len(items) > 0 and "media_url" in items[0]:
                        reel_url = items[0]["media_url"]

        print("Extracted Reel URL:", reel_url)

        if reel_url:
            # Button for convert to MP3
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🎵 Convert to MP3", callback_data=f"convert_mp3|{reel_url}")]]
            )
            await waiting_msg.delete()
            await update.message.reply_video(
                video=reel_url,
                caption="✅ Here’s your reel!\n\nClick below to convert it to MP3 🎧",
                reply_markup=keyboard
            )
        else:
            await waiting_msg.edit_text("❌ Could not fetch reel, try another link.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# ==================== MP3 Conversion Handler ====================
async def convert_to_mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    if len(data) != 2:
        await query.message.reply_text("⚠️ Invalid conversion request.")
        return

    reel_url = data[1]
    await query.message.reply_text("🎧 Converting video to MP3, please wait...")

    try:
        # Download video temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
            r = requests.get(reel_url)
            temp_video.write(r.content)
            video_path = temp_video.name

        # Convert to MP3
        mp3_path = video_path.replace(".mp4", ".mp3")
        video_clip = mp.VideoFileClip(video_path)
        video_clip.audio.write_audiofile(mp3_path)
        video_clip.close()

        # Send MP3
        with open(mp3_path, "rb") as audio_file:
            await query.message.reply_audio(audio=audio_file, caption="🎵 Here’s your MP3 version!")

        # Cleanup
        os.remove(video_path)
        os.remove(mp3_path)

    except Exception as e:
        await query.message.reply_text(f"⚠️ Conversion failed: {str(e)}")

# ==================== Main ====================
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription, pattern="check_sub"))
    app.add_handler(CallbackQueryHandler(convert_to_mp3, pattern="convert_mp3"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_reel))

    print("Bot is running 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
