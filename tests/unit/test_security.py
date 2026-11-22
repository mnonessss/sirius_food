import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.main import app


class FakeRole:
    def __init__(self, name):
        self.name = name


class FakeUser:
    def __init__(self, user_id, role_name):
        self.id = user_id
        self.role = FakeRole(role_name)
        self.is_blocked = False


class FakeOrder:
    def __init__(self, order_id, user_id):
        self.id = order_id
        self.user_id = user_id
        self.status = "processing"


class FakeOrderRepository:
    def __init__(self, db):
        self.orders = {1: FakeOrder(1, user_id=100)}

    def get_order(self, order_id):
        return self.orders.get(order_id)

    def cancel_order(self, order):
        raise AssertionError("чужой заказ не должен отменяться")


class FakeAuthRepository:
    def __init__(self, db):
        pass

    def get_by_email(self, email):
        return None


class FakeRedis:
    def __init__(self):
        self.counters = {}

    def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key, seconds):
        return True


class SecurityTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def login_as(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    def test_create_order_without_token_returns_401(self):
        response = self.client.post(
            "/orders/create",
            json={"item_id": 1, "quantity": 1},
        )

        self.assertEqual(response.status_code, 401)

    def test_student_cannot_open_kitchen_returns_403(self):
        self.login_as(FakeUser(1, "student"))

        response = self.client.get("/orders/kitchen/orders")

        self.assertEqual(response.status_code, 403)

    def test_cancel_foreign_order_returns_403(self):
        self.login_as(FakeUser(200, "student"))

        with patch("app.modules.orders.router.OrderRepository", FakeOrderRepository):
            response = self.client.post("/orders/1/cancel")

        self.assertEqual(response.status_code, 403)

    def test_login_bruteforce_returns_429(self):
        payload = {"email": "student@sirius.ru", "password": "wrong"}

        with patch("app.core.rate_limit.redis_client", FakeRedis()), \
                patch("app.modules.auth.router.AuthRepository", FakeAuthRepository):
            statuses = [
                self.client.post("/auth/login", json=payload).status_code
                for _ in range(6)
            ]

        self.assertEqual(statuses[:5], [401] * 5)
        self.assertEqual(statuses[5], 429)


if __name__ == "__main__":
    unittest.main()
