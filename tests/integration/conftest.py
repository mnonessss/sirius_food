import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient
import app.models  # noqa: F401  — регистрация таблиц в Base.metadata
from app.main import app
from app.database import Base, get_db


@pytest.fixture(scope="session")
def postgres():
    """Поднимает пустую PostgreSQL и создаёт таблицы по текущим моделям."""
    with PostgresContainer("postgres:15") as pg:
        engine = create_engine(pg.get_connection_url())
        Base.metadata.create_all(engine)
        engine.dispose()
        yield pg


@pytest.fixture
def db(postgres):
    """Создаёт сессию БД для одного теста."""
    engine = create_engine(postgres.get_connection_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    """FastAPI TestClient с подменённой БД."""

    # Подменяем зависимость get_db на тестовую сессию.
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()