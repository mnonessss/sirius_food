"""
Модуль управления доставкой.
Сначала проверяется право пользователя, затем вызов уходит в gRPC-микросервис.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.core.dependencies import get_current_user, require_role
from app.schemas import DeliveryAssign
from app.modules.delivery.grpc_client import DeliveryGrpcClient
from app.modules.delivery.repository import DeliveryRepository
from app.modules.delivery.service import (
    DeliveryForbiddenError,
    DeliveryNotFoundError,
    DeliveryService,
)

router = APIRouter()


def _service(db: Session) -> DeliveryService:
    return DeliveryService(DeliveryRepository(db), DeliveryGrpcClient())


@router.post("/assign")
def assign_courier(
    payload: DeliveryAssign,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service = _service(db)
    try:
        delivery_id = service.assign_courier(payload.order_id, payload.courier_id)
    except DeliveryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except DeliveryForbiddenError as error:
        raise HTTPException(status_code=403, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except ConnectionError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error))

    return {"status": "success", "delivery_id": delivery_id}


@router.get("/order/{order_id}")
def get_delivery(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = _service(db)
    try:
        delivery = service.view_order_delivery(order_id, current_user)
    except DeliveryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except DeliveryForbiddenError as error:
        raise HTTPException(status_code=403, detail=str(error))
    except ConnectionError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error))

    return {"status": "success", **delivery}


@router.patch("/{delivery_id}/complete")
def complete_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = _service(db)
    try:
        service.complete_delivery(delivery_id, current_user)
    except DeliveryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except DeliveryForbiddenError as error:
        raise HTTPException(status_code=403, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except ConnectionError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error))

    return {"status": "success"}
