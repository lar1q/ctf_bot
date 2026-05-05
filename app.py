import os
import re
import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
PORT = int(os.getenv("PORT", "8080"))

logging.basicConfig(level=logging.INFO)

fastapi_app = FastAPI()
telegram_app = Application.builder().token(BOT_TOKEN).build()


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
        logging.error(f"Не удалось отправить админу: {e}")


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


@fastapi_app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return Response(content="ok")

@fastapi_app.get("/")
async def root():
    return {"status": "ok"}


@fastapi_app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.start()
    # Устанавливаем вебхук
    render_external_name = os.getenv("RENDER_EXTERNAL_NAME")
    if not render_external_name:
        logging.error("RENDER_EXTERNAL_NAME не задан!")
        return
    webhook_url = f"https://{render_external_name}/webhook"
    await telegram_app.bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook установлен на {webhook_url}")

@fastapi_app.on_event("shutdown")
async def on_shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="0.0.0.0", port=PORT)
