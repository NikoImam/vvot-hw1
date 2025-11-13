import os
import requests
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import uvicorn
from yandex_cloud_ml_sdk import YCloudML
import openai
import json
import base64
import boto3


app = FastAPI()
test_app = TestClient(app)

TG_TOKEN = os.getenv('TG_BOT_TOKEN')
FOLDER_ID=os.getenv('FOLDER_ID')
AI_SA_API_KEY = os.getenv('AI_SA_API_KEY')
CONFIDENCE_LEVEL = float(os.getenv('CONFIDENCE_LEVEL', 0.8))
AI_MODEL = os.getenv('AI_MODEL', "yandexgpt-lite")
STATIC_KEY = os.getenv('STATIC_KEY')
STATIC_KEY_ID = os.getenv('STATIC_KEY_ID')
BUCKET_NAME=os.getenv('BUCKET_NAME')

if not (TG_TOKEN and FOLDER_ID and AI_SA_API_KEY and CONFIDENCE_LEVEL and STATIC_KEY and STATIC_KEY_ID):
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

s3_client = boto3.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=STATIC_KEY_ID,
    aws_secret_access_key=STATIC_KEY
)

def get_object(bucket_name: str, object_name: str):
    object = s3_client.get_object(Bucket=bucket_name, Key=object_name)

    return object['Body'].read().decode('utf-8')

def send_message(chat_id: int, text: str):
    requests.post(f'{API_URL}/sendMessage', json={'chat_id': chat_id, 'text': text})

def load_classifier_prompt():
    return get_object(str(BUCKET_NAME), 'classifier_prompt')

def load_gpt_prompt():
    return get_object(str(BUCKET_NAME), 'gpt_prompt')

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
        input=text
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

def handler(event, context):
    try:
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = {}
    except Exception as e:
        body = {}
        print("Ошибка при разборе тела:", e)

    response = test_app.post("/", json=body)

    return {
        "statusCode": response.status_code,
        "headers": {"Content-Type": "application/json"},
        "body": response.text
    }

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)