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
# /start
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🔥 <b>Load</b>\n\n"
        "Отправь ссылку с любой популярной платформы,\n"
        "и я загружу медиафайл для тебя.\n\n"
        "📥 Поддерживаются:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram\n"
        "• Twitter / X\n"
        "• Reddit\n"
        "• Facebook\n"
        "• И другие платформы\n\n"
        "⚡ Просто отправь ссылку сообщением."
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
        "1. Скопируй ссылку на видео\n"
        "2. Отправь её боту\n"
        "3. Подожди несколько секунд\n"
        "4. Получи готовый файл\n\n"
        "📌 Пример:\n"
        "<code>https://youtu.be/xxxxx</code>\n\n"
        "⚠️ Большие файлы Telegram может не пропустить."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )

# ==========================================
# ОБРАБОТКА ССЫЛОК
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = update.message.text.strip()

    # Проверка ссылки
    if not is_valid_url(url):

        await update.message.reply_text(
            "❌ Отправь корректную ссылку."
        )

        return

    # Сообщение статуса
    status_msg = await update.message.reply_text(
        "📥 Анализирую ссылку..."
    )

    try:

        ydl_opts = {
    "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
    "format": "best[height<=720]",
    "noplaylist": True,
    "restrictfilenames": True,
    "quiet": True,
    "cookiefile": "cookies.txt",
}

        # ==========================================
        # СКАЧИВАНИЕ ВИДЕО
        # ==========================================
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            # Получаем информацию
            info = ydl.extract_info(url, download=False)

            title = info.get("title", "video")

            await status_msg.edit_text(
                f"📥 Загружаю:\n<b>{title}</b>",
                parse_mode="HTML"
            )

            # Скачиваем
            ydl.download([url])

            # Путь к файлу
            file_path = ydl.prepare_filename(info)

        # ==========================================
        # ПРОВЕРКА ФАЙЛА
        # ==========================================
        if not os.path.exists(file_path):

            await status_msg.edit_text(
                "❌ Ошибка загрузки."
            )

            return

        # ==========================================
        # ПРОВЕРКА РАЗМЕРА
        # ==========================================
        file_size = os.path.getsize(file_path)

        # Лимит Telegram ~49MB
        if file_size > 49 * 1024 * 1024:

            os.remove(file_path)

            await status_msg.edit_text(
                "⚠️ Файл слишком большой для Telegram."
            )

            return

        # ==========================================
        # ОТПРАВКА
        # ==========================================
        await status_msg.edit_text(
            "📤 Отправляю файл..."
        )

        with open(file_path, "rb") as video:

            await update.message.reply_video(
                video=video,
                caption=f"🔥 <b>{title}</b>",
                parse_mode="HTML",
                supports_streaming=True,
            )

        # ==========================================
        # УДАЛЕНИЕ ФАЙЛА
        # ==========================================
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

    # Команды
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    # Сообщения
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("🔥 Load запущен...")

    # Удаляем webhook
    app.bot.delete_webhook(
        drop_pending_updates=True
    )

    # Запуск
    app.run_polling()

# ==========================================
# СТАРТ
# ==========================================
if __name__ == "__main__":
    main()
