# Sirius.Food

API столовой: пользователи, меню, заказы и доставка. Данные в PostgreSQL. Кеш меню и ограничение запросов — в Redis. Фоновые задачи заказов — в Celery.

## Зависимости

- Python 3.10 и виртуальное окружение `.venv`
- Docker: PostgreSQL 15 (порт 5440), Redis 7 (порт 6380)

## Запуск

```bash
docker compose up -d
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Проверка: http://127.0.0.1:8000/health отвечает `{"status":"ok"}`. Swagger при `DEBUG=True`: http://127.0.0.1:8000/docs.

Фоновые задачи:

```bash
celery -A app.core.celery_app worker -Q default --loglevel=info
celery -A app.core.celery_app beat --loglevel=info
celery -A app.core.celery_app flower --port=5555
```

Воркер слушает только очередь `default`. Очередь `dlq` остаётся в Redis, пока её не читают отдельно.

## Доставка: монолит и gRPC

HTTP-клиент по-прежнему ходит в монолит. Монолит проверяет токен и вызывает микросервис доставки. Запись в таблицу `deliveries` делает gRPC-сервер. База в этой работе общая.

```
HTTP-клиент
    |
    v
Монолит FastAPI :8000
    DeliveryGrpcClient
    |
    v
gRPC DeliveryService :50051
    |
    v
PostgreSQL :5440
```

Запуск микросервиса во втором терминале:

```bash
python delivery_server.py
```

Чат с курьером — двусторонний поток `ChatWithCourier`. Клиент отправляет сообщение и печатает ответ, не дожидаясь закрытия всего диалога:

```bash
python chat_client.py Где мой заказ?
```

## События и компенсация

Оплата публикует `order.paid`. Кухня и доставка подписаны на него отдельно. Если свободного курьера нет, доставка публикует `delivery.failed`. Воркер компенсации отменяет заказ, возвращает сумму на баланс и публикует `order.cancelled`. Повтор того же `event_id` возврат не повторяет.

```
POST /orders/{id}/pay
        |
        v
   order.paid
     |      |
     v      v
  кухня   доставка
            |
            | курьер не найден
            v
      delivery.failed
            |
            v
      компенсация: cancelled + возврат баланса
            |
            v
      order.cancelled
```

```bash
python -m app.workers.kitchen_consumer
python delivery_worker.py
python -m app.workers.compensation_consumer
```

## Трейсы

Jaeger поднимается вместе с остальными сервисами: `docker compose up -d jaeger`. Интерфейс: http://localhost:16686, сервис `order-service`.

Кухня слушает `order.paid`, поэтому полный путь заказа — один трейс запроса `POST /orders/{id}/pay`: HTTP, `OrderService.pay`, запись в базу, `RabbitMQ.publish` и `Kitchen.consume`. Ищите его по тегу `correlation_id`. Consumer кухни нужно перезапустить после включения трейсинга, у него нет автоперезагрузки.

