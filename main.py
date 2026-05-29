import os
import re
import yt_dlp

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# PASTE YOUR TELEGRAM BOT TOKEN HERE
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


# ==========================================
# CHECK URL
# ==========================================
def is_valid_url(text):
    url_regex = r"https?://\S+"
    return re.match(url_regex, text)


# ==========================================
# HANDLE USER MESSAGE
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text(
            "Send a valid video link."
        )
        return

    status_msg = await update.message.reply_text(
        "Downloading..."
    )

    try:
        ydl_opts = {
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "format": "best",
            "noplaylist": True,
            "restrictfilenames": True,
            "quiet": True,
        }

        # DOWNLOAD VIDEO
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        # CHECK FILE EXISTS
        if not os.path.exists(file_path):
            await status_msg.edit_text(
                "Download failed."
            )
            return

        # FILE SIZE CHECK
        file_size = os.path.getsize(file_path)

        # 49 MB LIMIT FOR TELEGRAM BOT API
        if file_size > 49 * 1024 * 1024:
            os.remove(file_path)

            await status_msg.edit_text(
                "File is too large for Telegram."
            )
            return

        await status_msg.edit_text(
            "Uploading..."
        )

        # SEND VIDEO
        with open(file_path, "rb") as video:
            await update.message.reply_video(
                video=video,
                supports_streaming=True,
            )

        # DELETE FILE AFTER SEND
        os.remove(file_path)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(
            f"Error:\n{str(e)}"
        )


# ==========================================
# START BOT
# ==========================================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Bot is running...")

    app.run_polling()


# ==========================================
# RUN
# ==========================================
if __name__ == "__main__":
    main()
