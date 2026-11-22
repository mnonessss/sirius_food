from app.modules.delivery.repository import DeliveryRepository


class DeliveryNotFoundError(Exception):
    """Доставка или связанная сущность отсутствует."""


class DeliveryForbiddenError(Exception):
    """Назначение запрещено бизнес-правилом блокировки курьера."""


class DeliveryService:
    """
    Класс инкапсулирует бизнес-правила доставки.
    Не имеет зависимостей от инфраструктурных фреймворков.
    """

    def __init__(self, repository: DeliveryRepository, delivery_client=None):
        # Внедрение зависимости через конструктор.
        self.repository = repository
        # Клиент подменяет запись в таблицу deliveries. Проверка прав остаётся здесь.
        self.delivery_client = delivery_client

    def assign_courier(self, order_id: int, courier_id: int) -> int:
        """
        Исполнение сценария назначения курьера.
        Возвращает идентификатор созданной доставки.
        Возбуждает DeliveryNotFoundError, DeliveryForbiddenError или ValueError
        при нарушении бизнес-правил.
        """
        order = self.repository.get_order_by_id(order_id)
        if not order:
            raise DeliveryNotFoundError("Заказ не найден")

        # Бизнес-правило: назначить курьера можно только на оплаченный заказ.
        if order.status != "paid":
            raise ValueError("Курьера можно назначить только на оплаченный заказ")

        courier = self.repository.get_user_by_id(courier_id)
        if not courier:
            raise DeliveryNotFoundError("Курьер не найден")

        if not courier.role or courier.role.name != "courier":
            raise DeliveryForbiddenError(
                "Назначить можно только пользователя с ролью курьера"
            )

        if courier.is_blocked:
            raise DeliveryForbiddenError(
                "Курьер заблокирован и не может быть назначен"
            )

        # Бизнес-правило: один курьер — одна активная доставка.
        active = self.repository.get_active_by_courier(courier_id)
        if active:
            raise ValueError("У курьера уже есть активная доставка")

        if self.delivery_client is not None:
            result = self._call_client(
                lambda: self.delivery_client.assign_courier(order_id, courier_id)
            )
            return result["delivery_id"]

        return self.repository.save_delivery(order_id, courier_id)

    def list_my_deliveries(self, current_user) -> list:
        """Доставки текущего курьера; чужие в выборку не попадают."""
        return self.repository.list_by_courier(current_user.id)

    def view_order_delivery(self, order_id: int, current_user) -> dict:
        """
        Доставка заказа через gRPC.
        Администратор видит любую, курьер — только свою, студент — только своего заказа.
        """
        order = self.repository.get_order_by_id(order_id)
        if not order:
            raise DeliveryNotFoundError("Заказ не найден")

        data = self._call_client(lambda: self.delivery_client.get_delivery(order_id))
        delivery = _DeliveryView(
            data["id"],
            order_id,
            data["courier_id"],
            data["status"],
        )
        self._ensure_can_view(delivery, current_user)
        return {
            "delivery_id": delivery.id,
            "order_id": order_id,
            "courier_id": delivery.courier_id,
            "status": delivery.status,
        }

    def get_delivery(self, delivery_id: int, current_user):
        """
        Возвращает доставку, если текущий пользователь имеет к ней право.
        Курьер видит только свою, студент — только доставку своего заказа.
        """
        delivery = self.repository.get_by_id(delivery_id)
        if not delivery:
            raise DeliveryNotFoundError("Доставка не найдена")
        self._ensure_can_view(delivery, current_user)
        return delivery

    def complete_delivery(self, delivery_id: int, current_user) -> None:
        """
        Исполнение сценария завершения доставки.
        Завершить доставку может только назначенный курьер.
        """
        delivery = self.repository.get_by_id(delivery_id)
        if not delivery:
            raise DeliveryNotFoundError("Доставка не найдена")

        if delivery.courier_id != current_user.id:
            raise DeliveryForbiddenError(
                "Завершить доставку может только назначенный курьер"
            )

        if delivery.status == "completed":
            raise ValueError("Доставка уже завершена")

        if delivery.status == "cancelled":
            raise ValueError("Отменённую доставку нельзя завершить")

        order = self.repository.get_order_by_id(delivery.order_id)
        if self.delivery_client is not None:
            self._call_client(
                lambda: self.delivery_client.complete_delivery(delivery_id)
            )
            if order:
                order.status = "delivered"
                self.repository.save_order(order)
            return

        delivery.status = "completed"
        if order:
            order.status = "delivered"
        self.repository.save_completion(delivery, order)

    def _ensure_can_view(self, delivery, current_user) -> None:
        role_name = current_user.role.name if current_user.role else None
        if role_name == "admin":
            return
        if role_name == "courier" and delivery.courier_id == current_user.id:
            return

        order = self.repository.get_order_by_id(delivery.order_id)
        if role_name == "student" and order and order.user_id == current_user.id:
            return

        raise DeliveryForbiddenError("Недостаточно прав для просмотра доставки")

    def _call_client(self, action):
        if self.delivery_client is None:
            raise ConnectionError("Delivery service is unavailable")
        try:
            return action()
        except ValueError as error:
            raise DeliveryNotFoundError(str(error)) from error


class _DeliveryView:
    def __init__(self, delivery_id, order_id, courier_id, status):
        self.id = delivery_id
        self.order_id = order_id
        self.courier_id = courier_id
        self.status = status
