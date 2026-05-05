import os
import sys
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
import uvicorn


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if ADMIN_CHAT_ID is not None:
    try:
        ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
    except ValueError:
        logging.error(f"ADMIN_CHAT_ID должен быть числом, получено: {ADMIN_CHAT_ID}")
        sys.exit(1)
else:
    logging.error("ADMIN_CHAT_ID не задан в переменных окружения")
    sys.exit(1)

PORT = int(os.getenv("PORT", "8080"))


RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
if not RENDER_EXTERNAL_URL:
    logging.error("Переменная RENDER_EXTERNAL_URL не установлена! Webhook не сможет работать.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Запуск с ADMIN_CHAT_ID={ADMIN_CHAT_ID}, PORT={PORT}")
logger.info(f"Webhook URL будет: {RENDER_EXTERNAL_URL}/telegram")


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
        logging.error(f"Не удалось отправить сообщение админу: {e}")


app = Starlette(debug=True)
ptb_app = Application.builder().token(BOT_TOKEN).build()

async def webhook(request: Request):
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, ptb_app.bot)
        await ptb_app.process_update(update)
        return Response("ok")
    except Exception as e:
        logger.error(f"Ошибка в webhook: {e}")
        return Response("error", status_code=500)

async def set_webhook():
    webhook_url = f"{RENDER_EXTERNAL_URL}/telegram"
    logger.info(f"Устанавливаем вебхук: {webhook_url}")
    await ptb_app.bot.set_webhook(url=webhook_url)

@app.on_event("startup")
async def on_startup():
    logger.info("Инициализация бота...")
    ptb_app.add_handler(CommandHandler("start", start))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await ptb_app.initialize()
    await set_webhook()
    logger.info("Бот готов")

@app.route("/telegram", methods=["POST"])
async def telegram_webhook(request: Request):
    return await webhook(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
