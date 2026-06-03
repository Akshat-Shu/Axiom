from marshmallow import Schema, fields, validate, validates, ValidationError


class TopicCreateSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    content_summary = fields.Str(load_default="")


class TopicUpdateSchema(Schema):
    title = fields.Str(validate=validate.Length(min=1, max=255))
    content_summary = fields.Str()


class ReviewSchema(Schema):
    duration_minutes = fields.Int(load_default=30, validate=validate.Range(min=1, max=480))
