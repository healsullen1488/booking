# Проверки правил прямо в PostgreSQL: приложение обходим, пишем SQL.
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.api.conftest import engine

T = "2030-01-10 %s+03"   # шаблон времени


def code(e):
    return e.value.orig.pgcode


@pytest.fixture
def ids():
    # роль 1 уже есть в справочнике
    with engine.begin() as c:
        u = c.execute(text(
            "INSERT INTO users (email, name, pass_hash, role_id) "
            "VALUES ('u@a.ru', 'U', 'x', 1) RETURNING id")).scalar()
        r = c.execute(text(
            "INSERT INTO rooms (name, floor, capacity) VALUES ('R', 1, 5) RETURNING id")).scalar()
    return u, r


def add(c, ids, a, b, people=2, status=1):
    return c.execute(text(
        "INSERT INTO bookings (room_id, user_id, status_id, title, people, start_at, end_at) "
        "VALUES (:r, :u, :s, 't', :p, :a, :b) RETURNING id"),
        {"r": ids[1], "u": ids[0], "s": status, "p": people, "a": T % a, "b": T % b}).scalar()


def test_overlap_is_forbidden(ids):
    with engine.begin() as c:
        add(c, ids, "10:00", "12:00")
    with pytest.raises(DBAPIError) as e:
        with engine.begin() as c:
            add(c, ids, "11:00", "13:00")
    assert code(e) == "23P01"


def test_touching_is_allowed(ids):
    with engine.begin() as c:
        add(c, ids, "10:00", "12:00")
        add(c, ids, "12:00", "13:00")
        add(c, ids, "09:00", "10:00")


def test_cancelled_does_not_block(ids):
    with engine.begin() as c:
        b = add(c, ids, "10:00", "12:00")
        c.execute(text("UPDATE bookings SET status_id = 4 WHERE id = :i"), {"i": b})
        add(c, ids, "10:00", "12:00")


def test_people_more_than_capacity(ids):
    with pytest.raises(DBAPIError) as e:
        with engine.begin() as c:
            add(c, ids, "10:00", "11:00", people=6)
    assert code(e) == "23514"


def test_inactive_room(ids):
    with engine.begin() as c:
        c.execute(text("UPDATE rooms SET is_active = false WHERE id = :i"), {"i": ids[1]})
    with pytest.raises(DBAPIError) as e:
        with engine.begin() as c:
            add(c, ids, "10:00", "11:00")
    assert code(e) == "23514"


@pytest.mark.parametrize("a,b,ok", [
    ("10:00", "10:14", False),
    ("10:00", "10:15", True),
    ("10:00", "14:00", True),
    ("10:00", "14:01", False),
    ("10:00", "10:00", False),
    ("11:00", "10:00", False),
])
def test_length_check(ids, a, b, ok):
    if ok:
        with engine.begin() as c:
            add(c, ids, a, b)
    else:
        with pytest.raises(DBAPIError) as e:
            with engine.begin() as c:
                add(c, ids, a, b)
        assert code(e) == "23514"


def test_new_booking_must_be_pending(ids):
    with pytest.raises(DBAPIError) as e:
        with engine.begin() as c:
            add(c, ids, "10:00", "11:00", status=2)
    assert code(e) == "23514"


def test_pending_to_completed_is_forbidden(ids):
    with engine.begin() as c:
        b = add(c, ids, "10:00", "11:00")
    with pytest.raises(DBAPIError) as e:
        with engine.begin() as c:
            c.execute(text("UPDATE bookings SET status_id = 3 WHERE id = :i"), {"i": b})
    assert code(e) == "23514"


def test_allowed_status_chain(ids):
    with engine.begin() as c:
        b = add(c, ids, "10:00", "11:00")
        for st in (2, 3):   # PENDING -> CONFIRMED -> COMPLETED
            c.execute(text("UPDATE bookings SET status_id = :s WHERE id = :i"), {"s": st, "i": b})


def test_closed_booking_is_locked(ids):
    with engine.begin() as c:
        b = add(c, ids, "10:00", "11:00")
        c.execute(text("UPDATE bookings SET status_id = 4 WHERE id = :i"), {"i": b})
    for sql in ("UPDATE bookings SET status_id = 2 WHERE id = :i",
                "UPDATE bookings SET title = 'z' WHERE id = :i"):
        with pytest.raises(DBAPIError) as e:
            with engine.begin() as c:
                c.execute(text(sql), {"i": b})
        assert code(e) == "23514"


def test_email_unique_ignoring_case(ids):
    with pytest.raises(DBAPIError) as e:
        with engine.begin() as c:
            c.execute(text("INSERT INTO users (email, name, pass_hash, role_id) "
                           "VALUES ('U@A.RU', 'U2', 'x', 1)"))
    assert code(e) == "23505"


def test_unknown_role_is_forbidden():
    with pytest.raises(DBAPIError) as e:
        with engine.begin() as c:
            c.execute(text("INSERT INTO users (email, name, pass_hash, role_id) "
                           "VALUES ('z@a.ru', 'Z', 'x', 9)"))
    assert code(e) == "23503"


def test_history_is_append_only(ids):
    with engine.begin() as c:
        b = add(c, ids, "10:00", "11:00")
        c.execute(text(
            "INSERT INTO booking_history (booking_id, user_id, action_id, status_id, start_at, end_at) "
            "VALUES (:b, :u, 1, 1, :a, :e)"), {"b": b, "u": ids[0], "a": T % "10:00", "e": T % "11:00"})
    for sql in ("UPDATE booking_history SET action_id = 2", "DELETE FROM booking_history"):
        with pytest.raises(DBAPIError) as e:
            with engine.begin() as c:
                c.execute(text(sql))
        assert code(e) == "23514"


def test_view_booking_info(ids):
    with engine.begin() as c:
        add(c, ids, "10:00", "11:00")
        row = c.execute(text("SELECT room, status, user_name FROM booking_info")).one()
    assert tuple(row) == ("R", "PENDING", "U")
