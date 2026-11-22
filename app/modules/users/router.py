"""
Модуль управления пользователями.
Транспортный слой: принимает HTTP-запрос и делегирует сценарий сервису.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.core.dependencies import get_current_user
from app.schemas import UserCreate
from app.modules.users.exceptions import EmailAlreadyExistsError
from app.modules.users.repository import UserRepository
from app.modules.users.service import (
    UserForbiddenError,
    UserNotFoundError,
    UserService,
)

router = APIRouter()


@router.post("/register")
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    # Проверка корректности email выполняется Pydantic (EmailStr).
    # Техническая проверка наличия телефона.
    if payload.phone and len(payload.phone) < 10:
        raise HTTPException(
            status_code=400,
            detail="Некорректный формат номера телефона",
        )

    # Сборка архитектурных слоёв.
    repository = UserRepository(db)
    service = UserService(repository)

    # Делегирование выполнения сценария слою бизнес-логики.
    try:
        user = service.register(
            email=payload.email,
            password=payload.password,
            phone=payload.phone,
        )
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email уже зарегистрирован",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "success",
        "user_id": user.id,
        "email": user.email,
    }


@router.post("/me/topup")
def top_up_balance(
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Техническая проверка положительности суммы пополнения.
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Сумма пополнения должна быть положительной",
        )

    repository = UserRepository(db)
    service = UserService(repository)

    try:
        new_balance = service.top_up_balance(
            user_id=current_user.id,
            amount=amount,
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UserForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "success", "new_balance": new_balance}
