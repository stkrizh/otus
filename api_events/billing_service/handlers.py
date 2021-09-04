import json
from decimal import Decimal
from enum import Enum

import aio_pika
from aio_pika import Connection
from aiohttp import web
from asyncpg import Pool
from marshmallow import ValidationError

from billing_service.schema import AccountSchema, AddFundsSchema, CreatePaymentSchema


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


async def add_funds(request: web.Request) -> web.Response:
    user_id = request["user_id"]
    schema = AddFundsSchema()

    try:
        request_body = schema.load(await request.json())
    except ValidationError as err:
        return web.json_response(err.normalized_messages(), status=400)

    pool = request.app["pg_pool"]

    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            UPDATE billing.account SET balance = balance + $1
            WHERE user_id = $2 
            RETURNING *
            """,
            request_body.get("amount"),
            user_id,
        )

    if row is None:
        return web.json_response(status=404)

    response_schema = AccountSchema()
    return web.json_response(response_schema.dump(row))


async def create_payment(request: web.Request) -> web.Response:
    amqp_connection = request.app["amqp_connection"]
    user_id = request["user_id"]
    schema = CreatePaymentSchema()

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
            if row["balance"] < request_body["amount"]:
                await _notify_payment_canceled(amqp_connection, user_id, request_body["amount"])
                return web.json_response({"error": "Insufficient funds."}, status=400)

            await connection.fetchrow(
                """
                UPDATE billing.account SET balance = balance - $1
                WHERE user_id = $2
                """,
                request_body["amount"],
                user_id,
            )

    await _notify_payment_succeeded(amqp_connection, user_id, request_body["amount"])
    return web.json_response(status=201)


async def health(_: web.Request) -> web.Response:
    return web.json_response()


async def _notify_payment_succeeded(amqp_connection: Connection, user_id: int, amount: Decimal) -> None:
    async with amqp_connection.channel() as channel:
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps({"user_id": user_id, "amount": str(amount)}).encode()),
            routing_key="payment.succeeded",
        )


async def _notify_payment_canceled(amqp_connection: Connection, user_id: int, amount: Decimal) -> None:
    async with amqp_connection.channel() as channel:
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps({"user_id": user_id, "amount": str(amount)}).encode()),
            routing_key="payment.canceled",
        )
