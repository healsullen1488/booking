from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.routers import auth, bookings, rooms

app = FastAPI(
    title="Сервис бронирования переговорных",
    description="REST API: комнаты, брони, роли EMPLOYEE / MANAGER / ADMIN, JWT.",
    version="1.0.0",
)


@app.exception_handler(AppError)
def on_error(request: Request, e: AppError):
    # единый формат ошибок: {"detail": "..."}
    h = {"WWW-Authenticate": "Bearer"} if e.code == 401 else None
    return JSONResponse(status_code=e.code, content={"detail": e.msg}, headers=h)


app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(bookings.router)


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}
