import logging
import os
import typing as t

import aio_pika
import asyncpg
from aiohttp import web

from auth_service.handlers import auth, health, sign_in, sign_up


INIT_DB_TABLES = """
    CREATE SCHEMA IF NOT EXISTS auth;

    CREATE TABLE IF NOT EXISTS auth.user (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS auth.session (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES auth.user,
        token TEXT NOT NULL UNIQUE
    );
"""


async def init_pg_pool(app: web.Application) -> t.AsyncIterator[None]:
    async with await asyncpg.create_pool(dsn=os.getenv("POSTGRESQL_URL")) as pool:
        app["pg_pool"] = pool

        async with pool.acquire() as connection:
            await connection.execute(INIT_DB_TABLES)

        yield


async def init_amqp_connection(app: web.Application) -> t.AsyncIterator[None]:
    connection = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))

    async with connection:
        app["amqp_connection"] = connection
        yield


async def init_app() -> web.Application:
    app = web.Application()
    app.cleanup_ctx.append(init_pg_pool)
    app.cleanup_ctx.append(init_amqp_connection)
    app.add_routes(
        [
            web.get("/auth{req_url:/?.*}", auth),
            web.post("/sign-up", sign_up),
            web.post("/sign-in", sign_in),
            web.get("/health", health)
        ]
    )
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(init_app(), port=8070)
