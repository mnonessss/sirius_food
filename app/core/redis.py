import redis
from app.core.config import settings

# Клиент Redis. decode_responses=True означает, что мы получаем строки,
# а не байты — удобно для JSON.
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def check_redis_connection() -> bool:
    """Проверка соединения с Redis."""
    try:
        return redis_client.ping()
    except redis.ConnectionError:
        return False