import uuid
from datetime import datetime, timedelta
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    """Создаёт короткоживущий access-токен (15 минут)."""
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Создаёт долгоживущий refresh-токен (7 дней)."""
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Декодирует и проверяет подпись токена."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])