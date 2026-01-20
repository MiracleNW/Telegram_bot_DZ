import json
import os
import boto3
from botocore.client import Config
import logging

BUCKET = os.getenv("BUCKET_NAME")
FILE_KEY = "users.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YC_ACCESS_KEY_ID = os.getenv("YC_ACCESS_KEY_ID")
YC_SECRET_ACCESS_KEY = os.getenv("YC_SECRET_ACCESS_KEY")

s3 = boto3.client(
    "s3",
    endpoint_url="https://storage.yandexcloud.net",
    aws_access_key_id=YC_ACCESS_KEY_ID,
    aws_secret_access_key=YC_SECRET_ACCESS_KEY,
    config=Config(signature_version='s3')
)

def load_users():
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=FILE_KEY)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        logger.info("Users загружены из Object Storage")
        return data
    except s3.exceptions.NoSuchKey:
        logger.warning("users.json не найден, создаю пустой")
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки users.json: {e}")
        raise

users = load_users()

def save_users():
    s3.put_object(
        Bucket=BUCKET,
        Key=FILE_KEY,
        Body=json.dumps(users, ensure_ascii=False, indent=2).encode("utf-8")
    )
    logger.info("users.json сохранён")
