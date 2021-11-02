from marshmallow import Schema, fields, validate


class AccountSchema(Schema):
    balance = fields.Decimal(places=2, as_string=True)


class AddFundsSchema(Schema):
    amount = fields.Decimal(required=True, places=2, as_string=True, validate=validate.Range(min=0, max=1_000_000))
    idempotency_key = fields.String(required=True)
