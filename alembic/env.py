# Окружение Alembic. Модели не используются: схема описана в db/*.sql.
import os

from alembic import context
from sqlalchemy import create_engine

url = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://booking:booking@localhost:5432/booking")


def run_online():
    engine = create_engine(url)
    with engine.connect() as c:
        context.configure(connection=c, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


run_online()
