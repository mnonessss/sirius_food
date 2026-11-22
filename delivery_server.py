"""
Микросервис доставки. Работает как отдельный процесс.
Слушает порт 50051 и обслуживает gRPC-вызовы от монолита.
"""
import logging
import grpc
from concurrent import futures
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("delivery")

# Импорт сгенерированных классов.
import delivery_pb2
import delivery_pb2_grpc

# Импорт инфраструктуры монолита для работы с БД.
# В реальном проекте у микросервиса была бы своя БД и модели.
from app.database import SessionLocal
from app.models import Delivery, Order


class DeliveryServiceServicer(delivery_pb2_grpc.DeliveryServiceServicer):
    """
    Реализация бизнес-логики модуля доставки.
    """

    def AssignCourier(self, request, context):
        """Назначение курьера на заказ."""
        logger.info(
            "AssignCourier order_id=%s courier_id=%s",
            request.order_id,
            request.courier_id,
        )
        db = SessionLocal()
        try:
            # Проверка, что заказ существует.
            order = db.query(Order).filter(Order.id == request.order_id).first()
            if not order:
                context.abort(grpc.StatusCode.NOT_FOUND, "Order not found")

            # Создание доставки.
            delivery = Delivery(
                order_id=request.order_id,
                courier_id=request.courier_id,
                status="in_progress"
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)

            logger.info(
                "AssignCourier создана доставка id=%s status=%s",
                delivery.id,
                delivery.status,
            )
            return delivery_pb2.AssignCourierResponse(
                delivery_id=delivery.id,
                status=delivery.status
            )
        finally:
            db.close()

    def CompleteDelivery(self, request, context):
        """Завершение доставки."""
        logger.info("CompleteDelivery delivery_id=%s", request.delivery_id)
        db = SessionLocal()
        try:
            delivery = db.query(Delivery).filter(Delivery.id == request.delivery_id).first()
            if not delivery:
                context.abort(grpc.StatusCode.NOT_FOUND, "Delivery not found")
            
            delivery.status = "completed"
            db.commit()
            
            logger.info("CompleteDelivery id=%s status=%s", delivery.id, delivery.status)
            return delivery_pb2.CompleteDeliveryResponse(status=delivery.status)
        finally:
            db.close()

    def GetDelivery(self, request, context):
        """Получение информации о доставке по ID заказа."""
        logger.info("GetDelivery order_id=%s", request.order_id)
        db = SessionLocal()
        try:
            delivery = db.query(Delivery).filter(Delivery.order_id == request.order_id).first()
            if not delivery:
                context.abort(grpc.StatusCode.NOT_FOUND, "Delivery not found")
            
            logger.info(
                "GetDelivery id=%s status=%s courier_id=%s",
                delivery.id,
                delivery.status,
                delivery.courier_id,
            )
            return delivery_pb2.GetDeliveryResponse(
                id=delivery.id,
                status=delivery.status,
                courier_id=delivery.courier_id
            )
        finally:
            db.close()

    def ChatWithCourier(self, request_iterator, context):
        """Ответ курьера уходит сразу после каждого сообщения клиента."""
        for incoming in request_iterator:
            logger.info(
                "ChatWithCourier courier_id=%s sender=%s text=%s",
                incoming.courier_id,
                incoming.sender,
                incoming.text,
            )
            reply = f"Курьер {incoming.courier_id}: получил «{incoming.text}»"
            logger.info("ChatWithCourier ответ: %s", reply)
            yield delivery_pb2.ChatMessage(
                courier_id=incoming.courier_id,
                sender="courier",
                text=reply,
            )


def serve():
    """Запуск gRPC-сервера."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    delivery_pb2_grpc.add_DeliveryServiceServicer_to_server(
        DeliveryServiceServicer(), server
    )
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.info("Delivery gRPC Server running on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()