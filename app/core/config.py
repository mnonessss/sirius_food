from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = []
    RABBITMQ_URL: str
    SENTRY_DSN: str = ""
    # Jaeger в docker-compose принимает OTLP/HTTP на порту 4318.
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://127.0.0.1:4318" 


settings = Settings()