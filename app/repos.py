# Репозитории: единственное место, где есть SQLAlchemy и SQL.
# Ошибки PostgreSQL переводятся в наши ошибки (коды SQLSTATE).
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import consts
from app.errors import Conflict, Invalid
from app.models import Booking, Equipment, History, Room, User


def translate(e):
    # SQLSTATE: 23P01 - EXCLUDE, 23505 - UNIQUE, 23514 - CHECK/триггер, 23503 - внешний ключ
    o = e.orig
    code = getattr(o, "pgcode", None) or getattr(o, "sqlstate", None)
    text = str(o).split("\n")[0]
    if code == "23P01":
        return Conflict("room is busy at this time")
    if code == "23505":
        return Conflict("already exists")
    if code == "23514":
        return Invalid(text)
    if code == "23503":
        return Invalid("bad reference")
    return e


def flush(s):
    try:
        s.flush()
    except IntegrityError as e:
        s.rollback()
        x = translate(e)
        if x is e:
            raise
        raise x from None


def commit(s):
    try:
        s.commit()
    except IntegrityError as e:
        s.rollback()
        x = translate(e)
        if x is e:
            raise
        raise x from None


class Repo:
    def __init__(self, s):
        self.s = s

    def commit(self):
        commit(self.s)


class UserRepo(Repo):
    def get(self, i):
        return self.s.get(User, i)

    def by_email(self, email):
        q = select(User).where(func.lower(User.email) == email.lower())
        return self.s.scalars(q).first()

    def add(self, email, name, pass_hash, role_id):
        u = User(email=email, name=name, pass_hash=pass_hash, role_id=role_id)
        self.s.add(u)
        flush(self.s)
        return u


class EquipRepo(Repo):
    def all(self):
        return list(self.s.scalars(select(Equipment).order_by(Equipment.id)))

    def many(self, ids):
        if not ids:
            return []
        q = select(Equipment).where(Equipment.id.in_(ids)).order_by(Equipment.id)
        return list(self.s.scalars(q))

    def by_name(self, name):
        return self.s.scalars(select(Equipment).where(Equipment.name == name)).first()

    def add(self, name):
        e = Equipment(name=name)
        self.s.add(e)
        flush(self.s)
        return e


class RoomRepo(Repo):
    def get(self, i):
        return self.s.get(Room, i)

    def by_name(self, name):
        return self.s.scalars(select(Room).where(Room.name == name)).first()

    def add(self, name, floor, capacity, eq):
        r = Room(name=name, floor=floor, capacity=capacity, is_active=True, equipment=list(eq))
        self.s.add(r)
        flush(self.s)
        return r

    def find(self, min_capacity, floor, eq_ids, only_active, offset, limit):
        q = select(Room)
        if only_active:
            q = q.where(Room.is_active.is_(True))
        if min_capacity is not None:
            q = q.where(Room.capacity >= min_capacity)
        if floor is not None:
            q = q.where(Room.floor == floor)
        for i in eq_ids:
            # комната должна иметь всё оборудование из списка
            q = q.where(Room.equipment.any(Equipment.id == i))
        total = self.s.scalar(select(func.count()).select_from(q.subquery()))
        items = self.s.scalars(q.order_by(Room.id).offset(offset).limit(limit)).all()
        return list(items), total


class BookingRepo(Repo):
    def get(self, i):
        return self.s.get(Booking, i)

    def add(self, room_id, user_id, title, people, start, end):
        b = Booking(room_id=room_id, user_id=user_id, status_id=consts.PENDING,
                    title=title, people=people, start_at=start, end_at=end)
        self.s.add(b)
        flush(self.s)
        return b

    def busy(self, room_id, start, end, skip_id=None):
        # есть ли активная бронь, которая пересекается с [start, end)
        q = select(Booking.id).where(Booking.room_id == room_id,
                                     Booking.status_id.in_(consts.ACTIVE),
                                     Booking.start_at < end,
                                     Booking.end_at > start)
        if skip_id is not None:
            q = q.where(Booking.id != skip_id)
        return self.s.scalars(q.limit(1)).first() is not None

    def busy_list(self, room_id, x, y):
        q = select(Booking.start_at, Booking.end_at).where(
            Booking.room_id == room_id,
            Booking.status_id.in_(consts.ACTIVE),
            Booking.start_at < y,
            Booking.end_at > x)
        return [(a, b) for a, b in self.s.execute(q)]

    def add_history(self, bid, uid, action, status, start, end):
        h = History(booking_id=bid, user_id=uid, action_id=action, status_id=status,
                    start_at=start, end_at=end)
        self.s.add(h)
        flush(self.s)
        return h

    def history(self, bid):
        q = select(History).where(History.booking_id == bid).order_by(History.at, History.id)
        return list(self.s.scalars(q))

    def find(self, user_id, status_id, offset, limit):
        q = select(Booking)
        if user_id is not None:
            q = q.where(Booking.user_id == user_id)
        if status_id is not None:
            q = q.where(Booking.status_id == status_id)
        total = self.s.scalar(select(func.count()).select_from(q.subquery()))
        items = self.s.scalars(
            q.order_by(Booking.start_at, Booking.id).offset(offset).limit(limit)).all()
        return list(items), total
