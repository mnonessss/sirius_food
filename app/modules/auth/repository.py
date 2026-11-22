import hashlib
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from app.models import RefreshToken, User


class AuthRepository:
    """Операции входа: поиск пользователя и сохранение refresh-токена."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def save_refresh_token(self, user_id: int, token: str) -> None:
        """Сохраняет хеш refresh-токена, а не сам токен."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(days=7),
            is_revoked=False,
        )
        self.db.add(record)
        self.db.commit()
    
    def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        return self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    
    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def revoke_refresh_token(self, token_hash: str) -> None:
        """Помечает один refresh-токен отозванным."""
        self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash
        ).update({RefreshToken.is_revoked: True})
        self.db.commit()

    def revoke_all_for_user(self, user_id: int) -> None:
        """Сбрасывает все refresh-токены пользователя."""
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).update({RefreshToken.is_revoked: True})
        self.db.commit()