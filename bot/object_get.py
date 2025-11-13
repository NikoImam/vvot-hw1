import os
import boto3

STATIC_KEY = os.getenv('STATIC_KEY')
STATIC_KEY_ID = os.getenv('STATIC_KEY_ID')

s3_client = boto3.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=STATIC_KEY_ID,
    aws_secret_access_key=STATIC_KEY
)

object = s3_client.get_object(Bucket='hw1-vvot05',Key='gpt_prompt')

print(object['Body'].read().decode('utf-8'))