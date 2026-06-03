from marshmallow import Schema, fields, validate


class UserCreateSchema(Schema):
    email = fields.Email(required=True)
    username = fields.Str(required=True, validate=validate.Length(min=2, max=100))
