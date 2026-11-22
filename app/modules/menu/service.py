from app.modules.menu.repository import MenuRepository


class MenuItemNotFoundError(Exception):
    """Блюдо с указанным идентификатором отсутствует в меню."""


class CategoryNotFoundError(Exception):
    """Категория с указанным идентификатором отсутствует."""


class MenuService:
    """
    Класс инкапсулирует бизнес-правила управления меню.
    Не имеет зависимостей от инфраструктурных фреймворков.
    """

    def __init__(self, repository: MenuRepository):
        # Внедрение зависимости через конструктор.
        self.repository = repository

    def list_items(self) -> list[dict]:
        """Исполнение сценария просмотра меню: только доступные блюда."""
        return self.repository.get_all()

    def get_item(self, item_id: int) -> dict:
        """Одно доступное блюдо для витрины. Нет блюда — MenuItemNotFoundError."""
        item = self.repository.get_by_id(item_id)
        if item is None or not item.is_available:
            raise MenuItemNotFoundError("Блюдо не найдено")
        return {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "category": item.category.name if item.category else None,
            "is_available": item.is_available,
        }

    def warm_up_menu_cache(self) -> None:
        """Заполняет кеш меню заранее, чтобы первый запрос не шёл в БД."""
        self.repository.warm_menu_cache()

    def create_item(self, name: str, price: float, category_id: int | None = None) -> int:
        """
        Исполнение сценария добавления блюда.
        Возвращает идентификатор созданного блюда.
        Возбуждает ValueError при нарушении бизнес-правил.
        """
        existing = self.repository.get_by_name(name)
        if existing:
            raise ValueError("Блюдо с таким названием уже существует")
        self._ensure_category_exists(category_id)

        item_id = self.repository.save_item(name, price, category_id)
        self.repository.invalidate_cache()
        self.repository.invalidate_category_cache(category_id)
        return item_id

    def update_item(
        self,
        item_id: int,
        name: str | None,
        price: float | None,
        is_available: bool | None,
        category_id: int | None = None,
    ) -> int:
        """
        Исполнение сценария изменения блюда.
        Возвращает идентификатор обновлённого блюда.
        Возбуждает MenuItemNotFoundError, если блюдо отсутствует.
        """
        item = self.repository.get_by_id(item_id)
        if not item:
            raise MenuItemNotFoundError("Блюдо не найдено")

        old_category_id = item.category_id
        if category_id is not None:
            self._ensure_category_exists(category_id)
            item.category_id = category_id
        if name is not None:
            item.name = name
        if price is not None:
            item.price = price
        if is_available is not None:
            item.is_available = is_available

        self.repository.update_item(item)
        self.repository.invalidate_cache()
        self.repository.invalidate_category_cache(old_category_id)
        self.repository.invalidate_category_cache(item.category_id)
        return item.id

    def get_category(self, category_id: int) -> dict:
        """
        Исполнение сценария просмотра категории с её доступными блюдами.
        Возбуждает CategoryNotFoundError, если категория отсутствует.
        """
        category = self.repository.get_category(category_id)
        if category is None:
            raise CategoryNotFoundError("Категория не найдена")
        return category

    def _ensure_category_exists(self, category_id: int | None) -> None:
        if category_id is not None and not self.repository.category_exists(category_id):
            raise CategoryNotFoundError("Категория не найдена")
