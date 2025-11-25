"""Account schemas for request/response validation."""
from decimal import Decimal
from typing import Optional

from marshmallow import Schema, fields, validate


class AccountSchema(Schema):
    """Account schema for serialization/deserialization."""

    id = fields.Str(dump_only=True)
    tenant_id = fields.Str(dump_only=True)
    
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    account_type = fields.Str(
        validate=validate.OneOf(["cash", "bank", "credit_card", "digital_wallet"]),
        load_default="cash"
    )
    
    currency = fields.Str(validate=validate.Length(equal=3), load_default="USD")
    opening_balance = fields.Decimal(required=True, as_string=True, places=2)
    current_balance = fields.Decimal(dump_only=True, as_string=True, places=2)
    low_balance_threshold = fields.Decimal(as_string=True, places=2, allow_none=True)
    
    is_active = fields.Bool(load_default=True)
    is_archived = fields.Bool(dump_only=True)
    
    description = fields.Str(allow_none=True)
    account_number_last4 = fields.Str(validate=validate.Length(equal=4), allow_none=True)
    
    created_by = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)


class AccountDetailSchema(AccountSchema):
    """Account detail schema with calculated metrics."""

    is_low_balance = fields.Bool(dump_only=True)
    balance_change = fields.Decimal(dump_only=True, as_string=True, places=2)
    balance_change_percentage = fields.Float(dump_only=True)


class AccountCreateSchema(Schema):
    """Schema for creating a new account."""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    account_type = fields.Str(
        validate=validate.OneOf(["cash", "bank", "credit_card", "digital_wallet"]),
        load_default="cash"
    )
    currency = fields.Str(validate=validate.Length(equal=3), load_default="USD")
    opening_balance = fields.Decimal(required=True, as_string=True, places=2)
    low_balance_threshold = fields.Decimal(as_string=True, places=2, allow_none=True)
    description = fields.Str(allow_none=True)
    account_number_last4 = fields.Str(validate=validate.Length(equal=4), allow_none=True)


class AccountUpdateSchema(Schema):
    """Schema for updating an account."""

    name = fields.Str(validate=validate.Length(min=1, max=255))
    account_type = fields.Str(
        validate=validate.OneOf(["cash", "bank", "credit_card", "digital_wallet"])
    )
    low_balance_threshold = fields.Decimal(as_string=True, places=2, allow_none=True)
    is_active = fields.Bool()
    is_archived = fields.Bool()
    description = fields.Str(allow_none=True)


class AccountBalanceAdjustmentSchema(Schema):
    """Schema for manual balance adjustment."""

    new_balance = fields.Decimal(required=True, as_string=True, places=2)
    reason = fields.Str(required=True, validate=validate.Length(min=1))


class AccountListQuerySchema(Schema):
    """Schema for account list query parameters."""

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    account_type = fields.Str(
        validate=validate.OneOf(["cash", "bank", "credit_card", "digital_wallet"])
    )
    is_active = fields.Bool()
    is_archived = fields.Bool()
    search = fields.Str()
    sort_by = fields.Str(validate=validate.OneOf(["name", "created_at", "current_balance"]))
    sort_order = fields.Str(validate=validate.OneOf(["asc", "desc"]), load_default="desc")
