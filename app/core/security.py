from passlib.context import CryptContext
from passlib.exc import UnknownHashError

# Контекст для хеширования. bcrypt — современный алгоритм с солью.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хеш пароля."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Проверяет соответствие пароля хешу."""
    try:
        return pwd_context.verify(plain, hashed)
    except (ValueError, UnknownHashError):
        return False