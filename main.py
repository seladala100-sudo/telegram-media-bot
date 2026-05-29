import os
import re
import requests
import yt_dlp

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# ==========================================
# LOAD BOT
# ==========================================

TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# ==========================================
# ПРОВЕРКА ССЫЛКИ
# ==========================================

def is_valid_url(text):
    url_regex = r"https?://\S+"
    return re.match(url_regex, text)

# ==========================================
# ПРОВЕРКА TIKTOK
# ==========================================

def is_tiktok(url):
    return "tiktok.com" in url or "vt.tiktok.com" in url

# ==========================================
# /start
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "⚡ <b>LOAD</b>\n\n"
        "Отправь ссылку с любой платформы,\n"
        "и я загружу медиафайл.\n\n"
        "📥 Поддерживаются:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram\n"
        "• Twitter / X\n"
        "• Reddit\n"
        "• Facebook\n\n"
        "🚀 Просто отправь ссылку."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )

# ==========================================
# /help
# ==========================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🛠 <b>Как пользоваться</b>\n\n"
        "1. Скопируй ссылку\n"
        "2. Отправь её боту\n"
        "3. Подожди загрузку\n"
        "4. Получи файл\n\n"
        "⚡ LOAD работает максимально быстро."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )

# ==========================================
# TIKTOK DOWNLOAD
# ==========================================

async def download_tiktok(url, update, status_msg):

    try:

        await status_msg.edit_text(
            "📥 Загружаю TikTok..."
        )

        api_url = f"https://www.tikwm.com/api/?url={url}"

        response = requests.get(api_url).json()

        if not response.get("data"):

            await status_msg.edit_text(
                "❌ Не удалось скачать TikTok."
            )

            return

        video_url = response["data"]["play"]
        title = response["data"].get("title", "TikTok Video")

        file_path = f"{DOWNLOAD_DIR}/tiktok.mp4"

        video_data = requests.get(video_url)

        with open(file_path, "wb") as f:
            f.write(video_data.content)

        await status_msg.edit_text(
            "📤 Отправляю TikTok..."
        )

        with open(file_path, "rb") as video:

            await update.message.reply_video(
                video=video,
                caption=f"⚡ <b>{title}</b>",
                parse_mode="HTML",
                supports_streaming=True,
            )

        os.remove(file_path)

        await status_msg.delete()

    except Exception as e:

        print(e)

        await status_msg.edit_text(
            "❌ Ошибка TikTok."
        )

# ==========================================
# YOUTUBE + OTHER
# ==========================================

async def download_ytdlp(url, update, status_msg):

    try:

        ydl_opts = {

            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",

            "format": "best[height<=720]",

            "noplaylist": True,

            "restrictfilenames": True,

            "quiet": True,

            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=False)

            title = info.get("title", "video")

            await status_msg.edit_text(
                f"📥 Загружаю:\n<b>{title}</b>",
                parse_mode="HTML"
            )

            ydl.download([url])

            file_path = ydl.prepare_filename(info)

        if not os.path.exists(file_path):

            await status_msg.edit_text(
                "❌ Ошибка загрузки."
            )

            return

        file_size = os.path.getsize(file_path)

        # Telegram limit
        if file_size > 49 * 1024 * 1024:

            os.remove(file_path)

            await status_msg.edit_text(
                "⚠️ Файл слишком большой."
            )

            return

        await status_msg.edit_text(
            "📤 Отправляю файл..."
        )

        with open(file_path, "rb") as video:

            await update.message.reply_video(
                video=video,
                caption=f"⚡ <b>{title}</b>",
                parse_mode="HTML",
                supports_streaming=True,
            )

        os.remove(file_path)

        await status_msg.delete()

    except Exception as e:

        print(e)

        await status_msg.edit_text(
            "❌ Не удалось скачать медиа."
        )

# ==========================================
# ОБРАБОТКА ССЫЛОК
# ==========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = update.message.text.strip()

    if not is_valid_url(url):

        await update.message.reply_text(
            "❌ Отправь корректную ссылку."
        )

        return

    status_msg = await update.message.reply_text(
        "📥 Анализирую ссылку..."
    )

    # TikTok
    if is_tiktok(url):

        await download_tiktok(
            url,
            update,
            status_msg
        )

    # Other platforms
    else:

        await download_ytdlp(
            url,
            update,
            status_msg
        )

# ==========================================
# ЗАПУСК
# ==========================================

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("⚡ LOAD запущен...")

    app.run_polling()

# ==========================================
# СТАРТ
# ==========================================

if __name__ == "__main__":
    main()
