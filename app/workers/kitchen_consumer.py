"""
Consumer для кухни. Слушает событие order.paid и регистрирует заказ в очереди кухни.
"""
import asyncio
import json
import aio_pika
import structlog
from aio_pika import ExchangeType

from opentelemetry import trace

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rabbitmq import correlation_id_from_message, trace_context_from_message
from app.core.tracing import setup_tracing
from app.database import SessionLocal
from app.models import KitchenOrder, ProcessedEvent

setup_logging()
setup_tracing("kitchen")
logger = structlog.get_logger().bind(service="kitchen")
tracer = trace.get_tracer("kitchen")

EXCHANGE_NAME = "sirius_events"
QUEUE_NAME = "kitchen_queue"


async def process_message(message: aio_pika.IncomingMessage) -> None:
    """
    Обрабатывает одно сообщение.
    Проверяет идемпотентность, затем создаёт запись для кухни.
    """
    async with message.process():
        payload = json.loads(message.body)
        event_id = payload["event_id"]
        order_id = payload["order_id"]
        correlation_id = correlation_id_from_message(message)
        parent = trace_context_from_message(message)

        with tracer.start_as_current_span("Kitchen.consume", context=parent) as span:
            span.set_attribute("order_id", order_id)
            span.set_attribute("correlation_id", correlation_id)
            db = SessionLocal()
            try:
                # Идемпотентность: если событие уже обработано — пропускаем.
                exists = db.query(ProcessedEvent).filter_by(id=event_id).first()
                if exists:
                    return

                # Создаём запись для кухни.
                db.add(KitchenOrder(order_id=order_id, status="pending"))
                db.add(ProcessedEvent(id=event_id))
                db.commit()
                logger.info(
                    "order_received",
                    order_id=order_id,
                    correlation_id=correlation_id,
                )
            finally:
                db.close()


async def main() -> None:
    """Запускает consumer и слушает очередь кухни."""
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)  # не берём больше 10 сообщений одновременно

    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
    )

    # Очередь с настройкой DLQ.
    queue = await channel.declare_queue(
        QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "dlx_exchange",
            "x-dead-letter-routing-key": "kitchen.dlq",
        },
    )

    # Привязываем очередь к exchange с ключом order.paid.
    await queue.bind(exchange, routing_key="order.paid")

    await queue.consume(process_message)
    logger.info("kitchen_waiting", queue=QUEUE_NAME)

    await asyncio.Future()  # бесконечное ожидание


if __name__ == "__main__":
    asyncio.run(main())