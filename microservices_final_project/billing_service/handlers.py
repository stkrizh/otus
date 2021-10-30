import json
from decimal import Decimal
from enum import Enum

import aio_pika
from aiohttp import web
from asyncpg import Pool, UniqueViolationError
from marshmallow import ValidationError

from billing_service.schema import AccountSchema, AddFundsSchema


RENT_PRICE = Decimal("100.00")
TEST_SCOOTER_ID = "test-billing-service-fails"


class PaymentStatus(Enum):
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


async def create_account(pool: Pool, message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        user_id = payload["user_id"]

        async with pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO billing.account (user_id, balance) VALUES ($1, 0)
                """,
                user_id,
            )


async def create_payment(pool: Pool, amqp_connection: aio_pika.Connection, message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        user_id = payload["user_id"]
        scooter_id = payload["scooter_id"]
        idempotency_key = payload["idempotency_key"]

        async with pool.acquire() as connection:
            async with connection.transaction() as transaction:
                row = await connection.fetchrow(
                    """
                    SELECT * FROM billing.account WHERE user_id = $1
                    FOR UPDATE
                    """,
                    user_id,
                )

                try:
                    await connection.fetchrow(
                        """
                        INSERT INTO billing.payment (user_id, amount, idempotency_key)
                        VALUES ($1, $2, $3)
                        """,
                        user_id,
                        -RENT_PRICE,
                        idempotency_key,
                    )
                except UniqueViolationError:
                    return None

                if (
                    row is None
                    or row["balance"] < RENT_PRICE
                    or scooter_id == TEST_SCOOTER_ID
                ):
                    await _notify_payment_canceled(amqp_connection, user_id, scooter_id)
                    await transaction.rollback()
                    return None

                await connection.fetchrow(
                    """
                    UPDATE billing.account SET balance = balance - $1 WHERE user_id = $2
                    """,
                    RENT_PRICE,
                    user_id,
                )
                await _notify_payment_succeeded(amqp_connection, user_id, scooter_id, idempotency_key)


async def cancel_payment(pool: Pool, amqp_connection: aio_pika.Connection, message: aio_pika.IncomingMessage) -> None:
    payload = json.loads(message.body)
    user_id = payload["user_id"]
    scooter_id = payload["scooter_id"]
    idempotency_key = payload["idempotency_key"]

    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.fetchrow(
                """
                SELECT * FROM billing.account WHERE user_id = $1
                FOR UPDATE
                """,
                user_id,
            )

            try:
                await connection.fetchrow(
                    """
                    INSERT INTO billing.payment (user_id, amount, idempotency_key)
                    VALUES ($1, $2, $3)
                    """,
                    user_id,
                    RENT_PRICE,
                    idempotency_key,
                )
            except UniqueViolationError:
                return None

            await connection.fetchrow(
                """
                UPDATE billing.account SET balance = balance + $1 WHERE user_id = $2
                """,
                RENT_PRICE,
                user_id,
            )
            await _notify_payment_canceled(amqp_connection, user_id, scooter_id)


async def get_balance(request: web.Request) -> web.Response:
    user_id = request["user_id"]
    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT * FROM billing.account WHERE user_id = $1
            """,
            user_id,
        )

    if row is None:
        return web.json_response(status=404)

    return web.json_response(AccountSchema().dump(row))


# TODO: replace version with idempotency key
async def add_funds(request: web.Request) -> web.Response:
    user_id = request["user_id"]
    schema = AddFundsSchema()

    try:
        request_body = schema.load(await request.json())
    except ValidationError as err:
        return web.json_response(err.normalized_messages(), status=400)

    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        async with connection.transaction():
            row = await connection.fetchrow(
                """
                SELECT * FROM billing.account WHERE user_id = $1 
                FOR UPDATE
                """,
                user_id,
            )

            if row is None:
                return web.json_response(status=404)

            if row["version"] != request_body["version"]:
                return web.json_response(status=412)

            row = await connection.fetchrow(
                """
                UPDATE billing.account SET 
                    balance = balance + $1, 
                    version = version + 1
                WHERE user_id = $2
                RETURNING *
                """,
                request_body["amount"],
                user_id,
            )

            # TODO: publish funds.transfer.succeeded

    response_schema = AccountSchema()
    return web.json_response(response_schema.dump(row))


async def health(_: web.Request) -> web.Response:
    return web.json_response()


async def _notify_payment_succeeded(
    amqp_connection: aio_pika.Connection,
    user_id: int,
    scooter_id: str,
    idempotency_key: str,
) -> None:
    payload = {
        "user_id": user_id,
        "scooter_id": scooter_id,
        "idempotency_key": idempotency_key,
    }

    async with amqp_connection.channel() as channel:
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(payload).encode()),
            routing_key="payment.succeeded",
        )


async def _notify_payment_canceled(amqp_connection: aio_pika.Connection, user_id: int, scooter_id: str) -> None:
    payload = {
        "user_id": user_id,
        "scooter_id": scooter_id,
    }

    async with amqp_connection.channel() as channel:
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(payload).encode()),
            routing_key="payment.canceled",
        )
