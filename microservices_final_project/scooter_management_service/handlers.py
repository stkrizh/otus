import json
import logging
from uuid import uuid4

import aio_pika
from aiohttp import web
from asyncpg import Pool, UniqueViolationError, ForeignKeyViolationError
from marshmallow import ValidationError

from scooter_management_service.schema import ScooterSchema, RentSchema, StartRentSchema


LOG = logging.getLogger(__name__)


async def health(_: web.Request) -> web.Response:
    return web.json_response()


async def get_scooters(request: web.Request) -> web.Response:
    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT * FROM scooter.scooter
            WHERE id NOT IN (
                SELECT scooter_id FROM scooter.rent WHERE status IN ('PENDING', 'ACTIVE')
            )
            ORDER BY charge DESC;
            """,
        )

    return web.json_response(ScooterSchema().dump(rows, many=True))


async def start_rent(request: web.Request) -> web.Response:
    pool = request.app["pg_pool"]
    amqp_connection = request.app["amqp_connection"]

    try:
        request_body = StartRentSchema().load(await request.json())
    except ValidationError as err:
        return web.json_response(err.normalized_messages(), status=400)

    user_id = request["user_id"]
    scooter_id = request_body["scooter_id"]

    async with pool.acquire() as connection:
        async with connection.transaction():
            try:
                row = await connection.fetchrow(
                    """
                    INSERT INTO scooter.rent (scooter_id, user_id, status) 
                    VALUES ($1, $2, 'PENDING')
                    RETURNING *
                    """,
                    scooter_id,
                    user_id,
                )
            except UniqueViolationError:
                LOG.info("Rent is not allowed.")
                return web.json_response(status=409)
            except ForeignKeyViolationError:
                LOG.info("Scooter with the ID doesn't exist.")
                return web.json_response(status=404)

            async with amqp_connection.channel() as channel:
                payload = {
                    "user_id": user_id,
                    "scooter_id": scooter_id,
                    "idempotency_key": uuid4().hex,
                }
                await channel.default_exchange.publish(
                    aio_pika.Message(body=json.dumps(payload).encode()),
                    routing_key="rent.pending",
                )

            LOG.info("Rent order is in pending status (idempotency key: %s).", payload["idempotency_key"])
            return web.json_response(RentSchema().dump(row))


async def stop_rent(request: web.Request) -> web.Response:
    pool = request.app["pg_pool"]
    user_id = request["user_id"]

    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            UPDATE scooter.rent SET status = 'FINISHED'
            WHERE user_id = $1 AND status = 'ACTIVE'
            RETURNING *
            """,
            user_id,
        )

    if row is None:
        LOG.info("Active rent not found.")
        return web.json_response(status=404)

    amqp_connection = request.app["amqp_connection"]
    async with amqp_connection.channel() as channel:
        payload = {
            "user_id": user_id,
            "scooter_id": row["scooter_id"],
            "idempotency_key": uuid4().hex,
        }
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(payload).encode()),
            routing_key="rent.finished",
        )

    LOG.info("Scooter rent has been successfully finished.")
    return web.json_response(RentSchema().dump(row), status=200)


async def get_rent_info(request: web.Request) -> web.Response:
    pool = request.app["pg_pool"]

    user_id = request["user_id"]

    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT * FROM scooter.rent WHERE user_id = $1
            ORDER BY id DESC LIMIT 1
            """,
            user_id,
        )

    if row is None:
        return web.json_response(status=404)

    return web.json_response(RentSchema().dump(row))


async def activate_rent(pool: Pool, message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        user_id = payload["user_id"]
        scooter_id = payload["scooter_id"]

        async with pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE scooter.rent SET status = 'ACTIVE'
                WHERE user_id = $1 AND scooter_id = $2 AND status = 'PENDING'
                """,
                user_id,
                scooter_id,
            )

    LOG.info("Scooter (%s) rent has been activated.", scooter_id)


async def cancel_rent(pool: Pool, message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        user_id = payload["user_id"]
        scooter_id = payload["scooter_id"]

        async with pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE scooter.rent SET status = 'CANCELED'
                WHERE user_id = $1 AND scooter_id = $2 AND status = 'PENDING'
                """,
                user_id,
                scooter_id,
            )

    LOG.info("Scooter (%s) rent has been canceled.", scooter_id)
