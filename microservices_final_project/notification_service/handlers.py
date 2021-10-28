import datetime as dt
import json

import aio_pika
from aiohttp import web
from asyncpg import Pool

from notification_service.schema import NotificationSchema


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


async def create_notification(pool: Pool, message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        user_id = payload["user_id"]
        amount = payload["amount"]
        status = message.routing_key.split(".")[-1]

        async with pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO notification.notification (user_id, created_at, payment_amount, status) 
                VALUES ($1, $2, $3, $4)
                """,
                user_id,
                dt.datetime.utcnow(),
                amount,
                status,
            )


async def health(_: web.Request) -> web.Response:
    return web.json_response()
