from sqlalchemy.orm import Session
from app.models import Delivery, Order, User


class DeliveryRepository:
    """
    Класс отвечает исключительно за выполнение операций ввода-вывода
    в контексте СУБД PostgreSQL с использованием SQLAlchemy ORM.
    Бизнес-правила в данном классе отсутствуют.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_order_by_id(self, order_id: int):
        """Извлечение объекта заказа по идентификатору."""
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_user_by_id(self, user_id: int):
        """Извлечение объекта пользователя по идентификатору."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_id(self, delivery_id: int):
        """Извлечение объекта доставки по идентификатору."""
        return self.db.query(Delivery).filter(Delivery.id == delivery_id).first()

    def list_by_courier(self, courier_id: int):
        """Все доставки, назначенные курьеру."""
        return self.db.query(Delivery).filter(
            Delivery.courier_id == courier_id
        ).order_by(Delivery.id).all()

    def get_active_by_courier(self, courier_id: int):
        """Извлечение активной доставки курьера."""
        return self.db.query(Delivery).filter(
            Delivery.courier_id == courier_id,
            Delivery.status == "in_progress",
        ).first()

    def save_delivery(self, order_id: int, courier_id: int) -> int:
        """
        Создание новой записи доставки и фиксация транзакции.
        Возвращает идентификатор созданной доставки.
        """
        new_delivery = Delivery(
            order_id=order_id,
            courier_id=courier_id,
            status="in_progress",
        )
        self.db.add(new_delivery)
        self.db.commit()
        self.db.refresh(new_delivery)
        return new_delivery.id

    def save_completion(self, delivery, order) -> None:
        """Фиксация завершения доставки и связанного статуса заказа."""
        self.db.add(delivery)
        if order is not None:
            self.db.add(order)
        self.db.commit()

    def save_order(self, order) -> None:
        """Фиксация статуса заказа. Строку доставки пишет gRPC-сервис."""
        self.db.add(order)
        self.db.commit()
