import json

import aio_pika
from aiohttp import web
from asyncpg import Pool
from marshmallow import ValidationError

from profile_service.schema import ProfileSchema


async def create_profile(pool: Pool, message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        user_id = payload["user_id"]

        async with pool.acquire() as connection:
            await connection.execute(
                """
                    INSERT INTO profile.profile (user_id) VALUES ($1)
                """,
                user_id,
            )


async def get_profile(request: web.Request) -> web.Response:
    user_id = request["user_id"]
    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
                SELECT * FROM profile.profile WHERE user_id = $1
            """,
            user_id,
        )

    if row is None:
        return web.json_response(status=404)

    return web.json_response(ProfileSchema().dump(row))


async def update_profile(request: web.Request) -> web.Response:
    user_id = request["user_id"]
    schema = ProfileSchema()

    try:
        request_body = schema.load(await request.json())
    except ValidationError as err:
        return web.json_response(err.normalized_messages(), status=400)

    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            UPDATE profile.profile SET first_name = $1, last_name = $2, email = $3
            WHERE user_id = $4 
            RETURNING *
            """,
            request_body.get("first_name"),
            request_body.get("last_name"),
            request_body.get("email"),
            user_id,
        )

    if row is None:
        return web.json_response(status=404)

    return web.json_response(schema.dump(row))


async def health(_: web.Request) -> web.Response:
    return web.json_response()
