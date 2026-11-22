from unittest.mock import patch

from app.core.jwt import create_access_token
from app.models import User, MenuItem, Order


@patch("app.modules.orders.service.send_order_sms")
@patch("app.modules.orders.service.send_order_email")
@patch("app.modules.orders.service.generate_order_pdf")
def test_create_order_saves_to_db(pdf, email, sms, client, db):
    """Проверяет, что POST /orders/create сохраняет заказ в БД."""
    user = User(email="test@example.com", balance=1000.0)
    item = MenuItem(name="Сырники", price=150.0, is_available=True)
    db.add_all([user, item])
    db.commit()

    token = create_access_token(user.id)
    response = client.post(
        "/orders/create",
        json={"item_id": item.id, "quantity": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    order_id = response.json()["order_id"]

    order = db.query(Order).filter_by(id=order_id).first()
    assert order is not None
    assert order.user_id == user.id
    assert order.quantity == 2
    assert order.status == "processing"
    db.refresh(user)
    assert user.balance == 700.0
    pdf.delay.assert_called_once_with(order_id)
    email.delay.assert_called_once_with(order_id, user.email)
    sms.delay.assert_called_once_with(order_id, user.phone)