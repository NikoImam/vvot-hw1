# from __future__ import annotations
from yandex_cloud_ml_sdk import YCloudML
import os

request_text = '''df'''
FOLDER_ID=os.getenv('FOLDER_ID')
API_KEY = os.getenv('AI_SA_API_KEY')

def main():
    sdk = YCloudML(
        folder_id=f'{FOLDER_ID}',
        auth=f'{API_KEY}',
    )

    # Sample 1: Zero-shot classification
    model = sdk.models.text_classifiers("yandexgpt-lite").configure(
        task_description="Ты — помощник, который помогает готовить ответы на экзаменационные вопросы по дисциплине \"Операционные системы\"." \
        "Классифицируй, является ли этот экзаменационный билет вопросом по дисциплине \"Операционные системы\"",
        labels=['операционные системы', 'другая дисциплина'],
    )

    result = model.run(request_text)

    print('Zero-shot classification:')

    for prediction in result:
        print(prediction)


if __name__ == "__main__":
    main()
