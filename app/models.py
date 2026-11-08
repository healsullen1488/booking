# ORM-модели. Таблицы создаёт не SQLAlchemy, а миграции (db/*.sql),
# здесь только сопоставление таблиц с классами.
from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey, Integer,
                        SmallInteger, String, Table, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


room_equipment = Table(
    "room_equipment", Base.metadata,
    Column("room_id", Integer, ForeignKey("rooms.id"), primary_key=True),
    Column("equipment_id", Integer, ForeignKey("equipment.id"), primary_key=True),
)


class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    pass_hash: Mapped[str] = mapped_column(String(100))
    role_id: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    floor: Mapped[int] = mapped_column(SmallInteger)
    capacity: Mapped[int] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    equipment: Mapped[list[Equipment]] = relationship(
        secondary=room_equipment, order_by=Equipment.id, lazy="selectin")


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status_id: Mapped[int] = mapped_column(SmallInteger)
    title: Mapped[str] = mapped_column(String(200))
    people: Mapped[int] = mapped_column(SmallInteger)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class History(Base):
    __tablename__ = "booking_history"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action_id: Mapped[int] = mapped_column(SmallInteger)
    status_id: Mapped[int] = mapped_column(SmallInteger)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
