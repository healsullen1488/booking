# Схемы запросов и ответов (pydantic v2).
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app import consts


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: str
    name: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(Out):
    id: int
    email: str
    name: str
    role_id: int

    @computed_field
    @property
    def role(self) -> str:
        return consts.ROLES[self.role_id]


class RoleIn(BaseModel):
    role: Literal["EMPLOYEE", "MANAGER", "ADMIN"]


class EquipIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class EquipOut(Out):
    id: int
    name: str


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    floor: int
    capacity: int
    equipment_ids: list[int] = []


class RoomOut(Out):
    id: int
    name: str
    floor: int
    capacity: int
    is_active: bool
    equipment: list[EquipOut]


class RoomPage(BaseModel):
    items: list[RoomOut]
    total: int
    page: int
    size: int


class BookingIn(BaseModel):
    room_id: int
    start_at: datetime
    end_at: datetime
    title: str = Field(min_length=1, max_length=200)
    people: int


class MoveIn(BaseModel):
    start_at: datetime
    end_at: datetime
    room_id: Optional[int] = None


class BookingOut(Out):
    id: int
    room_id: int
    user_id: int
    status_id: int
    title: str
    people: int
    start_at: datetime
    end_at: datetime

    @computed_field
    @property
    def status(self) -> str:
        return consts.STATUSES[self.status_id]


class BookingPage(BaseModel):
    items: list[BookingOut]
    total: int
    page: int
    size: int


class HistoryOut(Out):
    id: int
    booking_id: int
    user_id: int
    action_id: int
    status_id: int
    start_at: datetime
    end_at: datetime
    at: datetime

    @computed_field
    @property
    def action(self) -> str:
        return consts.ACTIONS[self.action_id]

    @computed_field
    @property
    def status(self) -> str:
        return consts.STATUSES[self.status_id]


class Slot(BaseModel):
    start_at: datetime
    end_at: datetime


class FreeOut(BaseModel):
    room_id: int
    day: date
    slots: list[Slot]
