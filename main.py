import logging
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==== Tokens ====
TELEGRAM_TOKEN = "8399634229:AAFBSB377vTAuXU1nv50D55XTR6Jyfl_G7U"
RAPIDAPI_KEY = "67a4030b4cmshb79b66aac0fbe25p124f92jsn81e79164041a"

# RapidAPI details
API_URL = "https://instagram-reels-downloader-api.p.rapidapi.com/download"
HEADERS = {
    "x-rapidapi-host": "instagram-reels-downloader-api.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY
}

# Logging
logging.basicConfig(level=logging.INFO)


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me an Instagram reel link and I will download it for you!"
    )


# Reel downloader with waiting popup
async def download_reel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if "instagram.com" not in user_text:
        await update.message.reply_text("⚠️ Please send a valid Instagram reel link.")
        return

    try:
        # 1️⃣ Send temporary waiting message
        waiting_msg = await update.message.reply_text("⏳ Processing your reel, please wait...")

    

        # 3️⃣ Fetch reel from API
        response = requests.get(API_URL, headers=HEADERS, params={"url": user_text})

        if response.status_code != 200:
            await waiting_msg.edit_text(f"⚠️ API returned status {response.status_code}")
            return

        data = response.json()

        # 4️⃣ Get reel URL
        reel_url = None
        if data.get("success") and "data" in data and "medias" in data["data"]:
            medias = data["data"]["medias"]
            reel_url = next((m["url"] for m in medias if m["type"] == "video"), None)

        if reel_url:
            # 5️⃣ Delete waiting message
            await waiting_msg.delete()
            # 6️⃣ Send the reel
            await update.message.reply_video(video=reel_url, caption="✅ Here is your reel!")
        else:
            await waiting_msg.edit_text("❌ Could not fetch reel, try another link.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")


# Main function
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_reel))

    print("Bot is running 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()
