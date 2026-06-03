from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from datetime import datetime


class EventCreateSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(load_default="")
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(required=True)
    priority = fields.Int(load_default=3, validate=validate.Range(min=1, max=5))
    is_flexible = fields.Bool(load_default=False)

    @validates_schema
    def validate_time_range(self, data, **kwargs):
        if data.get("start_time") and data.get("end_time"):
            if data["end_time"] <= data["start_time"]:
                raise ValidationError("end_time must be after start_time")


class EventUpdateSchema(Schema):
    title = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str()
    start_time = fields.DateTime()
    end_time = fields.DateTime()
    priority = fields.Int(validate=validate.Range(min=1, max=5))
    is_flexible = fields.Bool()

    @validates_schema
    def validate_time_range(self, data, **kwargs):
        if data.get("start_time") and data.get("end_time"):
            if data["end_time"] <= data["start_time"]:
                raise ValidationError("end_time must be after start_time")


class EventListQuerySchema(Schema):
    start = fields.DateTime(load_default=None)
    end = fields.DateTime(load_default=None)
