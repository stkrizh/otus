from marshmallow import Schema, fields


class NotificationSchema(Schema):
    id = fields.Integer()
    amount = fields.Decimal(places=2, as_string=True)
    created_at = fields.DateTime()
    status = fields.String()
