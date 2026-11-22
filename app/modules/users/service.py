from app.modules.users.repository import UserRepository
from app.models import User
from app.modules.users.exceptions import EmailAlreadyExistsError

from app.core.security import hash_password


class UserNotFoundError(Exception):
    """Пользователь с указанным идентификатором отсутствует."""


class UserForbiddenError(Exception):
    """Операция запрещена бизнес-правилом блокировки пользователя."""


class UserService:
    """
    Класс инкапсулирует бизнес-правила работы с пользователями.
    Не имеет зависимостей от инфраструктурных фреймворков.
    """

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def register(self, email: str, password: str, phone: str | None = None) -> User:
        existing = self.repository.get_by_email(email)
        if existing:
            raise EmailAlreadyExistsError()

        role_id = self.repository.get_role_id("student")
        if role_id is None:
            raise ValueError("Роль student не найдена")

        user = User(
            email=email,
            phone=phone,
            balance=0.0,
            is_blocked=False,
            password_hash=hash_password(password),
            role_id=role_id,
        )
        self.repository.save(user)
        return user

    def top_up_balance(self, user_id: int, amount: float) -> float:
        """Исполнение сценария пополнения баланса."""
        user = self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError("Пользователь не найден")

        if user.is_blocked:
            raise UserForbiddenError(
                "Пользователь заблокирован. Пополнение невозможно"
            )

        # Бизнес-правило: максимальная сумма одного пополнения.
        if amount > 50000:
            raise ValueError("Максимальная сумма пополнения — 50000 рублей")

        new_balance = user.balance + amount
        self.repository.update_user_balance(user, new_balance)
        return new_balance
