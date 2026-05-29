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

            # Путь
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",

            # YouTube FIX
            "format": "mp4[height<=720]/best[height<=720]",

            # Склейка аудио+видео
            "merge_output_format": "mp4",

            # Без плейлистов
            "noplaylist": True,

            # Без кривых символов
            "restrictfilenames": True,

            # Тихий режим
            "quiet": True,

            # User-Agent
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

            # Информация
            info = ydl.extract_info(url, download=False)

            title = info.get("title", "video")

            await status_msg.edit_text(
                f"📥 Загружаю:\n<b>{title}</b>",
                parse_mode="HTML"
            )

            # Скачивание
            ydl.download([url])

            # Путь
            file_path = ydl.prepare_filename(info)

            # Если после merge расширение изменилось
            if not os.path.exists(file_path):

                possible_mp4 = os.path.splitext(file_path)[0] + ".mp4"

                if os.path.exists(possible_mp4):
                    file_path = possible_mp4

        # Проверка
        if not os.path.exists(file_path):

            await status_msg.edit_text(
                "❌ Ошибка загрузки."
            )

            return

        # Размер
        file_size = os.path.getsize(file_path)

        # Telegram limit
        if file_size > 49 * 1024 * 1024:

            os.remove(file_path)

            await status_msg.edit_text(
                "⚠️ Файл слишком большой."
            )

            return

        # Отправка
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

        # Удаление
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
async def mp3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "❌ Использование:\n\n/mp3 ссылка"
        )

        return

    url = context.args[0]

    status_msg = await update.message.reply_text(
        "🎵 Подготавливаю MP3..."
    )

    try:

        ydl_opts = {

            "format": "bestaudio/best",

            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",

            "restrictfilenames": True,

            "quiet": True,

            "noplaylist": True,

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            title = info.get("title", "audio")

            filename = ydl.prepare_filename(info)

        mp3_file = os.path.splitext(filename)[0] + ".mp3"

        if not os.path.exists(mp3_file):

            await status_msg.edit_text(
                "❌ Не удалось создать MP3."
            )

            return

        await status_msg.edit_text(
            "📤 Отправляю MP3..."
        )

        with open(mp3_file, "rb") as audio:

            await update.message.reply_audio(
                audio=audio,
                title=title,
                caption=f"🎵 {title}",
            )

        os.remove(mp3_file)

        await status_msg.delete()

    except Exception as e:

        print(e)

        await status_msg.edit_text(
            "❌ Ошибка при создании MP3."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = update.message.text.strip()

    # Проверка
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

    # Остальные платформы
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

    # Команды
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )
app.add_handler(
    CommandHandler("mp3", mp3_command)
)
    # Сообщениях
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("⚡ LOAD запущен...")

    app.run_polling()

# ==========================================
# START
# ==========================================

if __name__ == "__main__":
    main()
