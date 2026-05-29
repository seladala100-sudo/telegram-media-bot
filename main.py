import os
import re
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
# ТОКЕН БОТА
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")

# ==========================================
# ПАПКА ДЛЯ ЗАГРУЗОК
# ==========================================
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
# КОМАНДА /start
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🔥 <b>Медиа Бот</b>\n\n"
        "Отправь мне ссылку с любой популярной платформы,\n"
        "и я скачаю медиафайл для тебя.\n\n"
        "📥 Поддерживаются:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram\n"
        "• Twitter / X\n"
        "• Reddit\n"
        "• Facebook\n"
        "• И многие другие\n\n"
        "⚡ Просто отправь ссылку сообщением."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# ==========================================
# КОМАНДА /help
# ==========================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🛠 <b>Как пользоваться ботом</b>\n\n"
        "1. Скопируй ссылку на видео\n"
        "2. Отправь её боту\n"
        "3. Подожди загрузку\n"
        "4. Получи готовый файл\n\n"
        "📌 Пример:\n"
        "<code>https://youtu.be/xxxxx</code>\n\n"
        "⚠️ Большие видео Telegram может не пропустить."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# ==========================================
# ОБРАБОТКА СООБЩЕНИЙ
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = update.message.text.strip()

    if not is_valid_url(url):

        await update.message.reply_text(
            "❌ Отправь корректную ссылку."
        )

        return

    status_msg = await update.message.reply_text(
        "📥 Загружаю видео..."
    )

    try:

        ydl_opts = {
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "format": "best",
            "noplaylist": True,
            "restrictfilenames": True,
            "quiet": True,
        }

        # СКАЧИВАНИЕ
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            file_path = ydl.prepare_filename(info)

        # ПРОВЕРКА ФАЙЛА
        if not os.path.exists(file_path):

            await status_msg.edit_text(
                "❌ Ошибка загрузки."
            )

            return

        # ПРОВЕРКА РАЗМЕРА
        file_size = os.path.getsize(file_path)

        # LIMIT TELEGRAM ~49MB
        if file_size > 49 * 1024 * 1024:

            os.remove(file_path)

            await status_msg.edit_text(
                "⚠️ Файл слишком большой для Telegram."
            )

            return

        await status_msg.edit_text(
            "📤 Отправляю файл..."
        )

        # ОТПРАВКА ВИДЕО
        with open(file_path, "rb") as video:

            await update.message.reply_video(
                video=video,
                supports_streaming=True,
            )

        # УДАЛЕНИЕ ФАЙЛА
        os.remove(file_path)

        await status_msg.delete()

    except Exception as e:

        await status_msg.edit_text(
            f"❌ Ошибка:\n{str(e)}"
        )


# ==========================================
# ЗАПУСК БОТА
# ==========================================
def main():

    app = ApplicationBuilder().token(TOKEN).build()

    # КОМАНДЫ
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    # СООБЩЕНИЯ
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Бот запущен...")

    # УДАЛЕНИЕ WEBHOOK
    app.bot.delete_webhook(
        drop_pending_updates=True
    )

    # POLLING
    app.run_polling()


# ==========================================
# СТАРТ
# ==========================================
if __name__ == "__main__":
    main()
