# Зависимости FastAPI: сессия БД, текущий пользователь, сервисы.
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session as DbSession

from app import config
from app.database import Session
from app.errors import Unauthorized
from app.repos import BookingRepo, EquipRepo, RoomRepo, UserRepo
from app.security import Hasher, Tokens
from app.services.auth import AuthService
from app.services.bookings import BookingService
from app.services.rooms import RoomService

oauth = OAuth2PasswordBearer(tokenUrl="/auth/login")
tokens = Tokens()


def get_db():
    s = Session()
    try:
        yield s
    finally:
        s.close()


def auth_service(s: DbSession = Depends(get_db)):
    return AuthService(UserRepo(s), Hasher(), tokens)


def room_service(s: DbSession = Depends(get_db)):
    return RoomService(RoomRepo(s), EquipRepo(s))


def booking_service(s: DbSession = Depends(get_db)):
    return BookingService(BookingRepo(s), RoomRepo(s), config.WORK_TZ)


def current_user(token: str = Depends(oauth), s: DbSession = Depends(get_db)):
    try:
        data = tokens.decode(token)
        uid = int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise Unauthorized("bad token")
    # роль берём из БД, а не из токена: смена роли действует сразу
    u = UserRepo(s).get(uid)
    if u is None:
        raise Unauthorized("user not found")
    return u
