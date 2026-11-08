# Сервис бронирования переговорных комнат

REST API для бизнес-центра или коворкинга: сотрудники бронируют комнаты, менеджеры
подтверждают брони, администратор управляет комнатами и ролями.

**Стек:** Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 16, Alembic, JWT (PyJWT), bcrypt,
pytest, Docker Compose.

## Возможности

* CRUD комнат с оборудованием, фильтры (вместимость, этаж, оборудование), пагинация,
  мягкое удаление (`is_active`).
* Брони: проверка пересечений, длительность 15 мин – 4 ч, не в прошлом, участников не больше
  вместимости, рабочее время 09:00–21:00, поиск свободных окон, перенос, отмена.
* Жизненный цикл: PENDING → CONFIRMED → COMPLETED, PENDING / CONFIRMED → CANCELLED.
* Роли EMPLOYEE / MANAGER / ADMIN, JWT, bcrypt.
* Журнал изменений `booking_history` и эндпоинт истории.
* Пересечения и остальные правила защищены ещё и в PostgreSQL (`EXCLUDE`, `CHECK`, триггеры).

## Запуск

```bash
docker-compose up --build
```

Поднимутся PostgreSQL и API; миграции применяются автоматически.
Swagger UI: <http://localhost:8000/docs>, OpenAPI: <http://localhost:8000/openapi.json>.

Первый администратор (остальные роли выдаёт ADMIN через `PATCH /users/{id}/role`):

```bash
docker-compose exec api python scripts/make_admin.py admin@example.com Admin secret123
```

Без Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg2://booking:booking@localhost:5432/booking
alembic upgrade head
uvicorn app.main:app --reload
```

## Примеры запросов (curl)

```bash
# регистрация и вход
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
     -d '{"email":"ivan@example.com","name":"Иван","password":"secret123"}'
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
     -d 'username=ivan@example.com&password=secret123' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# комнаты (создаёт ADMIN; тот же вход под admin@example.com)
curl -X POST localhost:8000/rooms -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
     -d '{"name":"Альфа","floor":2,"capacity":10,"equipment_ids":[1,2]}'
curl 'localhost:8000/rooms?min_capacity=8&equipment_id=1&page=1&size=10' -H "Authorization: Bearer $TOKEN"

# бронь
curl -X POST localhost:8000/bookings -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"room_id":1,"start_at":"2030-01-10T10:00:00+03:00","end_at":"2030-01-10T11:00:00+03:00","title":"Планёрка","people":5}'
# повтор на то же время -> 409 Conflict

# свободные окна на дату
curl 'localhost:8000/rooms/1/free?day=2030-01-10&minutes=30' -H "Authorization: Bearer $TOKEN"

# подтверждение (MANAGER или ADMIN) и история
curl -X POST localhost:8000/bookings/1/confirm -H "Authorization: Bearer $MANAGER_TOKEN"
curl localhost:8000/bookings/1/history -H "Authorization: Bearer $TOKEN"
```

## Тесты

```bash
# модульные: сервисный слой без БД и без установки пакетов
python -m unittest discover -s tests/unit -t .
python scripts/cover.py                      # покрытие сервисного слоя (стандартный trace)

# покрытие через pytest-cov и HTML-отчёт
pytest tests/unit --cov=app/services --cov-report=html:docs/coverage_report

# интеграционные: нужен PostgreSQL, отдельная база (схема в ней пересоздаётся!)
createdb booking_test
export TEST_DATABASE_URL=postgresql+psycopg2://booking:booking@localhost:5432/booking_test
pytest tests/api
```

## Структура

| Путь | Назначение |
| --- | --- |
| `app/routers` | HTTP-эндпоинты |
| `app/services` | бизнес-логика (`rules.py` — чистые функции) |
| `app/repos.py` | SQLAlchemy и перевод ошибок PostgreSQL |
| `app/models.py`, `schemas.py` | ORM-модели, схемы pydantic |
| `app/security.py`, `deps.py` | bcrypt, JWT, зависимости FastAPI |
| `db/` | SQL: таблицы, ограничения, триггеры, справочники, примеры запросов |
| `alembic/` | миграции (читают SQL из `db/`) |
| `tests/unit`, `tests/api` | модульные и интеграционные тесты |
| `docs/` | `design.md`, `normalization.md`, диаграммы |

Подробности: `docs/design.md` (архитектура, эндпоинты, права) и `docs/normalization.md`
(нормальные формы до 5НФ, НФБК и ДКНФ).
