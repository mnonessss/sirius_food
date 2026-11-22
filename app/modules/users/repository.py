from sqlalchemy.orm import Session
from app.models import Role, User


class UserRepository:
    """
    Класс отвечает исключительно за выполнение операций ввода-вывода
    в контексте СУБД PostgreSQL с использованием SQLAlchemy ORM.
    Бизнес-правила в данном классе отсутствуют.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int):
        """Извлечение объекта пользователя по идентификатору."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str):
        """Извлечение объекта пользователя по адресу электронной почты."""
        return self.db.query(User).filter(User.email == email).first()

    def get_role_id(self, name: str) -> int | None:
        """Идентификатор роли по её имени."""
        role = self.db.query(Role).filter(Role.name == name).first()
        if role is None:
            return None
        return role.id

    def save(self, user: User) -> User:
        """Сохраняет уже собранный объект пользователя."""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save_user(self, email: str, phone: str | None):
        """
        Создание новой записи пользователя и фиксация транзакции.
        Возвращает созданный объект пользователя.
        """
        new_user = User(
            email=email,
            phone=phone,
            balance=0.0,
            is_blocked=False,
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user

    def update_user_balance(self, user, new_balance: float) -> None:
        """Изменение значения баланса пользователя с фиксацией транзакции."""
        user.balance = new_balance
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
