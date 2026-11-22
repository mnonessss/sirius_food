import uuid

from opentelemetry import trace

from app.models import User, Order
from app.modules.orders.repository import OrderRepository
from app.modules.orders.exceptions import AccessDeniedError, OrderNotFoundError
from app.tasks.orders import generate_order_pdf, send_order_email, send_order_sms
from app.core.rabbitmq import publish_event

tracer = trace.get_tracer("order-service")


class OrderService:
    """
    Класс инкапсулирует бизнес-правила обработки заказов.
    Не имеет зависимостей от инфраструктурных фреймворков.
    """

    def __init__(self, repository: OrderRepository):
        # Внедрение зависимости через конструктор.
        self.repository = repository

    def create_order(self, user_id: int, item_id: int, quantity: int) -> int:
        """
        Исполнение сценария оформления заказа.
        Возвращает идентификатор созданного заказа.
        Возбуждает ValueError при нарушении бизнес-правил.
        """
        with tracer.start_as_current_span("OrderService.create") as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("item_id", item_id)
            user = self.repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("Пользователь не найден")

            item = self.repository.get_menu_item_by_id(item_id)
            if not item:
                raise ValueError("Указанное блюдо не найдено в меню")

            if not item.is_available:
                raise ValueError("Блюдо временно недоступно")

            total_cost = item.price * quantity
            if user.balance < total_cost:
                raise ValueError("Недостаточно средств на балансе студента")

            # Изменение состояния доменных данных.
            user.balance -= total_cost
            self.repository.update_user_balance(user, user.balance)

            # Делегирование операции сохранения инфраструктурному слою.
            with tracer.start_as_current_span("DB.insert"):
                order_id = self.repository.save_order(user_id, item_id, quantity)
            span.set_attribute("order_id", order_id)
            generate_order_pdf.delay(order_id)
            send_order_email.delay(order_id, user.email)
            send_order_sms.delay(order_id, user.phone)
            return order_id
    
    def cancel_order(self, order_id: int, current_user: User) -> Order:
        """
        Отменяет заказ. Проверяет, что заказ принадлежит текущему пользователю.
        Возбуждает OrderNotFoundError или AccessDeniedError.
        """
        order = self.repository.get_order(order_id)
        if order is None:
            raise OrderNotFoundError()
        if order.user_id != current_user.id:
            raise AccessDeniedError()
        self.repository.cancel_order(order)
        return order

    async def pay_order(
        self,
        order_id: int,
        current_user: User,
        correlation_id: str | None = None,
    ) -> Order:
        """
        Оплата заказа. После успешной оплаты публикуем событие OrderPaid.
        """
        with tracer.start_as_current_span("OrderService.pay") as span:
            span.set_attribute("order_id", order_id)
            if correlation_id:
                span.set_attribute("correlation_id", correlation_id)
            order = self.repository.get_order(order_id)
            if order is None:
                raise OrderNotFoundError()
            if order.user_id != current_user.id:
                raise AccessDeniedError()
            if order.status == "cancelled":
                raise ValueError("Отменённый заказ нельзя оплатить")
            if order.status != "processing":
                raise ValueError("Заказ уже оплачен")

            amount = order.item.price * order.quantity
            order.status = "paid"
            with tracer.start_as_current_span("DB.update"):
                self.repository.save(order)

            await publish_event(
                routing_key="order.paid",
                correlation_id=correlation_id,
                payload={
                    "event_id": str(uuid.uuid4()),
                    "order_id": order.id,
                    "customer_id": order.user_id,
                    "amount": amount,
                },
            )
            return order

    def get_kitchen_orders(self) -> list[dict]:
        """Заказы, которые кухня ещё должна приготовить."""
        orders = self.repository.list_kitchen_orders()
        return [
            {
                "order_id": order.id,
                "user_id": order.user_id,
                "item_id": order.item_id,
                "quantity": order.quantity,
                "status": order.status,
            }
            for order in orders
        ]