from fastapi import HTTPException, Request
from redis import Redis

from app.core.config import settings

redis_client = Redis.from_url(settings.REDIS_URL)


def rate_limit(max_requests: int = 5, window: int = 60):
    """
    Dependency для ограничения частоты запросов.
    Возбуждает HTTPException 429 при превышении лимита.
    """
    def checker(request: Request):
        ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{ip}:{request.url.path}"
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, window)
        if current > max_requests:
            raise HTTPException(429, "Too many requests")
    return checker