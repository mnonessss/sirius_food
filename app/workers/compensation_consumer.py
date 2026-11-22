"""
Слушает DeliveryFailed и компенсирует оплату: отмена заказа и возврат денег.
Повтор того же event_id деньги второй раз не возвращает.
"""
import asyncio
import json

import aio_pika
from aio_pika import ExchangeType

from app.core.config import settings
from app.core.rabbitmq import correlation_id_from_message, publish_event
from app.database import SessionLocal
from app.models import Order, ProcessedEvent, User

EXCHANGE_NAME = "sirius_events"
QUEUE_NAME = "compensation_queue"


async def process_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        event_id = str(payload["event_id"])
        order_id = payload["order_id"]
        amount = float(payload.get("amount") or 0)

        db = SessionLocal()
        try:
            if db.query(ProcessedEvent).filter_by(id=event_id).first():
                print(f"[Compensation] событие {event_id} уже обработано")
                return

            order = db.query(Order).filter(Order.id == order_id).first()
            if order is not None and order.status != "cancelled":
                user = db.query(User).filter(User.id == order.user_id).first()
                if user is not None:
                    user.balance += amount
                    print(
                        f"[Compensation] возврат {amount} пользователю {user.id}, "
                        f"заказ {order_id} отменён"
                    )
                order.status = "cancelled"
                db.commit()

            await publish_event(
                routing_key="order.cancelled",
                correlation_id=correlation_id_from_message(message),
                payload={
                    "event_id": event_id,
                    "order_id": order_id,
                    "customer_id": payload.get("customer_id"),
                    "amount": amount,
                },
            )
            db.add(ProcessedEvent(id=event_id))
            db.commit()
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
    await queue.bind(exchange, routing_key="delivery.failed")

    await queue.consume(process_message)
    print("[Compensation] Ждём события delivery.failed...")

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
