"""
Pydantic-схемы для валидации входных и выходных данных.
"""
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    phone: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    balance: float

    class Config:
        from_attributes = True


class MenuItemCreate(BaseModel):
    name: str
    price: float
    category_id: int | None = None


class MenuItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    is_available: bool | None = None
    category_id: int | None = None


class OrderCreate(BaseModel):
    item_id: int
    quantity: int


class DeliveryAssign(BaseModel):
    order_id: int
    courier_id: int