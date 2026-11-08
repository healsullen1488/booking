# Интеграционные тесты идут на настоящем PostgreSQL.
# База берётся из TEST_DATABASE_URL. ВНИМАНИЕ: схема public в ней пересоздаётся!
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://booking:booking@localhost:5432/booking_test")
os.environ["DATABASE_URL"] = URL   # до импорта app

from alembic import command                      # noqa: E402
from alembic.config import Config                # noqa: E402
from fastapi.testclient import TestClient        # noqa: E402
from sqlalchemy import create_engine, text       # noqa: E402
from sqlalchemy.exc import OperationalError      # noqa: E402

from app.main import app                         # noqa: E402

TZ = ZoneInfo("Europe/Moscow")
engine = create_engine(URL)


def at(h, m=0, days=3):
    # время через days дней в Москве, строкой ISO
    d = datetime.now(TZ) + timedelta(days=days)
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ).isoformat()


@pytest.fixture(scope="session", autouse=True)
def schema():
    try:
        with engine.connect() as c:
            c = c.execution_options(isolation_level="AUTOCOMMIT")
            c.exec_driver_sql("DROP SCHEMA public CASCADE")
            c.exec_driver_sql("CREATE SCHEMA public")
    except OperationalError:
        pytest.skip("PostgreSQL недоступен (см. TEST_DATABASE_URL)")
    cfg = Config(os.path.join(ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(ROOT, "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def clean(schema):
    with engine.begin() as c:
        c.exec_driver_sql(
            "TRUNCATE booking_history, bookings, room_equipment, rooms, users RESTART IDENTITY CASCADE")
        c.exec_driver_sql("DELETE FROM equipment WHERE id > 4")


@pytest.fixture
def client():
    return TestClient(app)


def make_user(client, email, role_id, name="User", pw="secret1"):
    r = client.post("/auth/register", json={"email": email, "name": name, "password": pw})
    assert r.status_code == 201, r.text
    with engine.begin() as c:
        c.execute(text("UPDATE users SET role_id = :r WHERE id = :i"),
                  {"r": role_id, "i": r.json()["id"]})
    r = client.post("/auth/login", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture
def emp(client):
    return make_user(client, "emp@a.ru", 1)


@pytest.fixture
def emp2(client):
    return make_user(client, "emp2@a.ru", 1)


@pytest.fixture
def man(client):
    return make_user(client, "man@a.ru", 2)


@pytest.fixture
def adm(client):
    return make_user(client, "adm@a.ru", 3)


@pytest.fixture
def room(client, adm):
    r = client.post("/rooms", headers=adm, json={
        "name": "Alpha", "floor": 2, "capacity": 10, "equipment_ids": [1, 2]})
    assert r.status_code == 201, r.text
    return r.json()


def book(client, h, room_id, a, b, people=3, title="Meet"):
    return client.post("/bookings", headers=h, json={
        "room_id": room_id, "start_at": a, "end_at": b, "title": title, "people": people})
