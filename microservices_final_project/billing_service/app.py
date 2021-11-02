import logging
import os
import typing as t
from functools import partial

import aio_pika
import asyncpg
from aiohttp import web

from billing_service.handlers import add_funds, create_account, create_payment, get_balance, health, cancel_payment

INIT_DB_TABLES = """
    CREATE SCHEMA IF NOT EXISTS billing;

    CREATE TABLE IF NOT EXISTS billing.account (
        user_id INTEGER PRIMARY KEY,
        balance NUMERIC(13,2) NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS billing.payment (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES billing.account (user_id),
        amount NUMERIC(13,2) NOT NULL,
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
            user_created_queue = await channel.declare_queue("user.created", auto_delete=True)
            await user_created_queue.consume(partial(create_account, app["pg_pool"]))

            rent_pending_queue = await channel.declare_queue("rent.pending", auto_delete=True)
            await rent_pending_queue.consume(partial(create_payment, app["pg_pool"], connection))

            rent_notification_failed_queue = await channel.declare_queue("rent.notification.failed", auto_delete=True)
            await rent_notification_failed_queue.consume(partial(cancel_payment, app["pg_pool"], connection))

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
            web.get("/", get_balance),
            web.post("/", add_funds),
            web.get("/health", health),
        ]
    )
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(init_app(), port=8081)
