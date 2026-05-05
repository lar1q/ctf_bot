import os
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text(
        "Для отправки ответа оформите:\n[название кейса][номер кейса] - [ваш ответ]\n\n"
        "Пример: Web1 - flag{test_flag}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    text = update.message.text.strip()
    username = user.username if user.username else "Без username"
    user_id = user.id

    
    if not re.match(r"^.+?\s+-\s+.+$", text):
        await update.message.reply_text(
            "❌ Неверный формат!\nПожалуйста, оформите ответ строго по шаблону:\n"
            "[название кейса][номер кейса] - [ваш ответ]\nПример: Web1 - flag{123}"
        )
        return

    await update.message.reply_text(
        "✅ Спасибо за ответ! Ваше сообщение было отправлено администратору."
    )

    admin_message = f"📨 Новый ответ от @{username} (id: {user_id}):\n└ {text}"
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админу: {e}")

def main():
    if not BOT_TOKEN or ADMIN_CHAT_ID == 0:
        logger.error("Не заданы BOT_TOKEN или ADMIN_CHAT_ID")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
