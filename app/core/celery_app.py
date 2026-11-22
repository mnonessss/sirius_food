from celery import Celery
from kombu import Queue, Exchange
from app.core.config import settings

# Создаём приложение Celery.
# Брокер (Redis) — сюда FastAPI ставит задачи.
# Backend (Redis) — сюда сохраняются результаты выполнения.
celery_app = Celery(
    "sirius_food",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.orders"],
)

# Настройки сериализации: JSON вместо pickle (безопаснее).
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Без этого воркер не шлёт события, и Flower не видит задачи в реальном времени.
    worker_send_task_events=True,
    task_send_sent_event=True,
)


celery_app.conf.task_queues = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("dlq", Exchange("dlq"), routing_key="dlq"),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

celery_app.conf.beat_schedule = {
    "refresh-daily-order-stats": {
        "task": "app.tasks.orders.refresh_daily_order_stats",
        "schedule": 60.0,
    },
}