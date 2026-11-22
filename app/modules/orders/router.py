import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import OrderCreate
from app.modules.orders.repository import OrderRepository
from app.modules.orders.service import OrderService
from app.core.dependencies import get_current_user, require_role
from app.modules.orders.exceptions import AccessDeniedError, OrderNotFoundError

logger = structlog.get_logger().bind(service="order-service")

router = APIRouter()


@router.post("/create")
def create_order(
    payload: OrderCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Техническая валидация уровня транспортного протокола.
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть больше нуля")

    # Сборка архитектурных слоёв.
    repository = OrderRepository(db)
    service = OrderService(repository)
    started = time.perf_counter()

    # Делегирование выполнения сценария слою бизнес-логики.
    try:
        order_id = service.create_order(
            user_id=current_user.id,
            item_id=payload.item_id,
            quantity=payload.quantity,
        )
    except ValueError as e:
        # Трансляция внутреннего исключения в HTTP-статус.
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(
        "order_created",
        order_id=order_id,
        user_id=current_user.id,
        correlation_id=request.state.correlation_id,
        duration_ms=round((time.perf_counter() - started) * 1000),
    )
    return {"status": "success", "order_id": order_id}


@router.post("/{order_id}/pay")
async def pay_order(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = OrderRepository(db)
    service = OrderService(repository)
    correlation_id = request.state.correlation_id
    try:
        order = await service.pay_order(order_id, current_user, correlation_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    logger.info(
        "order_paid",
        order_id=order.id,
        user_id=current_user.id,
        correlation_id=correlation_id,
    )
    return {"status": "success", "order_id": order.id}


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = OrderRepository(db)
    service = OrderService(repository)
    try:
        service.cancel_order(order_id, current_user)
    except OrderNotFoundError:
        raise HTTPException(404, "Order not found")
    except AccessDeniedError:
        raise HTTPException(403, "Access denied")
    return {"status": "success"}


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Чтение заказа без обработки отсутствия: так Sentry получает ошибку 500."""
    repository = OrderRepository(db)
    order = repository.get_order(order_id)
    if order is None:
        raise RuntimeError(f"Заказ {order_id} не найден")
    return {"order_id": order.id, "status": order.status}


@router.get("/kitchen/orders")
def kitchen_orders(
    current_user: User = Depends(require_role("cook")),
    db: Session = Depends(get_db),
):
    repository = OrderRepository(db)
    service = OrderService(repository)
    return service.get_kitchen_orders()