import openai
import json
# without search index
YANDEX_CLOUD_FOLDER = "b1g95o84ll543gh2kfu3"
YANDEX_CLOUD_API_KEY = "AQVN2h8qK_FynLCbpqE8nSMIKkjlZk8uhv7s0Swt"
YANDEX_CLOUD_MODEL = "yandexgpt-lite"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER
)

response = client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    temperature=0.3,
    instructions='''Ты — помощник, который помогает готовить ответы на экзаменационные вопросы по дисциплине "Операционные системы". 
После получения вопроса определи, сможешь ли ты на него ответить (относится ли данный вопрос к требуемой дисциплине). Если в запросе несколько вопросов, определи причастность каждого вопроса к теме.
Если вопрос относится к данной дисциплине, подготовь РАЗВЁРНУТЫЙ ответ: определения, ключевые пункты и пример (если уместно).
Внимание: каждый развёрнутый ответ на каждый из вопросов в отдельном блоке.
Ответ на запрос должен быть в формате JSON без всякого форматирования (HTML, Markdown и т.д.).
Формат JSON: {is_ready: True/False, response: "[Ответ на вопрос]"}. is_ready означает, смог ли ты подготовить ответ. Если запрос не по теме, то не смог подготовить.
-Отвечай по теме, не уходя на сторонние рассуждения.
-Максимум слов - 400.
-Ответ на русском языке.
-Выдели термины.
-Если вопросов несколько, верни ответ в виде списка в JSON.
-Ответ должен максимально раскрыть вопрос
''',
    input='''1.Управление памятью: Сегментная и сегментно-страничная организации памяти.
2.Кооперация процессов: Семафоры.''',
    max_output_tokens=500
)

data = json.loads(response.output_text.replace("```", ""))

data = [item.get('response') for item in data if item.get('is_ready')]

if len(data) > 0:
    combined = "\n\n".join(data)
    print(combined)