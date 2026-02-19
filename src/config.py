"""
배포 시 사용하는 환경 변수.
키 이름은 대문자와 언더스코어만 사용합니다.
DB_TYPE: POSTGRESQL | MYSQL | MARIADB | MONGODB
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 포트: WAS_PORT > WEB_PORT > PORT > 기본값 81
PORT = int(os.environ.get("WAS_PORT") or os.environ.get("WEB_PORT") or os.environ.get("PORT") or "81")
DB_TYPE = (os.environ.get("DB_TYPE") or "").strip().upper() or None
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
