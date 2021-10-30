import datetime as dt
import json
from uuid import uuid4

import aio_pika
from aiohttp import web
from asyncpg import Pool, UniqueViolationError

from notification_service.schema import NotificationSchema


TEST_SCOOTER_ID = "test-notification-service-fails"


async def get_notifications(request: web.Request) -> web.Response:
    user_id = request["user_id"]
    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT * FROM notification.notification WHERE user_id = $1 ORDER BY id DESC;
            """,
            user_id,
        )

    return web.json_response(NotificationSchema().dump(rows, many=True))


async def create_notification_on_payment_succeeded(
        pool: Pool,
        amqp_connection: aio_pika.Connection,
        message: aio_pika.IncomingMessage,
) -> None:
    async with message.process():
        payload = json.loads(message.body)
        user_id = payload["user_id"]
        scooter_id = payload["scooter_id"]
        idempotency_key = payload["idempotency_key"]

        async with pool.acquire() as connection:
            async with connection.transaction() as transaction:
                try:
                    await connection.execute(
                        """
                        INSERT INTO notification.notification (user_id, event, created_at, idempotency_key) 
                        VALUES ($1, $2, $3, $4)
                        """,
                        user_id,
                        f"Scooter rent started - {scooter_id}",
                        dt.datetime.utcnow(),
                        idempotency_key,
                    )
                except UniqueViolationError:
                    return None

                if scooter_id == TEST_SCOOTER_ID:
                    await _notify_notification_failed(amqp_connection, user_id, scooter_id)
                    await transaction.rollback()
                    return None

                await _notify_notification_succeeded(amqp_connection, user_id, scooter_id)


async def health(_: web.Request) -> web.Response:
    return web.json_response()


async def _notify_notification_failed(amqp_connection: aio_pika.Connection, user_id: int, scooter_id: str) -> None:
    payload = {
        "user_id": user_id,
        "scooter_id": scooter_id,
        "idempotency_key": uuid4().hex,
    }
    async with amqp_connection.channel() as channel:
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(payload).encode()),
            routing_key="rent.notification.failed",
        )


async def _notify_notification_succeeded(amqp_connection: aio_pika.Connection, user_id: int, scooter_id: str) -> None:
    async with amqp_connection.channel() as channel:
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps({"user_id": user_id, "scooter_id": scooter_id}).encode()),
            routing_key="rent.notification.succeeded",
        )
