"""
Точка входа приложения. Выполняет инициализацию FastAPI,
подключение модулей и создание таблиц базы данных.
"""
import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.correlation import correlation_id_middleware
from app.core.logging import setup_logging
from app.core.tracing import setup_tracing

setup_logging()
setup_tracing("order-service")

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.0,
        environment="sirius-food",
    )

from app.database import SessionLocal, engine
from app.modules.users.router import router as users_router
from app.modules.menu.router import router as menu_router
from app.modules.menu.repository import MenuRepository
from app.modules.menu.service import MenuService
from app.modules.orders.router import router as orders_router
from app.modules.delivery.router import router as delivery_router
from app.modules.auth.router import router as auth_router

logger = logging.getLogger(__name__)


def warm_up_cache() -> None:
    db = SessionLocal()
    try:
        MenuService(MenuRepository(db)).warm_up_menu_cache()
        logger.info("Кеш menu:all прогрет")
    except Exception:
        logger.warning("Не удалось прогреть кеш menu:all", exc_info=True)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    warm_up_cache()
    yield


app = FastAPI(
    title="Sirius.Food API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)

app.middleware("http")(correlation_id_middleware)
# HTTP-span создаётся снаружи middleware, поэтому correlation_id попадает в трейс.
FastAPIInstrumentor.instrument_app(app, excluded_urls="metrics,health")

app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(menu_router, prefix="/menu", tags=["menu"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
app.include_router(delivery_router, prefix="/delivery", tags=["delivery"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])




# Автоматически добавляет /metrics с RED-метриками.
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health():
    """Живость процесса и доступность PostgreSQL — удобная цель для нагрузки."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "service": "sirius-food"}
