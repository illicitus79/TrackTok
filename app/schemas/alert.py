"""Alert schemas for request/response validation."""
from marshmallow import Schema, fields, validate


class AlertSchema(Schema):
    """Alert schema for serialization/deserialization."""

    id = fields.Str(dump_only=True)
    tenant_id = fields.Str(dump_only=True)
    
    alert_type = fields.Str(
        required=True,
        validate=validate.OneOf([
            "LOW_BALANCE",
            "FORECAST_OVERSPEND",
            "BUDGET_EXCEEDED",
            "PROJECT_DEADLINE",
            "ACCOUNT_INACTIVE"
        ])
    )
    severity = fields.Str(
        validate=validate.OneOf(["info", "warning", "error", "critical"]),
        load_default="warning"
    )
    
    entity_type = fields.Str(
        required=True,
        validate=validate.OneOf(["account", "project", "budget", "expense"])
    )
    entity_id = fields.Str(required=True)
    
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    message = fields.Str(required=True)
    
    metadata = fields.Dict(allow_none=True)
    
    is_read = fields.Bool(dump_only=True)
    read_at = fields.DateTime(dump_only=True)
    read_by = fields.Str(dump_only=True)
    
    is_dismissed = fields.Bool(dump_only=True)
    dismissed_at = fields.DateTime(dump_only=True)
    
    notification_sent = fields.Bool(dump_only=True)
    notification_sent_at = fields.DateTime(dump_only=True)
    
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)


class AlertCreateSchema(Schema):
    """Schema for creating a new alert."""

    alert_type = fields.Str(
        required=True,
        validate=validate.OneOf([
            "LOW_BALANCE",
            "FORECAST_OVERSPEND",
            "BUDGET_EXCEEDED",
            "PROJECT_DEADLINE",
            "ACCOUNT_INACTIVE"
        ])
    )
    severity = fields.Str(
        validate=validate.OneOf(["info", "warning", "error", "critical"]),
        load_default="warning"
    )
    entity_type = fields.Str(
        required=True,
        validate=validate.OneOf(["account", "project", "budget", "expense"])
    )
    entity_id = fields.Str(required=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    message = fields.Str(required=True)
    metadata = fields.Dict(allow_none=True)


class AlertUpdateSchema(Schema):
    """Schema for updating an alert."""

    is_read = fields.Bool()
    is_dismissed = fields.Bool()


class AlertListQuerySchema(Schema):
    """Schema for alert list query parameters."""

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    alert_type = fields.Str(
        validate=validate.OneOf([
            "LOW_BALANCE",
            "FORECAST_OVERSPEND",
            "BUDGET_EXCEEDED",
            "PROJECT_DEADLINE",
            "ACCOUNT_INACTIVE"
        ])
    )
    severity = fields.Str(validate=validate.OneOf(["info", "warning", "error", "critical"]))
    entity_type = fields.Str(validate=validate.OneOf(["account", "project", "budget", "expense"]))
    is_read = fields.Bool()
    is_dismissed = fields.Bool()
    sort_by = fields.Str(validate=validate.OneOf(["created_at", "severity"]))
    sort_order = fields.Str(validate=validate.OneOf(["asc", "desc"]), load_default="desc")
