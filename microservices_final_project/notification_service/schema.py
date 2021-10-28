from marshmallow import Schema, fields


class NotificationSchema(Schema):
    id = fields.Integer()
    event = fields.String()
    created_at = fields.DateTime()
    status = fields.String()
