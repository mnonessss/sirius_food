class OrderNotFoundError(Exception):
    """Заказ не найден."""
    pass


class AccessDeniedError(Exception):
    """Пользователь не имеет прав на этот объект."""
    pass