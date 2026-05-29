import os
import re
import asyncio
import requests
import yt_dlp

from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
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
        "📌 <b>Команды:</b>\n"
        "/mp3 <code>ссылка</code> — скачать аудио\n"
        "/mp4 <code>ссылка</code> — скачать видео\n"
        "/info <code>ссылка</code> — информация о видео\n\n"
        "🚀 Или просто отправь ссылку."
    )
    await update.message.reply_text(text, parse_mode="HTML")

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
        "📌 <b>Дополнительно:</b>\n"
        "/mp3 <code>ссылка</code> — скачать аудио (MP3)\n"
        "/mp4 <code>ссылка</code> — скачать видео (MP4)\n"
        "/info <code>ссылка</code> — информация о видео\n\n"
        "⚡ LOAD работает максимально быстро."
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ==========================================
# /info
# ==========================================

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Использование:\n/info <code>ссылка</code>",
            parse_mode="HTML"
        )
        return

    url = context.args[0]
    msg = await update.message.reply_text("⏳ Получаю информацию...")

    try:
        ydl_opts = {"quiet": True, "noplaylist": True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title       = info.get("title", "Неизвестно")
        uploader    = info.get("uploader", "Неизвестно")
        duration    = info.get("duration", 0)
        views       = info.get("view_count") or 0
        likes       = info.get("like_count") or 0
        description = info.get("description", "") or ""
        upload_date = info.get("upload_date", "")
        webpage_url = info.get("webpage_url", url)
        thumbnail   = info.get("thumbnail", "")
        formats     = info.get("formats", [])

        duration_str = str(timedelta(seconds=int(duration))) if duration else "Неизвестно"

        if upload_date and len(upload_date) == 8:
            upload_date = f"{upload_date[6:8]}.{upload_date[4:6]}.{upload_date[:4]}"
        else:
            upload_date = "Неизвестно"

        short_desc = (description[:200] + "…") if len(description) > 200 else description
        short_desc = short_desc.replace("<", "&lt;").replace(">", "&gt;")

        has_mp4  = any(f.get("ext") == "mp4" for f in formats)
        has_mp3  = any(f.get("acodec") not in ("none", None) for f in formats)
        has_webm = any(f.get("ext") == "webm" for f in formats)

        format_icons = []
        if has_mp4:  format_icons.append("🎬 MP4")
        if has_mp3:  format_icons.append("🎵 MP3")
        if has_webm: format_icons.append("📦 WebM")
        formats_str = "  |  ".join(format_icons) if format_icons else "Нет данных"

        heights = [f.get("height") for f in formats if isinstance(f.get("height"), int)]
        max_res = f"{max(heights)}p" if heights else "Неизвестно"

        text = (
            f"⚡ <b>LOAD INFO</b>\n\n"
            f"🎬 <b>{title}</b>\n\n"
            f"👤 Автор: {uploader}\n"
            f"📅 Дата: {upload_date}\n"
            f"⏱ Длительность: {duration_str}\n"
            f"👁 Просмотры: {views:,}\n"
            f"👍 Лайки: {likes:,}\n"
            f"📐 Макс. качество: {max_res}\n"
            f"🗂 Форматы: {formats_str}\n"
        )

        if short_desc:
            text += f"\n📝 <b>Описание:</b>\n{short_desc}\n"

        text += f"\n🔗 <a href=\"{webpage_url}\">Открыть видео</a>"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎵 MP3", callback_data=f"dl_mp3|{url}"),
                InlineKeyboardButton("🎬 MP4", callback_data=f"dl_mp4|{url}"),
            ]
        ])

        await msg.delete()

        if thumbnail:
            await update.message.reply_photo(
                photo=thumbnail,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        print(e)
        await msg.edit_text("❌ Не удалось получить информацию.")

# ==========================================
# TIKTOK DOWNLOAD
# ==========================================

async def download_tiktok(url, update, status_msg):
    try:
        await status_msg.edit_text("📥 Загружаю TikTok...")

        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url).json()

        if not response.get("data"):
            await status_msg.edit_text("❌ Не удалось скачать TikTok.")
            return

        video_url = response["data"]["play"]
        title = response["data"].get("title", "TikTok Video")

        file_path = f"{DOWNLOAD_DIR}/tiktok.mp4"
        video_data = requests.get(video_url)

        with open(file_path, "wb") as f:
            f.write(video_data.content)

        await status_msg.edit_text("📤 Отправляю TikTok...")

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
        await status_msg.edit_text("❌ Ошибка TikTok.")

# ==========================================
# YOUTUBE + OTHER (видео)
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
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
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

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: ydl.download([url]))

            file_path = ydl.prepare_filename(info)

        if not os.path.exists(file_path):
            await status_msg.edit_text("❌ Ошибка загрузки.")
            return

        file_size = os.path.getsize(file_path)

        if file_size > 49 * 1024 * 1024:
            os.remove(file_path)
            await status_msg.edit_text("⚠️ Файл слишком большой.")
            return

        await status_msg.edit_text("📤 Отправляю файл...")

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
        await status_msg.edit_text("❌ Не удалось скачать медиа.")

# ==========================================
# СКАЧАТЬ MP3
# ==========================================

async def download_mp3(url, update, status_msg):
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "noplaylist": True,
            "restrictfilenames": True,
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "audio")

            await status_msg.edit_text(
                f"📥 Загружаю аудио:\n<b>{title}</b>",
                parse_mode="HTML"
            )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: ydl.download([url]))

            file_path = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"

        if not os.path.exists(file_path):
            await status_msg.edit_text("❌ Ошибка загрузки аудио.")
            return

        file_size = os.path.getsize(file_path)

        if file_size > 49 * 1024 * 1024:
            os.remove(file_path)
            await status_msg.edit_text("⚠️ Файл слишком большой.")
            return

        await status_msg.edit_text("📤 Отправляю аудио...")

        message = update.message or update.callback_query.message

        with open(file_path, "rb") as audio:
            await message.reply_audio(
                audio=audio,
                title=title,
                caption=f"⚡ <b>{title}</b>",
                parse_mode="HTML",
            )

        os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        print(e)
        await status_msg.edit_text("❌ Не удалось скачать аудио.")

# ==========================================
# СКАЧАТЬ MP4
# ==========================================

async def download_mp4(url, update, status_msg):
    try:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "quiet": True,
            "noplaylist": True,
            "restrictfilenames": True,
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "merge_output_format": "mp4",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "video")

            await status_msg.edit_text(
                f"📥 Загружаю видео:\n<b>{title}</b>",
                parse_mode="HTML"
            )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: ydl.download([url]))

            file_path = ydl.prepare_filename(info)

        if not os.path.exists(file_path):
            await status_msg.edit_text("❌ Ошибка загрузки видео.")
            return

        file_size = os.path.getsize(file_path)

        if file_size > 49 * 1024 * 1024:
            os.remove(file_path)
            await status_msg.edit_text("⚠️ Файл слишком большой.")
            return

        await status_msg.edit_text("📤 Отправляю видео...")

        message = update.message or update.callback_query.message

        with open(file_path, "rb") as video:
            await message.reply_video(
                video=video,
                caption=f"⚡ <b>{title}</b>",
                parse_mode="HTML",
                supports_streaming=True,
            )

        os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        print(e)
        await status_msg.edit_text("❌ Не удалось скачать видео.")

# ==========================================
# /mp3
# ==========================================

async def mp3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Использование:\n/mp3 <code>ссылка</code>",
            parse_mode="HTML"
        )
        return

    url = context.args[0]
    status_msg = await update.message.reply_text("⏳ Подготавливаю...")
    await download_mp3(url, update, status_msg)

# ==========================================
# /mp4
# ==========================================

async def mp4_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Использование:\n/mp4 <code>ссылка</code>",
            parse_mode="HTML"
        )
        return

    url = context.args[0]
    status_msg = await update.message.reply_text("⏳ Подготавливаю...")
    await download_mp4(url, update, status_msg)

# ==========================================
# ИНЛАЙН-КНОПКИ (из /info)
# ==========================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, url = query.data.split("|", 1)
    status_msg = await query.message.reply_text("⏳ Подготавливаю...")

    if action == "dl_mp3":
        await download_mp3(url, update, status_msg)
    elif action == "dl_mp4":
        await download_mp4(url, update, status_msg)

# ==========================================
# ОБРАБОТКА ССЫЛОК
# ==========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("❌ Отправь корректную ссылку.")
        return

    status_msg = await update.message.reply_text("📥 Анализирую ссылку...")

    if is_tiktok(url):
        await download_tiktok(url, update, status_msg)
    else:
        await download_ytdlp(url, update, status_msg)

# ==========================================
# ЗАПУСК
# ==========================================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("mp3", mp3_command))
    app.add_handler(CommandHandler("mp4", mp4_command))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern=r"^dl_(mp3|mp4)\|"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("⚡ LOAD запущен...")
    app.run_polling()

# ==========================================
# СТАРТ
# ==========================================

if __name__ == "__main__":
    main()
