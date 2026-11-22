"""
Скрипт настройки DLQ. Запускается один раз перед стартом consumer'ов.
"""
import asyncio
import aio_pika
from aio_pika import ExchangeType
from app.core.config import settings


async def setup() -> None:
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()

    # Создаём DLX exchange.
    dlx = await channel.declare_exchange(
        "dlx_exchange", ExchangeType.DIRECT, durable=True
    )

    # Создаём очередь DLQ.
    dlq = await channel.declare_queue("kitchen_dlq", durable=True)
    await dlq.bind(dlx, routing_key="kitchen.dlq")

    print("DLQ настроена.")
    await connection.close()


if __name__ == "__main__":
    asyncio.run(setup())