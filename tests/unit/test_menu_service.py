import unittest

from app.modules.menu.service import MenuService


class FakeMenuItem:
    def __init__(self, item_id, name, price):
        self.id = item_id
        self.name = name
        self.price = price


class FakeMenuRepository:
    def __init__(self, items=None):
        self.items = list(items or [])

    def get_by_name(self, name):
        return next((item for item in self.items if item.name == name), None)

    def save_item(self, name, price):
        raise AssertionError("сохранение не должно вызываться при дубликате названия")


class MenuServiceTest(unittest.TestCase):
    def test_create_item_rejects_duplicate_name(self):
        repository = FakeMenuRepository([FakeMenuItem(1, "Борщ", 150)])
        service = MenuService(repository)

        with self.assertRaises(ValueError) as caught:
            service.create_item("Борщ", 180)

        self.assertEqual(
            str(caught.exception),
            "Блюдо с таким названием уже существует",
        )


if __name__ == "__main__":
    unittest.main()
