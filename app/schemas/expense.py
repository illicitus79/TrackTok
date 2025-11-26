"""Expense schemas for API validation and serialization."""
from datetime import date

from marshmallow import Schema, ValidationError, fields, validates
from app.core.extensions import db
from app.models.user import User


class CategorySchema(Schema):
    """Schema for expense category."""

    id = fields.Str(dump_only=True)
    name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 100)
    description = fields.Str(allow_none=True)
    color = fields.Str(allow_none=True, validate=lambda x: x is None or len(x) == 7)
    icon = fields.Str(allow_none=True)
    is_budget_enabled = fields.Bool(missing=False)
    monthly_budget = fields.Decimal(allow_none=True, as_string=True, places=2)
    parent_id = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class ExpenseSchema(Schema):
    """Schema for expense data."""

    id = fields.Str(dump_only=True)
    amount = fields.Decimal(required=True, as_string=True, places=2)
    currency = fields.Str(missing="USD", validate=lambda x: len(x) == 3)
    title = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 255)
    description = fields.Str(allow_none=True)
    category_id = fields.Str(required=True)
    expense_date = fields.Date(required=True)
    payment_method = fields.Str(
        missing="cash",
        validate=lambda x: x
        in ["cash", "credit_card", "debit_card", "bank_transfer", "other"],
    )
    payment_reference = fields.Str(allow_none=True)
    status = fields.Str(
        dump_only=True,
        validate=lambda x: x in ["draft", "submitted", "approved", "rejected"],
    )
    receipt_url = fields.Str(allow_none=True)
    attachments = fields.List(fields.Dict(), missing=list)
    tags = fields.List(fields.Str(), missing=list)
    notes = fields.Str(allow_none=True)
    metadata = fields.Dict(missing=dict)
    created_by = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    edited = fields.Method("get_edited", dump_only=True)
    last_amount = fields.Method("get_last_amount", dump_only=True)
    last_updated_by = fields.Method("get_last_updated_by", dump_only=True)
    last_updated_at = fields.Method("get_last_updated_at", dump_only=True)

    @validates("amount")
    def validate_amount(self, value):
        """Validate amount is positive."""
        if value <= 0:
            raise ValidationError("Amount must be greater than 0")

    @validates("expense_date")
    def validate_date(self, value):
        """Validate expense date is not in the future."""
        if value > date.today():
            raise ValidationError("Expense date cannot be in the future")

    def _meta(self, obj):
        return getattr(obj, "expense_metadata", {}) or {}

    def get_edited(self, obj):
        return bool(self._meta(obj).get("edited"))

    def get_last_amount(self, obj):
        val = self._meta(obj).get("last_amount")
        return str(val) if val is not None else None

    def get_last_updated_by(self, obj):
        user_id = self._meta(obj).get("last_updated_by")
        if not user_id:
            return None
        user = db.session.get(User, user_id)
        if not user:
            return user_id
        return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email or user_id

    def get_last_updated_at(self, obj):
        return self._meta(obj).get("last_updated_at")


class ExpenseCreateSchema(Schema):
    """Schema for creating an expense."""

    amount = fields.Decimal(required=True, as_string=True, places=2)
    currency = fields.Str(missing="USD", validate=lambda x: len(x) == 3)
    title = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 255)
    description = fields.Str(allow_none=True)
    category_id = fields.Str(required=True)
    expense_date = fields.Date(required=True)
    payment_method = fields.Str(
        missing="cash",
        validate=lambda x: x
        in ["cash", "credit_card", "debit_card", "bank_transfer", "other"],
    )
    payment_reference = fields.Str(allow_none=True)
    receipt_url = fields.Str(allow_none=True)
    tags = fields.List(fields.Str(), missing=list)
    notes = fields.Str(allow_none=True)
    metadata = fields.Dict(missing=dict)


class ExpenseUpdateSchema(Schema):
    """Schema for updating an expense."""

    amount = fields.Decimal(as_string=True, places=2)
    title = fields.Str(validate=lambda x: 1 <= len(x) <= 255)
    description = fields.Str(allow_none=True)
    category_id = fields.Str()
    expense_date = fields.Date()
    payment_method = fields.Str(
        validate=lambda x: x
        in ["cash", "credit_card", "debit_card", "bank_transfer", "other"]
    )
    payment_reference = fields.Str(allow_none=True)
    receipt_url = fields.Str(allow_none=True)
    tags = fields.List(fields.Str())
    notes = fields.Str(allow_none=True)
    metadata = fields.Dict()


class ExpenseFilterSchema(Schema):
    """Schema for expense filtering query parameters."""

    project_id = fields.Str()
    account_id = fields.Str()
    category_id = fields.Str()
    status = fields.Str(validate=lambda x: x in ["draft", "submitted", "approved", "rejected"])
    min_amount = fields.Decimal(as_string=True, places=2)
    max_amount = fields.Decimal(as_string=True, places=2)
    start_date = fields.Date()
    end_date = fields.Date()
    payment_method = fields.Str()
    tags = fields.List(fields.Str())
    search = fields.Str()  # Search in title/description
    page = fields.Int(missing=1, validate=lambda x: x > 0)
    per_page = fields.Int(missing=20, validate=lambda x: 1 <= x <= 100)
    sort_by = fields.Str(missing="expense_date", validate=lambda x: x in ["expense_date", "amount", "created_at"])
    sort_order = fields.Str(missing="desc", validate=lambda x: x in ["asc", "desc"])


class RecurringExpenseSchema(Schema):
    """Schema for recurring expense."""

    id = fields.Str(dump_only=True)
    amount = fields.Decimal(required=True, as_string=True, places=2)
    currency = fields.Str(missing="USD", validate=lambda x: len(x) == 3)
    title = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 255)
    description = fields.Str(allow_none=True)
    category_id = fields.Str(required=True)
    frequency = fields.Str(
        required=True,
        validate=lambda x: x in ["daily", "weekly", "monthly", "yearly"],
    )
    interval = fields.Int(missing=1, validate=lambda x: x > 0)
    start_date = fields.Date(required=True)
    end_date = fields.Date(allow_none=True)
    is_active = fields.Bool(missing=True)
    next_generation_date = fields.Date(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
