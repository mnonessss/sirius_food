"""
Модуль управления меню столовой.
Транспортный слой: принимает HTTP-запрос и делегирует сценарий сервису.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.core.dependencies import get_current_user, require_role
from app.schemas import MenuItemCreate, MenuItemUpdate
from app.modules.menu.repository import MenuRepository
from app.modules.menu.service import (
    CategoryNotFoundError,
    MenuItemNotFoundError,
    MenuService,
)

router = APIRouter()


@router.get("/items")
def list_menu_items(db: Session = Depends(get_db)):
    """Публичная витрина: SSR-фронтенд читает меню без токена."""
    service = MenuService(MenuRepository(db))
    return service.list_items()


@router.get("/items/{item_id}")
def get_menu_item(item_id: int, db: Session = Depends(get_db)):
    """Одно блюдо или 404. Публично, как в контракте витрины."""
    service = MenuService(MenuRepository(db))
    try:
        return service.get_item(item_id)
    except MenuItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/items")
def create_menu_item(
    payload: MenuItemCreate,
    current_user: User = Depends(require_role("admin", "cook")),
    db: Session = Depends(get_db),
):
    # Техническая валидация цены и названия.
    if payload.price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Цена должна быть положительной",
        )

    if len(payload.name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Название блюда слишком короткое",
        )

    # Сборка архитектурных слоёв.
    repository = MenuRepository(db)
    service = MenuService(repository)

    try:
        item_id = service.create_item(
            name=payload.name,
            price=payload.price,
            category_id=payload.category_id,
        )
    except CategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "success", "item_id": item_id}


@router.patch("/items/{item_id}")
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    current_user: User = Depends(require_role("admin", "cook")),
    db: Session = Depends(get_db),
):
    # Техническая валидация нового значения цены.
    if payload.price is not None and payload.price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Цена должна быть положительной",
        )

    repository = MenuRepository(db)
    service = MenuService(repository)

    try:
        updated_id = service.update_item(
            item_id=item_id,
            name=payload.name,
            price=payload.price,
            is_available=payload.is_available,
            category_id=payload.category_id,
        )
    except (MenuItemNotFoundError, CategoryNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status": "success", "item_id": updated_id}


@router.get("/categories/{category_id}")
def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MenuService(MenuRepository(db))
    try:
        category = service.get_category(category_id)
    except CategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "success", "category": category}
