import logging
import time

from sqlalchemy import func

from app.core.celery_app import celery_app
from app.core.redis import redis_client
from app.database import SessionLocal
from app.models import Order

logger = logging.getLogger(__name__)


class EmailTask(celery_app.Task):
    """Письмо с ретраями. После последней неудачи копия уходит в очередь dlq."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        order_id = args[0] if args else None
        logger.error(
            "Превышено max_retries (%s) для send_order_email, заказ %s отправлен в DLQ",
            self.max_retries,
            order_id,
        )
        self.apply_async(args=args, kwargs=kwargs, queue="dlq")


@celery_app.task(bind=True)
def generate_order_pdf(self, order_id: int) -> str:
    """Генерация PDF с проверкой идемпотентности."""
    # Ключ идемпотентности
    key = f"pdf_generated:{order_id}"
    
    # Если ключ уже есть — PDF уже сгенерирован, пропускаем
    if redis_client.exists(key):
        return f"PDF already generated for order {order_id}"
    
    time.sleep(2)
    
    # Сохраняем флаг на 1 час
    redis_client.setex(key, 3600, "1")
    
    return f"PDF generated for order {order_id}"


@celery_app.task(base=EmailTask, bind=True)
def send_order_email(self, order_id: int, email: str) -> str:
    """Отправка email с ретраями."""
    routing_key = (self.request.delivery_info or {}).get("routing_key")
    if routing_key == "dlq":
        return f"Order {order_id} is already in DLQ"
    time.sleep(1)
    # Имитация падения для каждого 5-го заказа
    if order_id % 5 == 0:
        raise Exception("Email service unavailable")
    return f"Email sent to {email} for order {order_id}"



@celery_app.task
def send_order_sms(order_id: int, phone: str) -> str:
    """Отправка SMS о создании заказа."""
    time.sleep(1)
    return f"SMS sent to {phone} for order {order_id}"


@celery_app.task
def refresh_daily_order_stats() -> str:
    """Считает заказы за текущие сутки и записывает число в Redis."""
    db = SessionLocal()
    try:
        day = db.query(func.current_date()).scalar()
        count = (
            db.query(func.count(Order.id))
            .filter(func.date(Order.created_at) == day)
            .scalar()
        )
    finally:
        db.close()
    key = f"stats:orders:{day.isoformat()}"
    redis_client.set(key, int(count or 0))
    return f"{key}={count}"