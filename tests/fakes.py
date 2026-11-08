# Репозитории в памяти для модульных тестов сервисов. БД не нужна.
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from zoneinfo import ZoneInfo

from app import consts
from app.services import rules
from app.services.auth import AuthService
from app.services.bookings import BookingService
from app.services.rooms import RoomService

TZ = ZoneInfo("Europe/Moscow")
# "сейчас" в тестах: понедельник 9 ноября 2026, 08:00 по Москве
NOW = datetime(2026, 11, 9, 8, 0, tzinfo=TZ)


def t(h, m=0, d=10):
    # время на d-е число ноября 2026, по Москве
    return datetime(2026, 11, d, h, m, tzinfo=TZ)


class FakeUsers:
    def __init__(self):
        self.a = {}
        self.n = 0
        self.commits = 0

    def by_email(self, email):
        for u in self.a.values():
            if u.email.lower() == email.lower():
                return u
        return None

    def get(self, i):
        return self.a.get(i)

    def add(self, email, name, pass_hash, role_id):
        self.n += 1
        u = NS(id=self.n, email=email, name=name, pass_hash=pass_hash, role_id=role_id)
        self.a[u.id] = u
        return u

    def commit(self):
        self.commits += 1


class FakeEquip:
    def __init__(self):
        self.a = {}
        self.n = 0

    def many(self, ids):
        return [self.a[i] for i in ids if i in self.a]

    def all(self):
        return list(self.a.values())

    def by_name(self, name):
        for e in self.a.values():
            if e.name == name:
                return e
        return None

    def add(self, name):
        self.n += 1
        e = NS(id=self.n, name=name)
        self.a[e.id] = e
        return e

    def commit(self):
        pass


class FakeRooms:
    def __init__(self):
        self.a = {}
        self.n = 0
        self.commits = 0

    def get(self, i):
        return self.a.get(i)

    def by_name(self, name):
        for r in self.a.values():
            if r.name == name:
                return r
        return None

    def add(self, name, floor, capacity, eq):
        self.n += 1
        r = NS(id=self.n, name=name, floor=floor, capacity=capacity,
               is_active=True, equipment=list(eq))
        self.a[r.id] = r
        return r

    def find(self, min_capacity, floor, eq_ids, only_active, offset, limit):
        xs = []
        for r in self.a.values():
            if only_active and not r.is_active:
                continue
            if min_capacity is not None and r.capacity < min_capacity:
                continue
            if floor is not None and r.floor != floor:
                continue
            have = {e.id for e in r.equipment}
            if not set(eq_ids) <= have:
                continue
            xs.append(r)
        xs.sort(key=lambda r: r.id)
        return xs[offset:offset + limit], len(xs)

    def commit(self):
        self.commits += 1


class FakeBookings:
    def __init__(self):
        self.a = {}
        self.h = []
        self.n = 0
        self.commits = 0

    def get(self, i):
        return self.a.get(i)

    def add(self, room_id, user_id, title, people, start, end):
        self.n += 1
        b = NS(id=self.n, room_id=room_id, user_id=user_id, status_id=consts.PENDING,
               title=title, people=people, start_at=start, end_at=end)
        self.a[b.id] = b
        return b

    def busy(self, room_id, start, end, skip_id=None):
        for b in self.a.values():
            if b.room_id != room_id or b.id == skip_id:
                continue
            if b.status_id not in consts.ACTIVE:
                continue
            if rules.is_overlap(b.start_at, b.end_at, start, end):
                return True
        return False

    def busy_list(self, room_id, x, y):
        return [(b.start_at, b.end_at) for b in self.a.values()
                if b.room_id == room_id and b.status_id in consts.ACTIVE
                and rules.is_overlap(b.start_at, b.end_at, x, y)]

    def add_history(self, bid, uid, action, status, start, end):
        h = NS(id=len(self.h) + 1, booking_id=bid, user_id=uid, action_id=action,
               status_id=status, start_at=start, end_at=end,
               at=datetime.now(timezone.utc))
        self.h.append(h)
        return h

    def history(self, bid):
        return [h for h in self.h if h.booking_id == bid]

    def find(self, user_id, status_id, offset, limit):
        xs = [b for b in self.a.values()
              if (user_id is None or b.user_id == user_id)
              and (status_id is None or b.status_id == status_id)]
        xs.sort(key=lambda b: b.id)
        return xs[offset:offset + limit], len(xs)

    def commit(self):
        self.commits += 1


class FakeHasher:
    def make(self, p):
        return "h$" + p[::-1]

    def check(self, p, h):
        return h == "h$" + p[::-1]


class FakeTokens:
    def make(self, u):
        return "tok-%s-%s" % (u.id, u.role_id)


class World:
    # всё вместе: репозитории, сервисы и три пользователя разных ролей
    def __init__(self):
        self.users = FakeUsers()
        self.equip = FakeEquip()
        self.rooms = FakeRooms()
        self.books = FakeBookings()
        self.auth = AuthService(self.users, FakeHasher(), FakeTokens())
        self.rs = RoomService(self.rooms, self.equip)
        self.bs = BookingService(self.books, self.rooms, TZ, lambda: NOW)
        self.emp = self.mk("emp@a.ru", consts.EMPLOYEE)
        self.emp2 = self.mk("emp2@a.ru", consts.EMPLOYEE)
        self.man = self.mk("man@a.ru", consts.MANAGER)
        self.adm = self.mk("adm@a.ru", consts.ADMIN)
        self.room = self.rs.create(self.adm, "Alpha", 2, 10, [])

    def mk(self, email, role):
        u = self.auth.register(email, "User", "secret1")
        u.role_id = role
        return u
