from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app import consts
from app.deps import booking_service, current_user, room_service
from app.schemas import EquipIn, EquipOut, FreeOut, RoomIn, RoomOut, RoomPage, Slot
from app.services.bookings import BookingService
from app.services.rooms import RoomService

router = APIRouter(tags=["rooms"])


@router.get("/equipment", response_model=list[EquipOut])
def equipment(u=Depends(current_user), svc: RoomService = Depends(room_service)):
    return svc.equipment()


@router.post("/equipment", response_model=EquipOut, status_code=201)
def add_equipment(x: EquipIn, u=Depends(current_user), svc: RoomService = Depends(room_service)):
    return svc.add_equipment(u, x.name)


@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(x: RoomIn, u=Depends(current_user), svc: RoomService = Depends(room_service)):
    return svc.create(u, x.name, x.floor, x.capacity, x.equipment_ids)


@router.get("/rooms", response_model=RoomPage)
def list_rooms(
        min_capacity: Optional[int] = Query(None, ge=1, description="вместимость не меньше"),
        floor: Optional[int] = Query(None, description="этаж"),
        equipment_id: list[int] = Query([], description="нужное оборудование (можно несколько)"),
        only_active: bool = True,
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        u=Depends(current_user),
        svc: RoomService = Depends(room_service)):
    return svc.list(min_capacity, floor, equipment_id, only_active, page, size)


@router.get("/rooms/{room_id}", response_model=RoomOut)
def get_room(room_id: int, u=Depends(current_user), svc: RoomService = Depends(room_service)):
    return svc.get(room_id)


@router.put("/rooms/{room_id}", response_model=RoomOut)
def update_room(room_id: int, x: RoomIn, u=Depends(current_user),
                svc: RoomService = Depends(room_service)):
    return svc.update(u, room_id, x.name, x.floor, x.capacity, x.equipment_ids)


@router.delete("/rooms/{room_id}", response_model=RoomOut)
def deactivate_room(room_id: int, u=Depends(current_user),
                    svc: RoomService = Depends(room_service)):
    # мягкое удаление: is_active = false
    return svc.deactivate(u, room_id)


@router.get("/rooms/{room_id}/free", response_model=FreeOut)
def free(room_id: int, day: date,
         minutes: int = Query(consts.MIN_MIN, ge=1, description="минимальная длина окна"),
         u=Depends(current_user),
         svc: BookingService = Depends(booking_service)):
    xs = svc.free(room_id, day, minutes)
    return FreeOut(room_id=room_id, day=day,
                   slots=[Slot(start_at=a, end_at=b) for a, b in xs])
