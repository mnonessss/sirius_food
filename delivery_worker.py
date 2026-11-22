"""
Consumer для микросервиса доставки. Слушает событие order.paid
и подготавливает доставку. Если курьера нет, публикует DeliveryFailed.
"""
import asyncio
import json

import aio_pika
from aio_pika import ExchangeType

from app.core.config import settings
from app.core.rabbitmq import correlation_id_from_message, publish_event
from app.database import SessionLocal
from app.models import Delivery, Order, ProcessedEvent, Role, User

EXCHANGE_NAME = "sirius_events"
QUEUE_NAME = "delivery_queue"


def _already_processed(db, event_id: str) -> bool:
    return db.query(ProcessedEvent).filter_by(id=event_id).first() is not None


def _mark_processed(db, event_id: str) -> None:
    db.add(ProcessedEvent(id=event_id))
    db.commit()


def _find_free_courier(db):
    """Незаблокированный курьер без активной доставки."""
    couriers = (
        db.query(User)
        .join(Role)
        .filter(Role.name == "courier", User.is_blocked.is_(False))
        .order_by(User.id)
        .all()
    )
    for courier in couriers:
        active = (
            db.query(Delivery)
            .filter(
                Delivery.courier_id == courier.id,
                Delivery.status == "in_progress",
            )
            .first()
        )
        if active is None:
            return courier
    return None


async def process_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        source_event_id = str(payload["event_id"])
        order_id = payload["order_id"]
        handled_id = f"delivery:{source_event_id}"

        db = SessionLocal()
        try:
            if _already_processed(db, handled_id):
                return

            order = db.query(Order).filter(Order.id == order_id).first()
            existing = (
                db.query(Delivery).filter(Delivery.order_id == order_id).first()
                if order is not None
                else None
            )
            courier = _find_free_courier(db) if order is not None and existing is None else None

            if existing is not None:
                print(f"[Delivery] Подготовка доставки для заказа {order_id}")
            elif courier is None:
                amount = payload.get("amount")
                if amount is None and order is not None and order.item is not None:
                    amount = order.item.price * order.quantity
                await publish_event(
                    routing_key="delivery.failed",
                    correlation_id=correlation_id_from_message(message),
                    payload={
                        "event_id": f"delivery-failed:{source_event_id}",
                        "order_id": order_id,
                        "customer_id": payload.get("customer_id"),
                        "amount": amount or 0,
                        "reason": "courier_not_found",
                    },
                )
                print(f"[Delivery] Курьер не найден, DeliveryFailed для заказа {order_id}")
            else:
                db.add(
                    Delivery(
                        order_id=order_id,
                        courier_id=courier.id,
                        status="in_progress",
                    )
                )
                db.commit()
                print(f"[Delivery] Подготовка доставки для заказа {order_id}")

            _mark_processed(db, handled_id)
        finally:
            db.close()


async def main() -> None:
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
    )

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    await queue.bind(exchange, routing_key="order.paid")

    await queue.consume(process_message)
    print("[Delivery] Ждём события order.paid...")

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
