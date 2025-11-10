import os
import requests
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

TG_TOKEN = os.getenv('TG_BOT_TOKEN')
if not TG_TOKEN:
    raise RuntimeError('Переменная окружения TG_BOT_TOKEN не установлена')

API_URL = f"https://api.telegram.org/bot{TG_TOKEN}"


def send_message(chat_id: int, text: str):
    requests.post(f'{API_URL}/sendMessage', json={'chat_id': chat_id, 'text': text})

def load_prompt_instruction():
    # TODO: impl
    return "Prompt"

def is_exam_question(text: str, prompt_instruction: str):
    # TODO: impl
    return False

def generate_text_answer(text: str, prompt_instruction: str):
    # TODO: impl
    return "Ответ"

def recognite_text_on_image(img):
    # TODO: impl
    return "Распознаный текст"

def handle_text_answer(text: str, chat_id: int):
    prompt_instruction = load_prompt_instruction()

    is_exam_q = is_exam_question(text, prompt_instruction)

    if not is_exam_q:
        send_message(
            chat_id,
            "Я не могу понять вопрос.\n"
            "Пришлите экзаменационный вопрос по «Операционным системам» — фото или текстом."
        )

        return {'ok': True}
    else:
        try:
            answer = generate_text_answer(text, prompt_instruction)
            send_message(chat_id, answer)

        except Exception:
            send_message(chat_id, "Я не смог подготовить ответ на экзаменационный вопрос.")

        return {'ok': True}

@app.post("/")
async def webhook(request: Request):
    update = await request.json()
    message = update['message']

    if not message:
        return {'ok': True}

    chat_id = message['chat']['id']

    text = message.get('text')
    photos = message.get('photo')

    if text and (text.startswith('/start') or text.startswith('/help')):
        send_message(
            chat_id,
            "Я помогу ответить на экзаменационный вопрос по «Операционным системам».\n"
            "Присылайте вопрос — фото или текстом."
        )

        return {'ok': True}
    
    if text:
        handle_text_answer(text, chat_id)

    elif photos:
        if 'media_group_id' in message:
            send_message(chat_id, "Я могу обработать только одну фотографию.")

            return {'ok': True}
        
        file_id = photos[-1]['file_id']
        r = requests.get(f'{API_URL}/getFile?file_id={file_id}')
        r.raise_for_status()
        file_path = r.json()['result']['file_path']
        file_url = f'https://api.telegram.org/file/bot{TG_TOKEN}/{file_path}'

        img = requests.get(file_url)
        if img.status_code != 200:
            send_message(chat_id, "Я не могу обработать эту фотографию.")
            
            return {'ok': True}
        
        try:
            recognition_text = recognite_text_on_image(img)
        except Exception:
            send_message(chat_id, "Я не могу обработать эту фотографию.")

            return {'ok': True}
        
        handle_text_answer(recognition_text, chat_id)

    else:
        send_message(chat_id, "Я могу обработать только текстовое сообщение или фотографию.")

        return {'ok': True}


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)