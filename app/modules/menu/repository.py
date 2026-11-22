import json
from redis.exceptions import LockError
from sqlalchemy.orm import Session
from app.models import Category, MenuItem
from app.core.redis import redis_client

MENU_CACHE_KEY = "menu:all"
MENU_CACHE_TTL = 300
CATEGORY_CACHE_TTL = 600
# Замок снимается сам через LOCK_TIMEOUT, даже если держатель упал.
LOCK_TIMEOUT = 10
# Сколько остальные запросы ждут замок, прежде чем пойти в БД сами.
LOCK_WAIT = 5


class MenuRepository:
    """
    Класс отвечает исключительно за выполнение операций ввода-вывода
    в контексте СУБД PostgreSQL с использованием SQLAlchemy ORM.
    Бизнес-правила в данном классе отсутствуют.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, item_id: int):
        """Извлечение объекта блюда из меню по идентификатору."""
        return self.db.query(MenuItem).filter(MenuItem.id == item_id).first()

    def get_by_name(self, name: str):
        """Извлечение объекта блюда из меню по названию."""
        return self.db.query(MenuItem).filter(MenuItem.name == name).first()

    def list_available(self):
        """Извлечение доступных для заказа блюд."""
        return (
            self.db.query(MenuItem)
            .filter(MenuItem.is_available.is_(True))
            .order_by(MenuItem.id)
            .all()
        )

    def save_item(self, name: str, price: float, category_id: int | None = None) -> int:
        """
        Создание новой записи блюда и фиксация транзакции.
        Возвращает идентификатор созданного блюда.
        """
        new_item = MenuItem(
            name=name,
            price=price,
            is_available=True,
            category_id=category_id,
        )
        self.db.add(new_item)
        self.db.commit()
        self.db.refresh(new_item)
        return new_item.id

    def update_item(self, item) -> None:
        """Фиксация изменений блюда."""
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
    

    def get_all(self) -> list[dict]:
        """
        Возвращает доступные блюда меню.
        Сначала проверяет кеш Redis (Cache-Aside).
        При промахе (miss) идёт в БД и кеширует результат.
        """
        cached_data = redis_client.get(MENU_CACHE_KEY)
        if cached_data:
            return json.loads(cached_data)
        return self.warm_menu_cache()

    def warm_menu_cache(self) -> list[dict]:
        """Читает доступные блюда из БД и записывает их в menu:all."""
        items = [
            {
                "id": item.id,
                "name": item.name,
                "price": item.price,
            }
            for item in self.list_available()
        ]
        redis_client.setex(MENU_CACHE_KEY, MENU_CACHE_TTL, json.dumps(items, ensure_ascii=False))
        return items

    def invalidate_cache(self) -> None:
        """Сбрасывает кеш меню."""
        redis_client.delete(MENU_CACHE_KEY)

    def category_exists(self, category_id: int) -> bool:
        return self.db.query(Category.id).filter(Category.id == category_id).first() is not None

    def get_category(self, category_id: int) -> dict | None:
        """
        Возвращает категорию с доступными блюдами (Cache-Aside).
        Ключ menu:category:{id}, TTL 10 минут.
        При промахе в БД идёт только держатель замка, остальные ждут
        и берут результат из обновлённого кеша.
        """
        cache_key = f"menu:category:{category_id}"

        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        lock = redis_client.lock(
            f"lock:{cache_key}",
            timeout=LOCK_TIMEOUT,
            blocking_timeout=LOCK_WAIT,
        )
        acquired = lock.acquire()
        try:
            # Пока ждали замок, кеш мог заполнить другой запрос.
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            return self._load_category_to_cache(category_id, cache_key)
        finally:
            if acquired:
                try:
                    lock.release()
                except LockError:
                    pass

    def _load_category_to_cache(self, category_id: int, cache_key: str) -> dict | None:
        category = self.db.query(Category).filter(Category.id == category_id).first()
        if category is None:
            return None

        data = {
            "id": category.id,
            "name": category.name,
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "price": item.price,
                }
                for item in sorted(category.items, key=lambda i: i.id)
                if item.is_available
            ],
        }
        redis_client.setex(cache_key, CATEGORY_CACHE_TTL, json.dumps(data, ensure_ascii=False))
        return data

    def invalidate_category_cache(self, category_id: int | None) -> None:
        if category_id is not None:
            redis_client.delete(f"menu:category:{category_id}")

