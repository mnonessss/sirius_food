"""
Модуль инициализации подключения к СУБД PostgreSQL.
"""
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    user = quote_plus(os.getenv("POSTGRES_USER", "postgres"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5440")
    db_name = os.getenv("POSTGRES_DB", "sirius_food_db")
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

# pool_pre_ping заново открывает соединение, если контейнер Postgres пересоздали.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Генератор сессии базы данных для использования в Depends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()