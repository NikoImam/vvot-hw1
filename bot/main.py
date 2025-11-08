import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
if not TG_TOKEN:
    raise RuntimeError("Переменная окружения TG_BOT_TOKEN не установлена")

API_URL = f"https://api.telegram.org/bot{TG_TOKEN}"


def send_message(chat_id: int, text: str):
    """Отправить сообщение пользователю"""
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})


@app.post("/webhook")
async def webhook(request: Request):
    """Основной обработчик Telegram Webhook"""
    update = await request.json()

    if "message" not in update:
        return {"ok": True}

    message = update["message"]
    chat_id = message["chat"]["id"]

    # 1️⃣ Команды /start и /help
    if "text" in message:
        text = message["text"]
        if text.startswith("/start") or text.startswith("/help"):
            send_message(
                chat_id,
                "👋 Привет! Я помогу тебе с экзаменационными вопросами по 'Операционным системам'.\n"
                "Просто пришли вопрос — текстом или фото 📸"
            )
            return {"ok": True}

        # 2️⃣ Текст
        send_message(chat_id, "Вы отправили текст. В будущем я обработаю его через YandexGPT 🤖.")
        return {"ok": True}

    # 3️⃣ Фото
    if "photo" in message:
        send_message(chat_id, "Вы отправили фото. Я позже распознаю его через Yandex Vision OCR 👁️.")
        return {"ok": True}

    # 4️⃣ Остальные типы сообщений
    send_message(chat_id, "Пока я понимаю только текст и фото 😅.")
    return {"ok": True}
