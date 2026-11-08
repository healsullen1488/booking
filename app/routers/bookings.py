from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.deps import booking_service, current_user
from app.schemas import BookingIn, BookingOut, BookingPage, HistoryOut, MoveIn
from app.services.bookings import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=201)
def create(x: BookingIn, u=Depends(current_user), svc: BookingService = Depends(booking_service)):
    return svc.create(u, x.room_id, x.start_at, x.end_at, x.title, x.people)


@router.get("", response_model=BookingPage)
def list_bookings(
        show_all: bool = Query(False, alias="all", description="все брони (MANAGER, ADMIN)"),
        status_id: Optional[int] = Query(None, description="фильтр по статусу, только с all=true"),
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        u=Depends(current_user),
        svc: BookingService = Depends(booking_service)):
    if show_all:
        return svc.all(u, status_id, page, size)
    return svc.mine(u, page, size)


@router.get("/{bid}", response_model=BookingOut)
def get_one(bid: int, u=Depends(current_user), svc: BookingService = Depends(booking_service)):
    return svc.get(u, bid)


@router.put("/{bid}/move", response_model=BookingOut)
def move(bid: int, x: MoveIn, u=Depends(current_user),
         svc: BookingService = Depends(booking_service)):
    return svc.move(u, bid, x.start_at, x.end_at, x.room_id)


@router.post("/{bid}/confirm", response_model=BookingOut)
def confirm(bid: int, u=Depends(current_user), svc: BookingService = Depends(booking_service)):
    return svc.confirm(u, bid)


@router.post("/{bid}/complete", response_model=BookingOut)
def complete(bid: int, u=Depends(current_user), svc: BookingService = Depends(booking_service)):
    return svc.complete(u, bid)


@router.post("/{bid}/cancel", response_model=BookingOut)
def cancel(bid: int, u=Depends(current_user), svc: BookingService = Depends(booking_service)):
    return svc.cancel(u, bid)


@router.get("/{bid}/history", response_model=list[HistoryOut])
def history(bid: int, u=Depends(current_user), svc: BookingService = Depends(booking_service)):
    return svc.history(u, bid)
