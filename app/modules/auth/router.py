from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.repository import AuthRepository
from app.modules.auth.exceptions import InvalidRefreshTokenError
from app.modules.auth.service import AuthService, InvalidCredentialsError
from app.core.rate_limit import rate_limit

router = APIRouter()


class LoginSchema(BaseModel):
    """Схема запроса на вход."""
    email: EmailStr
    password: str


class RefreshSchema(BaseModel):
    """Схема запроса на обновление токена."""
    refresh_token: str


@router.post("/login", dependencies=[Depends(rate_limit(5, 60))])
def login(payload: LoginSchema, db: Session = Depends(get_db)):
    """Аутентификация пользователя и выдача пары токенов."""
    repository = AuthRepository(db)
    service = AuthService(repository)
    try:
        return service.login(payload.email, payload.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")


@router.post("/refresh", dependencies=[Depends(rate_limit(5, 60))])
def refresh(token: RefreshSchema, db: Session = Depends(get_db)):
    """Обновление refresh - токена. Старый токен инвалидируется"""
    repository = AuthRepository(db)
    service = AuthService(repository)
    try:
        return service.refresh(token.refresh_token)
    except InvalidRefreshTokenError:
        raise HTTPException(status_code=401, detail="Неверный refresh-токен")
    