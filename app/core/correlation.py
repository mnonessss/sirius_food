"""
Middleware для correlation_id.
Генерирует ID, если клиент не передал его, и кладёт в request.state.
"""
import uuid

import sentry_sdk
from fastapi import Request
from opentelemetry import trace


async def correlation_id_middleware(request: Request, call_next):
    # Берём ID из заголовка или генерируем новый.
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

    # Кладём в request.state, чтобы был доступен в эндпоинтах.
    request.state.correlation_id = correlation_id
    # Тот же ID попадёт в событие Sentry, если запрос закончится ошибкой.
    sentry_sdk.set_tag("correlation_id", correlation_id)
    # И в текущий span, чтобы трейс в Jaeger находился по correlation_id.
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("correlation_id", correlation_id)

    # Передаём запрос дальше в эндпоинт.
    response = await call_next(request)
    
    # Возвращаем ID клиенту.
    response.headers["X-Correlation-ID"] = correlation_id
    return response