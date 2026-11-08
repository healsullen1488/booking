from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app import consts
from app.deps import auth_service, current_user
from app.schemas import RegisterIn, RoleIn, TokenOut, UserOut
from app.services.auth import AuthService

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserOut, status_code=201)
def register(x: RegisterIn, svc: AuthService = Depends(auth_service)):
    return svc.register(x.email, x.name, x.password)


@router.post("/auth/login", response_model=TokenOut)
def login(f: OAuth2PasswordRequestForm = Depends(), svc: AuthService = Depends(auth_service)):
    # username - это e-mail, так работает кнопка Authorize в Swagger
    return TokenOut(access_token=svc.login(f.username, f.password))


@router.get("/users/me", response_model=UserOut)
def me(u=Depends(current_user)):
    return u


@router.patch("/users/{user_id}/role", response_model=UserOut)
def set_role(user_id: int, x: RoleIn, u=Depends(current_user),
             svc: AuthService = Depends(auth_service)):
    names = {v: k for k, v in consts.ROLES.items()}
    return svc.set_role(u, user_id, names[x.role])
