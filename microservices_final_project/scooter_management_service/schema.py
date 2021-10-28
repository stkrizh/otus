from marshmallow import Schema, fields, validate


class ScooterSchema(Schema):
    id = fields.UUID()
    charge = fields.Float()
    latitude = fields.Decimal(as_string=True)
    longitude = fields.Decimal(as_string=True)


class RentSchema(Schema):
    id = fields.Integer()
    scooter_id = fields.UUID()
    status = fields.String(validate=validate.OneOf(["PENDING", "ACTIVE", "CANCELED", "FINISHED"]))


class StartRentSchema(Schema):
    scooter_id = fields.UUID(required=True)
    version = fields.Integer(required=True)
