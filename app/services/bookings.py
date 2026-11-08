# Бронирования: создание, перенос, смена статуса, права, журнал.
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app import consts
from app.errors import Conflict, Forbidden, Invalid, NotFound
from app.services import rules
from app.services.rooms import Page, check_page


def is_boss(u):
    return u.role_id in (consts.MANAGER, consts.ADMIN)


class BookingService:
    def __init__(self, bookings, rooms, tz="Europe/Moscow", now=None):
        self.bookings = bookings
        self.rooms = rooms
        self.tz = ZoneInfo(tz) if isinstance(tz, str) else tz
        # now - функция без аргументов; в тестах подставляем своё время
        self.now = now or (lambda: datetime.now(timezone.utc))

    # --- служебное ---

    def _room(self, room_id):
        r = self.rooms.get(room_id)
        if r is None:
            raise NotFound("room not found")
        return r

    def _get(self, actor, bid):
        b = self.bookings.get(bid)
        if b is None:
            raise NotFound("booking not found")
        if b.user_id != actor.id and not is_boss(actor):
            raise Forbidden("not your booking")
        return b

    def _check_all(self, r, start, end, people, skip_id=None):
        # все правила для комнаты r и интервала; общий код для create и move
        if not r.is_active:
            raise Conflict("room is not active")
        rules.check_time(start, end, self.now(), self.tz)
        rules.check_people(people, r.capacity)
        if self.bookings.busy(r.id, start, end, skip_id):
            raise Conflict("room is busy at this time")

    def _log(self, b, actor, action):
        # запись журнала со снимком брони
        self.bookings.add_history(b.id, actor.id, action, b.status_id, b.start_at, b.end_at)

    # --- операции ---

    def create(self, actor, room_id, start, end, title, people):
        if not title or not title.strip():
            raise Invalid("title is empty")
        r = self._room(room_id)
        self._check_all(r, start, end, people)
        b = self.bookings.add(r.id, actor.id, title.strip(), people, start, end)
        self._log(b, actor, consts.A_CREATE)
        self.bookings.commit()
        return b

    def get(self, actor, bid):
        return self._get(actor, bid)

    def mine(self, actor, page=1, size=20):
        check_page(page, size)
        items, total = self.bookings.find(actor.id, None, (page - 1) * size, size)
        return Page(items, total, page, size)

    def all(self, actor, status_id=None, page=1, size=20):
        if not is_boss(actor):
            raise Forbidden("manager or admin only")
        check_page(page, size)
        if status_id is not None and status_id not in consts.STATUSES:
            raise Invalid("unknown status")
        items, total = self.bookings.find(None, status_id, (page - 1) * size, size)
        return Page(items, total, page, size)

    def move(self, actor, bid, start, end, room_id=None):
        b = self._get(actor, bid)
        if b.status_id not in consts.ACTIVE:
            raise Conflict("closed booking can not be moved")
        r = self._room(room_id if room_id is not None else b.room_id)
        self._check_all(r, start, end, b.people, skip_id=b.id)
        b.room_id = r.id
        b.start_at = start
        b.end_at = end
        self._log(b, actor, consts.A_MOVE)
        self.bookings.commit()
        return b

    def _change(self, actor, bid, to, action):
        # единственное место, где меняется статус
        b = self._get(actor, bid)
        if not rules.can_move(b.status_id, to):
            raise Conflict("can not move from %s to %s" % (
                consts.STATUSES[b.status_id], consts.STATUSES[to]))
        b.status_id = to
        self._log(b, actor, action)
        self.bookings.commit()
        return b

    def confirm(self, actor, bid):
        if not is_boss(actor):
            raise Forbidden("manager or admin only")
        return self._change(actor, bid, consts.CONFIRMED, consts.A_CONFIRM)

    def complete(self, actor, bid):
        if not is_boss(actor):
            raise Forbidden("manager or admin only")
        return self._change(actor, bid, consts.COMPLETED, consts.A_COMPLETE)

    def cancel(self, actor, bid):
        return self._change(actor, bid, consts.CANCELLED, consts.A_CANCEL)

    def history(self, actor, bid):
        self._get(actor, bid)
        return self.bookings.history(bid)

    def free(self, room_id, day, minutes=consts.MIN_MIN):
        r = self._room(room_id)
        if minutes < 1:
            raise Invalid("minutes must be positive")
        if not r.is_active:
            return []
        x, y = rules.day_window(day, self.tz)
        busy = self.bookings.busy_list(r.id, x, y)
        return rules.free_slots(busy, day, self.tz, self.now(), minutes)
