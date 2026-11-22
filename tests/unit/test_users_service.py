import unittest

from app.modules.users.exceptions import EmailAlreadyExistsError
from app.modules.users.service import UserService


class FakeUser:
    def __init__(self, user_id, email, balance=0.0, is_blocked=False, phone=None):
        self.id = user_id
        self.email = email
        self.balance = balance
        self.is_blocked = is_blocked
        self.phone = phone


class FakeUserRepository:
    def __init__(self, users=None):
        self.users = list(users or [])

    def get_by_email(self, email):
        return next((user for user in self.users if user.email == email), None)

    def get_role_id(self, name):
        raise AssertionError("роль не должна запрашиваться при дубликате email")

    def save(self, user):
        raise AssertionError("сохранение не должно вызываться при дубликате email")


class UserServiceTest(unittest.TestCase):
    def test_register_rejects_duplicate_email(self):
        repository = FakeUserRepository([FakeUser(1, "student@sirius.ru")])
        service = UserService(repository)

        with self.assertRaises(EmailAlreadyExistsError):
            service.register("student@sirius.ru", "secret")


if __name__ == "__main__":
    unittest.main()
