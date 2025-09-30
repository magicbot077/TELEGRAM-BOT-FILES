import logging
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== Tokens =====
import os
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# RapidAPI details
API_URL = "https://instagram-reels-downloader-api.p.rapidapi.com/download"
HEADERS = {
    "x-rapidapi-host": "instagram-reels-downloader-api.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY
}

# Logging
logging.basicConfig(level=logging.INFO)

# ==================== Dummy HTTP Server for Render ====================
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading

PORT = int(os.environ.get("PORT", 10000))  # Render automatically sets PORT

def run_dummy_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ==================== Bot Handlers ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me an Instagram reel link and I will download it for you!"
    )

async def download_reel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if "instagram.com" not in user_text:
        await update.message.reply_text("⚠️ Please send a valid Instagram reel link.")
        return

    try:
        waiting_msg = await update.message.reply_text("⏳ Processing your reel, please wait...")

        response = requests.get(API_URL, headers=HEADERS, params={"url": user_text})

        if response.status_code != 200:
            await waiting_msg.edit_text(f"⚠️ API returned status {response.status_code}")
            return

        data = response.json()
        reel_url = None
        if data.get("success") and "data" in data and "medias" in data["data"]:
            medias = data["data"]["medias"]
            reel_url = next((m["url"] for m in medias if m["type"] == "video"), None)

        if reel_url:
            await waiting_msg.delete()
            await update.message.reply_video(video=reel_url, caption="✅ Here is your reel!")
        else:
            await waiting_msg.edit_text("❌ Could not fetch reel, try another link.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# ==================== Main ====================
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_reel))

    print("Bot is running 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
