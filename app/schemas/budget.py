"""Budget schemas for API validation and serialization."""
from marshmallow import Schema, ValidationError, fields, validates, validates_schema


class BudgetSchema(Schema):
    """Schema for budget data."""

    id = fields.Str(dump_only=True)
    name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 255)
    description = fields.Str(allow_none=True)
    amount = fields.Decimal(required=True, as_string=True, places=2)
    currency = fields.Str(missing="USD", validate=lambda x: len(x) == 3)
    period = fields.Str(
        missing="monthly",
        validate=lambda x: x in ["daily", "weekly", "monthly", "quarterly", "yearly", "custom"],
    )
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    category_id = fields.Str(allow_none=True)
    owner_id = fields.Str(allow_none=True)
    alert_threshold = fields.Int(missing=80, validate=lambda x: 0 <= x <= 100)
    alert_enabled = fields.Bool(missing=True)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates("amount")
    def validate_amount(self, value):
        """Validate amount is positive."""
        if value <= 0:
            raise ValidationError("Amount must be greater than 0")

    @validates_schema
    def validate_dates(self, data, **kwargs):
        """Validate start_date is before end_date."""
        if "start_date" in data and "end_date" in data:
            if data["start_date"] > data["end_date"]:
                raise ValidationError("start_date must be before end_date")


class BudgetCreateSchema(Schema):
    """Schema for creating a budget."""

    name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 255)
    description = fields.Str(allow_none=True)
    amount = fields.Decimal(required=True, as_string=True, places=2)
    currency = fields.Str(missing="USD", validate=lambda x: len(x) == 3)
    period = fields.Str(
        missing="monthly",
        validate=lambda x: x in ["daily", "weekly", "monthly", "quarterly", "yearly", "custom"],
    )
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    category_id = fields.Str(allow_none=True)
    owner_id = fields.Str(allow_none=True)
    alert_threshold = fields.Int(missing=80, validate=lambda x: 0 <= x <= 100)
    alert_enabled = fields.Bool(missing=True)


class BudgetUpdateSchema(Schema):
    """Schema for updating a budget."""

    name = fields.Str(validate=lambda x: 1 <= len(x) <= 255)
    description = fields.Str(allow_none=True)
    amount = fields.Decimal(as_string=True, places=2)
    end_date = fields.Date()
    alert_threshold = fields.Int(validate=lambda x: 0 <= x <= 100)
    alert_enabled = fields.Bool()
    is_active = fields.Bool()


class BudgetStatusSchema(Schema):
    """Schema for budget status (spent/remaining)."""

    budget_id = fields.Str()
    name = fields.Str()
    amount = fields.Decimal(as_string=True, places=2)
    spent = fields.Decimal(as_string=True, places=2)
    remaining = fields.Decimal(as_string=True, places=2)
    utilization_percentage = fields.Float()
    is_exceeded = fields.Bool()
    alert_threshold = fields.Int()
    should_alert = fields.Bool()


class BudgetAlertSchema(Schema):
    """Schema for budget alert."""

    id = fields.Str(dump_only=True)
    budget_id = fields.Str()
    threshold_percentage = fields.Int()
    amount_spent = fields.Decimal(as_string=True, places=2)
    budget_amount = fields.Decimal(as_string=True, places=2)
    is_sent = fields.Bool()
    sent_at = fields.Date()
    created_at = fields.DateTime(dump_only=True)
