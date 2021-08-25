from marshmallow import Schema, fields, validate


class ProfileSchema(Schema):
    first_name = fields.String(required=True, allow_none=True, validate=validate.Length(max=256))
    last_name = fields.String(required=True, allow_none=True, validate=validate.Length(max=256))
    email = fields.Email(required=True, allow_none=True, validate=validate.Length(max=256))
