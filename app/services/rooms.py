# Комнаты и оборудование.
from app import consts
from app.errors import Conflict, Forbidden, Invalid, NotFound


def only_admin(u):
    if u.role_id != consts.ADMIN:
        raise Forbidden("admin only")


def check_page(page, size):
    if page < 1:
        raise Invalid("page must be >= 1")
    if size < 1 or size > 100:
        raise Invalid("size must be 1..100")


class Page:
    def __init__(self, items, total, page, size):
        self.items = items
        self.total = total
        self.page = page
        self.size = size


class RoomService:
    def __init__(self, rooms, equip):
        self.rooms = rooms
        self.equip = equip

    def _check(self, name, floor, capacity):
        if not name or not name.strip():
            raise Invalid("name is empty")
        if capacity < 1:
            raise Invalid("capacity must be positive")
        if floor < -5 or floor > 100:
            raise Invalid("bad floor")

    def _eq(self, ids):
        ids = sorted(set(ids or []))
        found = self.equip.many(ids)
        if len(found) != len(ids):
            raise Invalid("unknown equipment")
        return found

    def create(self, actor, name, floor, capacity, equipment_ids=None):
        only_admin(actor)
        self._check(name, floor, capacity)
        if self.rooms.by_name(name.strip()):
            raise Conflict("room name already used")
        eq = self._eq(equipment_ids)
        r = self.rooms.add(name.strip(), floor, capacity, eq)
        self.rooms.commit()
        return r

    def get(self, room_id):
        r = self.rooms.get(room_id)
        if r is None:
            raise NotFound("room not found")
        return r

    def list(self, min_capacity=None, floor=None, equipment_ids=None,
             only_active=True, page=1, size=20):
        check_page(page, size)
        items, total = self.rooms.find(
            min_capacity, floor, sorted(set(equipment_ids or [])),
            only_active, (page - 1) * size, size)
        return Page(items, total, page, size)

    def update(self, actor, room_id, name, floor, capacity, equipment_ids=None):
        only_admin(actor)
        r = self.get(room_id)
        self._check(name, floor, capacity)
        x = self.rooms.by_name(name.strip())
        if x is not None and x.id != r.id:
            raise Conflict("room name already used")
        eq = self._eq(equipment_ids)
        r.name = name.strip()
        r.floor = floor
        r.capacity = capacity
        r.equipment = eq
        self.rooms.commit()
        return r

    def deactivate(self, actor, room_id):
        # мягкое удаление; старые брони остаются, новые создать нельзя
        only_admin(actor)
        r = self.get(room_id)
        r.is_active = False
        self.rooms.commit()
        return r

    def equipment(self):
        return self.equip.all()

    def add_equipment(self, actor, name):
        only_admin(actor)
        if not name or not name.strip():
            raise Invalid("name is empty")
        if self.equip.by_name(name.strip()):
            raise Conflict("equipment already exists")
        e = self.equip.add(name.strip())
        self.equip.commit()
        return e
