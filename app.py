import os
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
import uvicorn

# Настройки
BOT_TOKEN = os.getenv("8604697648:AAFb75wbTYl0wTKfG7dl8wWduOvX-5ODNlk")
ADMIN_CHAT_ID = int(os.getenv("5253095009", "0"))
PORT = int(os.getenv("PORT", "8080"))

logging.basicConfig(level=logging.INFO)

# --- Логика бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Приветствие только в личных чатах
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text(
        "Для отправки ответа оформите:\n[название кейса][номер кейса] - [ваш ответ]\n\n"
        "Пример: Web1 - flag{test_flag}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Игнорируем всё, кроме личных сообщений
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    text = update.message.text.strip()
    username = user.username if user.username else "Без username"
    user_id = user.id

    # Проверка формата
    if not re.match(r"^.+?\s+-\s+.+$", text):
        await update.message.reply_text(
            "❌ Неверный формат!\nПожалуйста, оформите ответ строго по шаблону:\n"
            "[название кейса][номер кейса] - [ваш ответ]\nПример: Web1 - flag{123}"
        )
        return

    # Подтверждение пользователю
    await update.message.reply_text(
        "✅ Спасибо за ответ! Ваше сообщение было отправлено администратору."
    )

    # Отправка администратору (в группу или лично)
    admin_message = f"📨 Новый ответ от @{username} (id: {user_id}):\n└ {text}"
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение админу: {e}")

# --- Веб-сервер для Render (webhook) ---
app = Starlette(debug=True)
ptb_app = Application.builder().token(BOT_TOKEN).build()

async def webhook(request: Request):
    req_json = await request.json()
    update = Update.de_json(req_json, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response("ok")

async def set_webhook():
    webhook_url = f"{os.environ['RENDER_EXTERNAL_URL']}/telegram"
    await ptb_app.bot.set_webhook(url=webhook_url)

@app.on_event("startup")
async def on_startup():
    ptb_app.add_handler(CommandHandler("start", start))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await ptb_app.initialize()
    await set_webhook()

@app.route("/telegram", methods=["POST"])
async def telegram_webhook(request: Request):
    return await webhook(request)

# --- Запуск ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)