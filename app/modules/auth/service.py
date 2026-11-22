import hashlib
from datetime import datetime

from app.core.jwt import create_access_token, create_refresh_token
from app.core.security import verify_password

from app.modules.auth.repository import AuthRepository
from app.modules.auth.exceptions import InvalidRefreshTokenError


class InvalidCredentialsError(Exception):
    """Неверный email или пароль."""
    pass


class AuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

    def login(self, email: str, password: str) -> dict:
        """Проверяет учётные данные и возвращает пару токенов."""
        user = self.repository.get_by_email(email)
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # Сохраняем refresh-токен в БД для возможности отзыва.
        self.repository.save_refresh_token(user.id, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    
    def refresh(self, refresh_token: str) -> dict:
        """
        Меняет refresh-токен на новую пару.
        Повторное использование уже отозванного токена сбрасывает всю сессию.
        """
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        record = self.repository.get_refresh_token(token_hash)
        if record is None:
            raise InvalidRefreshTokenError()

        if record.is_revoked:
            self.repository.revoke_all_for_user(record.user_id)
            raise InvalidRefreshTokenError()

        if record.expires_at < datetime.utcnow():
            raise InvalidRefreshTokenError()

        user = self.repository.get_user_by_id(record.user_id)
        if user is None:
            raise InvalidRefreshTokenError()

        self.repository.revoke_refresh_token(token_hash)
        access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)
        self.repository.save_refresh_token(user.id, new_refresh_token)
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }