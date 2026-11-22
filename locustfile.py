from locust import HttpUser, task, between


class SiriusUser(HttpUser):
    """Виртуальный пользователь «Сириус.Еды»."""
    wait_time = between(1, 3)  # пауза между запросами 1–3 сек

    @task(7)
    def get_menu(self):
        """70% запросов — витрина."""
        self.client.get("/menu/items")

    @task(2)
    def get_menu_item(self):
        """20% запросов — карточка блюда."""
        self.client.get("/menu/items/1")

    @task(1)
    def create_order(self):
        """10% запросов — создание заказа."""
        self.client.post("/orders/create", json={
            "user_id": 1,
            "item_id": 1,
            "quantity": 1,
        })