"""
gRPC-клиент для общения с микросервисом доставки.
Является адаптером между бизнес-логикой монолита и сетью.
"""
import grpc
import delivery_pb2
import delivery_pb2_grpc


class DeliveryGrpcClient:
    def __init__(self, host: str = "localhost", port: int = 50051):
        # Создаём канал. insecure_channel — для локальной разработки без TLS.
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = delivery_pb2_grpc.DeliveryServiceStub(self.channel)

    def assign_courier(self, order_id: int, courier_id: int) -> dict:
        try:
            request = delivery_pb2.AssignCourierRequest(
                order_id=order_id, courier_id=courier_id
            )
            # Таймаут 5 секунд, чтобы не ждать вечно, если сервис упал.
            response = self.stub.AssignCourier(request, timeout=5)
            return {"delivery_id": response.delivery_id, "status": response.status}
        except grpc.RpcError as e:
            self._handle_error(e)

    def complete_delivery(self, delivery_id: int) -> dict:
        try:
            request = delivery_pb2.CompleteDeliveryRequest(delivery_id=delivery_id)
            response = self.stub.CompleteDelivery(request, timeout=5)
            return {"status": response.status}
        except grpc.RpcError as e:
            self._handle_error(e)

    def get_delivery(self, order_id: int) -> dict:
        try:
            request = delivery_pb2.GetDeliveryRequest(order_id=order_id)
            response = self.stub.GetDelivery(request, timeout=5)
            return {
                "id": response.id,
                "status": response.status,
                "courier_id": response.courier_id
            }
        except grpc.RpcError as e:
            self._handle_error(e)

    def chat_with_courier(self, courier_id: int, texts: list[str]):
        """Шлёт сообщения клиента и сразу отдаёт ответы курьера из того же потока."""
        def outgoing():
            for text in texts:
                yield delivery_pb2.ChatMessage(
                    courier_id=courier_id,
                    sender="client",
                    text=text,
                )

        try:
            for reply in self.stub.ChatWithCourier(outgoing(), timeout=30):
                yield {
                    "courier_id": reply.courier_id,
                    "sender": reply.sender,
                    "text": reply.text,
                }
        except grpc.RpcError as e:
            self._handle_error(e)

    def _handle_error(self, e: grpc.RpcError):
        """Обработка сетевых ошибок gRPC."""
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise ValueError("Object not found")
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            raise ConnectionError("Delivery service is unavailable")
        if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise TimeoutError("Delivery service timeout")
        raise RuntimeError(f"gRPC error: {e.details()}")