import json
from hashlib import sha256
from secrets import token_hex

import aio_pika
from aiohttp import web
from asyncpg.exceptions import UniqueViolationError
from marshmallow import ValidationError

from auth_service.schema import AuthHeaderSchema, SignInSchema, SignUpSchema, UserSchema


async def sign_up(request: web.Request) -> web.Response:
    schema = SignUpSchema()

    try:
        request_body = schema.load(await request.json())
    except ValidationError as err:
        return web.json_response(err.normalized_messages(), status=400)

    username = request_body["username"]
    raw_password = request_body["password"]
    password_hash = sha256(raw_password.encode()).hexdigest()

    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        try:
            user_id = await connection.fetchval(
                """
                    INSERT INTO auth.user (name, password) VALUES ($1, $2) 
                    RETURNING id
                """,
                username,
                password_hash,
            )
        except UniqueViolationError:
            return web.json_response({"username": ["Already exists."]}, status=400)

    amqp_connection = request.app["amqp_connection"]
    async with amqp_connection.channel() as channel:
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps({"user_id": user_id}).encode()),
            routing_key="user.created",
        )

    return web.json_response(status=201)


async def sign_in(request: web.Request) -> web.Response:
    schema = SignInSchema()

    try:
        request_body = schema.load(await request.json())
    except ValidationError as err:
        return web.json_response(err.normalized_messages(), status=400)

    username = request_body["username"]
    raw_password = request_body["password"]
    password_hash = sha256(raw_password.encode()).hexdigest()

    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        user_row = await connection.fetchrow(
            """
                SELECT * from auth.user WHERE name = $1 AND password = $2
            """,
            username,
            password_hash,
        )

    if user_row is None:
        return web.json_response(status=401)

    async with pool.acquire() as connection:
        session_row = await connection.fetchrow(
            """
                INSERT INTO auth.session (user_id, token) VALUES ($1, $2)
                RETURNING token
            """,
            user_row["id"],
            token_hex(64),
        )

    return web.json_response({"token": session_row["token"]})


async def auth(request: web.Request) -> web.Response:
    try:
        token = AuthHeaderSchema().load(request.headers)
    except ValidationError:
        return web.json_response(status=401)

    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        user_row = await connection.fetchrow(
            """
                SELECT * from auth.user
                JOIN auth.session ON auth.user.id = auth.session.user_id
                WHERE auth.session.token = $1
            """,
            token,
        )

    if user_row is None:
        return web.json_response(status=401)

    return web.json_response(
        headers={
            "X-User-Id": str(user_row["user_id"]),
        },
    )


async def health(_: web.Request) -> web.Response:
    return web.json_response()
