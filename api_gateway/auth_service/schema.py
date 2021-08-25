from marshmallow import EXCLUDE, Schema, fields, post_load, validate


class AuthHeaderSchema(Schema):
    authorization = fields.String(
        required=True, validate=validate.Regexp("Bearer [0-9a-f]{64}")
    )

    class Meta:
        unknown = EXCLUDE

    @post_load
    def get_auth_token(self, data, **kwargs) -> str:
        return data["authorization"][7:]


class SignInSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(max=256))
    password = fields.String(required=True, validate=validate.Length(max=256))


class SignUpSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=2, max=256))
    password = fields.String(required=True, validate=validate.Length(min=2, max=256))


class UserSchema(Schema):
    id = fields.Int()
    name = fields.String()
