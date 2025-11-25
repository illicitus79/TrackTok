"""User preferences schemas for API validation."""
from marshmallow import Schema, fields, validate


class UserPreferencesSchema(Schema):
    """Full user preferences schema."""
    
    id = fields.Str(dump_only=True)
    user_id = fields.Str(dump_only=True)
    
    # Email notifications
    email_notifications_enabled = fields.Bool()
    email_frequency = fields.Str(
        validate=validate.OneOf(["instant", "daily_digest", "weekly_digest"])
    )
    
    # Alert type preferences
    notify_low_balance = fields.Bool()
    notify_forecast_overspend = fields.Bool()
    notify_budget_exceeded = fields.Bool()
    notify_project_deadline = fields.Bool()
    
    # Notification channels
    in_app_notifications = fields.Bool()
    email_alerts = fields.Bool()
    push_notifications = fields.Bool()
    
    # Digest preferences
    daily_summary_enabled = fields.Bool()
    daily_summary_time = fields.Str(
        validate=validate.Regexp(r"^([01]\d|2[0-3]):([0-5]\d)$"),
        allow_none=True
    )
    weekly_report_enabled = fields.Bool()
    weekly_report_day = fields.Str(
        validate=validate.OneOf([
            "monday", "tuesday", "wednesday", "thursday", 
            "friday", "saturday", "sunday"
        ]),
        allow_none=True
    )
    
    # UI preferences
    theme = fields.Str(validate=validate.OneOf(["dark", "light", "auto"]))
    dashboard_layout = fields.Dict(allow_none=True)
    chart_preferences = fields.Dict(allow_none=True)
    
    # Timezone and locale
    timezone = fields.Str()
    locale = fields.Str()
    
    # Additional settings
    custom_settings = fields.Dict(allow_none=True)
    
    # Timestamps
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class UserPreferencesUpdateSchema(Schema):
    """Schema for updating user preferences."""
    
    # Email notifications
    email_notifications_enabled = fields.Bool()
    email_frequency = fields.Str(
        validate=validate.OneOf(["instant", "daily_digest", "weekly_digest"])
    )
    
    # Alert type preferences
    notify_low_balance = fields.Bool()
    notify_forecast_overspend = fields.Bool()
    notify_budget_exceeded = fields.Bool()
    notify_project_deadline = fields.Bool()
    
    # Notification channels
    in_app_notifications = fields.Bool()
    email_alerts = fields.Bool()
    push_notifications = fields.Bool()
    
    # Digest preferences
    daily_summary_enabled = fields.Bool()
    daily_summary_time = fields.Str(
        validate=validate.Regexp(r"^([01]\d|2[0-3]):([0-5]\d)$"),
        allow_none=True
    )
    weekly_report_enabled = fields.Bool()
    weekly_report_day = fields.Str(
        validate=validate.OneOf([
            "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"
        ]),
        allow_none=True
    )
    
    # UI preferences
    theme = fields.Str(validate=validate.OneOf(["dark", "light", "auto"]))
    dashboard_layout = fields.Dict(allow_none=True)
    chart_preferences = fields.Dict(allow_none=True)
    
    # Timezone and locale
    timezone = fields.Str()
    locale = fields.Str()
    
    # Additional settings
    custom_settings = fields.Dict(allow_none=True)
