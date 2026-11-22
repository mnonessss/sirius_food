"""Клиент двустороннего чата с курьером.

Сервер delivery_server.py должен слушать порт 50051.
Сообщение передаётся аргументами командной строки.
"""
import sys

from app.modules.delivery.grpc_client import DeliveryGrpcClient


def main() -> None:
    text = " ".join(sys.argv[1:]).strip() or "Где мой заказ?"
    client = DeliveryGrpcClient()
    for reply in client.chat_with_courier(courier_id=8, texts=[text]):
        print(f"{reply['sender']}: {reply['text']}")


if __name__ == "__main__":
    main()
