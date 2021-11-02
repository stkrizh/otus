import logging
import os
import typing as t
from functools import partial

import aio_pika
import asyncpg
from aiohttp import web

from notification_service.handlers import (
    create_notification_on_funds_transferred,
    create_notification_on_payment_succeeded,
    create_notification_on_rent_finished,
    get_notifications,
    health,
)

INIT_DB_TABLES = """
    CREATE SCHEMA IF NOT EXISTS notification;

    CREATE TABLE IF NOT EXISTS notification.notification (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        event TEXT NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
        idempotency_key TEXT NOT NULL,
        UNIQUE (user_id, idempotency_key)
    );
"""


async def init_pg_pool(app: web.Application) -> asyncpg.Pool:
    async with await asyncpg.create_pool(os.getenv("POSTGRESQL_URL")) as pool:
        app["pg_pool"] = pool

        async with pool.acquire() as connection:
            await connection.execute(INIT_DB_TABLES)

        yield


async def init_amqp_connection(app: web.Application) -> t.AsyncIterator[None]:
    connection = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))

    async with connection:
        app["amqp_connection"] = connection

        async with connection.channel() as channel:
            queue_payment_succeeded = await channel.declare_queue("payment.succeeded", auto_delete=True)
            await queue_payment_succeeded.consume(
                partial(create_notification_on_payment_succeeded, app["pg_pool"], connection),
            )

            queue_funds_transferred = await channel.declare_queue("funds.transferred", auto_delete=True)
            await queue_funds_transferred.consume(
                partial(create_notification_on_funds_transferred, app["pg_pool"]),
            )

            queue_rent_finished = await channel.declare_queue("rent.finished", auto_delete=True)
            await queue_rent_finished.consume(
                partial(create_notification_on_rent_finished, app["pg_pool"]),
            )

            yield


@web.middleware
async def user_id_middleware(request: web.Request, handler: t.Any) -> web.Response:
    if request.path == "/health":
        return await handler(request)

    try:
        user_id = int(request.headers["x-user-id"])
    except (KeyError, TypeError, ValueError):
        return web.json_response(status=401)

    request["user_id"] = user_id
    return await handler(request)


async def init_app() -> web.Application:
    app = web.Application(middlewares=[user_id_middleware])
    app.cleanup_ctx.append(init_pg_pool)
    app.cleanup_ctx.append(init_amqp_connection)
    app.add_routes(
        [
            web.get("/", get_notifications),
            web.get("/health", health),
        ]
    )
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(init_app(), port=8082)
