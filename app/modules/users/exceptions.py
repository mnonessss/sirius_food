class EmailAlreadyExistsError(Exception):
    """Email уже существует."""
    pass


class UserNotFoundError(Exception):
    """Пользователь не найден."""
    pass

class UserForbiddenError(Exception):
    """Пользователь не имеет прав на этот объект."""
    pass

class UserInvalidPasswordError(Exception):
    """Неверный пароль."""
    pass