import os
import requests
from fastapi import FastAPI, Request
import uvicorn
from yandex_cloud_ml_sdk import YCloudML
import openai
import json
import base64

app = FastAPI()

TG_TOKEN = os.getenv('TG_BOT_TOKEN')
FOLDER_ID=os.getenv('FOLDER_ID')
AI_SA_API_KEY = os.getenv('AI_SA_API_KEY')
CONFIDENCE_LEVEL = float(os.getenv('CONFIDENCE_LEVEL', 0.8))
AI_MODEL = os.getenv('AI_MODEL', "yandexgpt-lite")

if not (TG_TOKEN and FOLDER_ID and AI_SA_API_KEY and CONFIDENCE_LEVEL):
    raise RuntimeError("Установлены не все переменные окружения")

API_URL = f"https://api.telegram.org/bot{TG_TOKEN}"
sdk = YCloudML(
    folder_id=f'{FOLDER_ID}',
    auth=f'{AI_SA_API_KEY}',
)

client = openai.OpenAI(
    api_key=AI_SA_API_KEY,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
    project=FOLDER_ID
)

def send_message(chat_id: int, text: str):
    requests.post(f'{API_URL}/sendMessage', json={'chat_id': chat_id, 'text': text})

def load_classifier_prompt():
    # TODO: impl
    return "Ты — помощник, который помогает готовить ответы на экзаменационные вопросы по дисциплине \"Операционные системы\"." \
        "Классифицируй, является ли этот экзаменационный билет вопросом по дисциплине \"Операционные системы\""

def load_gpt_prompt():
    # TODO: impl
    return '''Ты — помощник, который помогает готовить ответы на экзаменационные вопросы по дисциплине "Операционные системы". 
После получения вопроса определи, сможешь ли ты на него ответить (относится ли данный вопрос к требуемой дисциплине). Если в запросе несколько вопросов, определи причастность каждого вопроса к теме.
Если вопрос относится к данной дисциплине, подготовь РАЗВЁРНУТЫЙ ответ: определения, ключевые пункты и пример (если уместно).
Внимание: каждый развёрнутый ответ на каждый из вопросов в отдельном блоке.
Внимание: ответ на запрос должен быть без всякого форматирования по типу HTML, Markdown и т.д.
Формат JSON: {is_ready: True/False, response: "[Ответ на вопрос]"}. is_ready означает, смог ли ты подготовить ответ. Если запрос не по теме, то не смог подготовить.
-Отвечай по теме, не уходя на сторонние рассуждения.
-Максимум слов - 400.
-Ответ на русском языке.
-Добавь определения терминов
-Ответ развёрнутый
-Если вопросов несколько, верни ответ в виде списка в JSON.
-Ответ должен максимально раскрыть вопрос
'''

def is_exam_question(text: str, prompt: str):
    try:
        model = sdk.models.text_classifiers(AI_MODEL).configure(
            task_description=prompt,
            labels=['операционные системы', 'другая дисциплина'],
        )

        result = model.run(text)

        max_conf_item = max(result, key=lambda x: x.confidence)
        
        return max_conf_item.label == 'операционные системы' and max_conf_item.confidence > CONFIDENCE_LEVEL
    
    except Exception:
        return False

def generate_answer(text: str, prompt: str):
    response = client.responses.create(
        model=f"gpt://{FOLDER_ID}/{AI_MODEL}",
        temperature=0.3,
        instructions=prompt,
        input=text,
        max_output_tokens=500
    )

    data = json.loads(response.output_text.replace("```", ""))

    data = [item.get('response') for item in data if item.get('is_ready')]

    if len(data) > 0:
        combined = "\n\n".join(data)
        return combined
    else:
        raise RuntimeError("Не удалось получить ответа")


def recognite_text_on_image(img):
    img_base64 = base64.b64encode(img).decode("utf-8")
    data = {"mimeType": "JPEG",
            "languageCodes": ["ru","en"],
            "content": img_base64}

    url = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"

    headers= {"Content-Type": "application/json",
            "Authorization": f"Api-Key {AI_SA_API_KEY}",
            "x-folder-id": FOLDER_ID,
            "x-data-logging-enabled": "true"}
    
    response = requests.post(url=url, headers=headers, data=json.dumps(data))
    response = response.json()

    return response['result']['textAnnotation']['fullText']
    

def handle_text_answer(text: str, chat_id: int):
    is_exam_q = is_exam_question(text, load_classifier_prompt())

    if not is_exam_q:
        send_message(
            chat_id,
            "Я не могу понять вопрос.\n"
            "Пришлите экзаменационный вопрос по «Операционным системам» — фото или текстом."
        )

        return {'ok': True}
    else:
        try:
            answer = generate_answer(text, load_gpt_prompt())
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

        response = requests.get(file_url)
        if response.status_code != 200:
            send_message(chat_id, "Я не могу обработать эту фотографию.")
            
            return {'ok': True}
        
        try:
            recognition_text = recognite_text_on_image(response.content)
        except Exception:
            send_message(chat_id, "Я не могу обработать эту фотографию.")

            return {'ok': True}
        
        handle_text_answer(recognition_text, chat_id)

    else:
        send_message(chat_id, "Я могу обработать только текстовое сообщение или фотографию.")

        return {'ok': True}


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)