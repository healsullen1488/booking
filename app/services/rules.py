# Чистые функции правил. Без БД и без FastAPI.
from datetime import datetime, timedelta, time

from app import consts
from app.errors import Invalid


def is_overlap(a1, a2, b1, b2):
    # интервалы [a1, a2) и [b1, b2) пересекаются, если a1 < b2 и b1 < a2.
    # "встык" (a2 == b1) пересечением не считается
    return a1 < b2 and b1 < a2


def check_time(start, end, now, tz):
    # проверки по порядку; первая неудачная даёт Invalid
    if start.tzinfo is None or end.tzinfo is None:
        raise Invalid("time must have timezone")
    if end <= start:
        raise Invalid("end must be after start")
    d = end - start
    if d < timedelta(minutes=consts.MIN_MIN):
        raise Invalid("booking is shorter than 15 minutes")
    if d > timedelta(minutes=consts.MAX_MIN):
        raise Invalid("booking is longer than 4 hours")
    if start < now:
        raise Invalid("start is in the past")
    a = start.astimezone(tz)
    b = end.astimezone(tz)
    if a.date() != b.date():
        # бронь до ровно 21:00 заканчивается в тот же день, так что полночь сюда не попадает
        raise Invalid("booking must be inside one day")
    if a.time() < time(consts.OPEN_H) or b.time() > time(consts.CLOSE_H):
        raise Invalid("work time is 09:00-21:00")


def check_people(people, capacity):
    if people < 1:
        raise Invalid("people must be positive")
    if people > capacity:
        raise Invalid("people more than room capacity")


def can_move(a, b):
    # можно ли поменять статус a -> b
    return b in consts.MOVES.get(a, ())


def day_window(day, tz):
    # рабочее окно даты day (datetime.date) в часовом поясе tz
    x = datetime(day.year, day.month, day.day, consts.OPEN_H, tzinfo=tz)
    y = datetime(day.year, day.month, day.day, consts.CLOSE_H, tzinfo=tz)
    return x, y


def free_slots(busy, day, tz, now, minutes=consts.MIN_MIN):
    # busy - список (start, end) занятых интервалов
    # возвращает список свободных (start, end) не короче minutes минут
    x, y = day_window(day, tz)
    if now.astimezone(tz) > x:
        x = now.astimezone(tz)
    need = timedelta(minutes=minutes)
    res = []
    cur = x
    for s, e in sorted(busy):
        s = s.astimezone(tz)
        e = e.astimezone(tz)
        if e <= cur:
            continue
        if s >= y:
            break
        if s > cur and s - cur >= need:
            res.append((cur, s))
        if e > cur:
            cur = e
    if cur < y and y - cur >= need:
        res.append((cur, y))
    return res
