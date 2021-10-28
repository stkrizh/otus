import logging
import os
import typing as t
from functools import partial
from random import random
from uuid import uuid4

import aio_pika
import asyncpg
from aiohttp import web

from scooter_management_service.handlers import (
    health,
    get_rent_info,
    get_scooters,
    start_rent,
    stop_rent,
    activate_rent,
    cancel_rent,
)

INIT_DB_TABLES = """
    CREATE SCHEMA IF NOT EXISTS scooter;

    CREATE TABLE IF NOT EXISTS scooter.scooter (
        id UUID PRIMARY KEY,
        charge DOUBLE PRECISION NOT NULL,
        latitude DECIMAL(10,8) NOT NULL,
        longitude DECIMAL(11,8) NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS scooter.rent (
        id SERIAL PRIMARY KEY,
        scooter_id UUID NOT NULL REFERENCES scooter.scooter (id),
        user_id INTEGER NOT NULL,
        status TEXT NOT NULL
    );
    
    CREATE UNIQUE INDEX IF NOT EXISTS user_idx ON scooter.rent (user_id)
    WHERE status IN ('PENDING', 'ACTIVE');
    
    CREATE UNIQUE INDEX IF NOT EXISTS scooter_idx ON scooter.rent (scooter_id)
    WHERE status IN ('PENDING', 'ACTIVE');
"""


async def init_pg_pool(app: web.Application) -> asyncpg.Pool:
    async with await asyncpg.create_pool(os.getenv("POSTGRESQL_URL")) as pool:
        app["pg_pool"] = pool

        async with pool.acquire() as connection:
            await connection.execute(INIT_DB_TABLES)

            count = await connection.fetchval("SELECT COUNT(id) FROM scooter.scooter")

            if count == 0:
                for _ in range(20):
                    await connection.execute(
                        """
                        INSERT INTO scooter.scooter  (id, charge, latitude, longitude) VALUES
                        ($1, $2, $3, $4)
                        """,
                        uuid4(),
                        random() * 100,
                        random() * 180 - 90,
                        random() * 360 - 180,
                    )

        yield


async def init_amqp_connection(app: web.Application) -> t.AsyncIterator[None]:
    connection = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))

    async with connection:
        app["amqp_connection"] = connection

        async with connection.channel() as channel:
            queue_rent_activation = await channel.declare_queue("rent.activated")
            await queue_rent_activation.consume(partial(activate_rent, app["pg_pool"]))

            queue_rent_canceling = await channel.declare_queue("rent.canceled")
            await queue_rent_canceling.consume(partial(cancel_rent, app["pg_pool"]))

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
            web.get("/", get_scooters),
            web.get("/rent", get_rent_info),
            web.put("/rent", start_rent),
            web.delete("/rent", stop_rent),
            web.get("/health", health),
        ]
    )
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(init_app(), port=8090)
