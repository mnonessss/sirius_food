import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.modules.orders.exceptions import AccessDeniedError, OrderNotFoundError
from app.modules.orders.service import OrderService


class FakeUser:
    def __init__(self, user_id, balance=500, email="student@sirius.ru", phone="+70000000000"):
        self.id = user_id
        self.balance = balance
        self.email = email
        self.phone = phone


class FakeItem:
    def __init__(self, item_id, price, is_available=True):
        self.id = item_id
        self.price = price
        self.is_available = is_available


class FakeOrder:
    def __init__(self, order_id, user_id, status="processing", item=None, quantity=2):
        self.id = order_id
        self.user_id = user_id
        self.item_id = 3
        self.status = status
        self.item = item or FakeItem(3, 40)
        self.quantity = quantity


class FakeOrderRepository:
    def __init__(self, user=None, item=None, order=None, kitchen=None):
        self.user = user
        self.item = item
        self.order = order
        self.kitchen = list(kitchen or [])
        self.saved_balance = None
        self.saved_order = None
        self.cancelled = None

    def get_user_by_id(self, user_id):
        if self.user and self.user.id == user_id:
            return self.user
        return None

    def get_menu_item_by_id(self, item_id):
        if self.item and self.item.id == item_id:
            return self.item
        return None

    def update_user_balance(self, user, balance):
        self.saved_balance = balance

    def save_order(self, user_id, item_id, quantity):
        self.saved_order = (user_id, item_id, quantity)
        return 72

    def get_order(self, order_id):
        if self.order and self.order.id == order_id:
            return self.order
        return None

    def cancel_order(self, order):
        self.cancelled = order

    def save(self, order):
        self.saved_order = order

    def list_kitchen_orders(self):
        return self.kitchen


class OrderServiceTest(unittest.TestCase):
    def test_create_order_rejects_unknown_user(self):
        service = OrderService(FakeOrderRepository(item=FakeItem(1, 100)))

        with self.assertRaises(ValueError) as caught:
            service.create_order(user_id=9, item_id=1, quantity=1)

        self.assertEqual(str(caught.exception), "Пользователь не найден")

    def test_create_order_rejects_unavailable_dish(self):
        repository = FakeOrderRepository(
            user=FakeUser(9, balance=500),
            item=FakeItem(1, 100, is_available=False),
        )
        service = OrderService(repository)

        with self.assertRaises(ValueError) as caught:
            service.create_order(user_id=9, item_id=1, quantity=1)

        self.assertEqual(str(caught.exception), "Блюдо временно недоступно")
        self.assertIsNone(repository.saved_order)

    def test_create_order_rejects_insufficient_balance(self):
        repository = FakeOrderRepository(
            user=FakeUser(9, balance=50),
            item=FakeItem(1, 100),
        )
        service = OrderService(repository)

        with self.assertRaises(ValueError) as caught:
            service.create_order(user_id=9, item_id=1, quantity=1)

        self.assertEqual(str(caught.exception), "Недостаточно средств на балансе студента")
        self.assertEqual(repository.user.balance, 50)

    @patch("app.modules.orders.service.send_order_sms")
    @patch("app.modules.orders.service.send_order_email")
    @patch("app.modules.orders.service.generate_order_pdf")
    def test_create_order_charges_balance_and_returns_id(self, pdf, email, sms):
        user = FakeUser(9, balance=500)
        repository = FakeOrderRepository(user=user, item=FakeItem(1, 120))
        service = OrderService(repository)

        order_id = service.create_order(user_id=9, item_id=1, quantity=2)

        self.assertEqual(order_id, 72)
        self.assertEqual(user.balance, 260)
        self.assertEqual(repository.saved_balance, 260)
        self.assertEqual(repository.saved_order, (9, 1, 2))
        pdf.delay.assert_called_once_with(72)
        email.delay.assert_called_once_with(72, "student@sirius.ru")
        sms.delay.assert_called_once_with(72, "+70000000000")

    def test_cancel_order_rejects_missing_order(self):
        service = OrderService(FakeOrderRepository())

        with self.assertRaises(OrderNotFoundError):
            service.cancel_order(15, FakeUser(9))

    def test_cancel_order_rejects_foreign_user(self):
        repository = FakeOrderRepository(order=FakeOrder(15, user_id=9))
        service = OrderService(repository)

        with self.assertRaises(AccessDeniedError):
            service.cancel_order(15, FakeUser(4))

        self.assertIsNone(repository.cancelled)

    def test_pay_order_rejects_cancelled_order(self):
        order = FakeOrder(15, user_id=9, status="cancelled")
        service = OrderService(FakeOrderRepository(order=order))

        with self.assertRaises(ValueError) as caught:
            asyncio.run(service.pay_order(15, FakeUser(9), "demo-42"))

        self.assertEqual(str(caught.exception), "Отменённый заказ нельзя оплатить")
        self.assertEqual(order.status, "cancelled")

    def test_pay_order_marks_paid_and_publishes_event(self):
        order = FakeOrder(15, user_id=9, quantity=2)
        service = OrderService(FakeOrderRepository(order=order))

        with patch("app.modules.orders.service.publish_event", new_callable=AsyncMock) as publish:
            result = asyncio.run(service.pay_order(15, FakeUser(9), "demo-42"))

        self.assertIs(result, order)
        self.assertEqual(order.status, "paid")
        publish.assert_awaited_once()
        kwargs = publish.await_args.kwargs
        self.assertEqual(kwargs["routing_key"], "order.paid")
        self.assertEqual(kwargs["correlation_id"], "demo-42")
        self.assertEqual(kwargs["payload"]["order_id"], 15)
        self.assertEqual(kwargs["payload"]["customer_id"], 9)
        self.assertEqual(kwargs["payload"]["amount"], 80)

    def test_get_kitchen_orders_returns_plain_rows(self):
        order = FakeOrder(15, user_id=9, status="paid", quantity=2)
        service = OrderService(FakeOrderRepository(kitchen=[order]))

        self.assertEqual(
            service.get_kitchen_orders(),
            [
                {
                    "order_id": 15,
                    "user_id": 9,
                    "item_id": 3,
                    "quantity": 2,
                    "status": "paid",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
