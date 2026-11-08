# Настройки из переменных окружения.
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://booking:booking@localhost:5432/booking")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-please-change-me-32-bytes")
TOKEN_MINUTES = int(os.environ.get("TOKEN_MINUTES", "60"))
WORK_TZ = os.environ.get("WORK_TZ", "Europe/Moscow")
