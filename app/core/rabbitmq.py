"""
Инфраструктурный модуль для работы с RabbitMQ.
Обеспечивает подключение и публикацию сообщений в exchange.
"""
import aio_pika
from aio_pika import ExchangeType
from opentelemetry import propagate, trace

from app.core.config import settings

# Единый exchange для всех событий проекта.
EXCHANGE_NAME = "sirius_events"


async def get_connection() -> aio_pika.RobustConnection:
    """Создаёт подключение к RabbitMQ. Robust — автоматически переподключается."""
    return await aio_pika.connect_robust(settings.RABBITMQ_URL)


def trace_context_from_message(message: aio_pika.IncomingMessage):
    """Достаёт traceparent из заголовков, чтобы span кухни продолжил трейс монолита."""
    carrier: dict[str, str] = {}
    for key, value in (message.headers or {}).items():
        if isinstance(value, bytes):
            value = value.decode()
        if value is None:
            continue
        text = str(value)
        carrier[str(key)] = text
        carrier[str(key).lower()] = text
    return propagate.extract(carrier)


def correlation_id_from_message(message: aio_pika.IncomingMessage) -> str:
    """Читает X-Correlation-ID из заголовков сообщения. Нет заголовка — unknown."""
    headers = message.headers or {}
    value = headers.get("X-Correlation-ID")
    if isinstance(value, bytes):
        return value.decode()
    if value:
        return str(value)
    return "unknown"


async def publish_event(
    routing_key: str,
    payload: dict,
    correlation_id: str | None = None,
) -> None:
    """
    Публикует событие в RabbitMQ.
    routing_key — например, 'order.paid'.
    payload — словарь с данными события.
    correlation_id кладётся в заголовок, чтобы consumer увидел тот же ID, что и монолит.
    """
    import json

    tracer = trace.get_tracer("order-service")
    with tracer.start_as_current_span("RabbitMQ.publish") as span:
        span.set_attribute("messaging.system", "rabbitmq")
        span.set_attribute("messaging.destination", routing_key)
        if payload.get("order_id") is not None:
            span.set_attribute("order_id", payload["order_id"])

        # traceparent уходит вместе с correlation_id: кухня продолжит этот же трейс.
        headers: dict[str, str] = {}
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        propagate.inject(headers)

        connection = await get_connection()
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                EXCHANGE_NAME,
                ExchangeType.TOPIC,
                durable=True,  # exchange переживёт перезапуск RabbitMQ
            )
            message = aio_pika.Message(
                body=json.dumps(payload).encode(),
                headers=headers,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # сообщение пишется на диск
            )
            await exchange.publish(message, routing_key=routing_key)