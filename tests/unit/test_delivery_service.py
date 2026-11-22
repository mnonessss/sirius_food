import unittest

from app.modules.delivery.service import DeliveryForbiddenError, DeliveryService


class FakeOrder:
    def __init__(self, order_id, status):
        self.id = order_id
        self.status = status


class FakeDeliveryRepository:
    def __init__(self, orders=None, deliveries=None):
        self.orders = list(orders or [])
        self.deliveries = list(deliveries or [])

    def get_order_by_id(self, order_id):
        return next((order for order in self.orders if order.id == order_id), None)

    def get_by_id(self, delivery_id):
        return next((item for item in self.deliveries if item.id == delivery_id), None)

    def save_delivery(self, order_id, courier_id):
        raise AssertionError("доставка не должна создаваться для неоплаченного заказа")


class DeliveryServiceTest(unittest.TestCase):
    def test_assign_courier_requires_paid_order(self):
        repository = FakeDeliveryRepository([FakeOrder(1, "processing")])
        service = DeliveryService(repository)

        with self.assertRaises(ValueError) as caught:
            service.assign_courier(1, 7)

        self.assertEqual(
            str(caught.exception),
            "Курьера можно назначить только на оплаченный заказ",
        )

    def test_foreign_courier_cannot_complete_delivery(self):
        delivery = FakeDelivery(delivery_id=5, courier_id=10)
        client = FakeDeliveryClient()
        service = DeliveryService(
            FakeDeliveryRepository(deliveries=[delivery]),
            client,
        )

        with self.assertRaises(DeliveryForbiddenError):
            service.complete_delivery(5, FakeUser(200, "courier"))

        self.assertFalse(client.completed)

    def test_student_cannot_view_foreign_order_delivery(self):
        order = FakeOrder(1, "paid")
        order.user_id = 100
        client = FakeDeliveryClient()
        client.delivery = {
            "id": 5,
            "courier_id": 10,
            "status": "in_progress",
        }
        service = DeliveryService(FakeDeliveryRepository([order]), client)

        with self.assertRaises(DeliveryForbiddenError):
            service.view_order_delivery(1, FakeUser(200, "student"))


class FakeRole:
    def __init__(self, name):
        self.name = name


class FakeUser:
    def __init__(self, user_id, role_name):
        self.id = user_id
        self.role = FakeRole(role_name)


class FakeDelivery:
    def __init__(self, delivery_id, courier_id):
        self.id = delivery_id
        self.order_id = 1
        self.courier_id = courier_id
        self.status = "in_progress"


class FakeDeliveryClient:
    def __init__(self):
        self.completed = False

    def complete_delivery(self, delivery_id):
        self.completed = True
        return {"status": "completed"}

    def get_delivery(self, order_id):
        return self.delivery


if __name__ == "__main__":
    unittest.main()
