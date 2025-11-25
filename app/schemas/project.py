"""Project schemas for request/response validation."""
from datetime import date
from decimal import Decimal
from typing import Optional

from marshmallow import Schema, fields, validate


class ProjectSchema(Schema):
    """Project schema for serialization/deserialization."""

    id = fields.Str(dump_only=True)
    tenant_id = fields.Str(dump_only=True)
    
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    
    starting_budget = fields.Decimal(required=True, as_string=True, places=2)
    projected_estimate = fields.Decimal(required=True, as_string=True, places=2)
    currency = fields.Str(validate=validate.Length(equal=3), load_default="USD")
    
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)
    
    status = fields.Str(
        validate=validate.OneOf(["active", "completed", "archived", "on_hold"]),
        load_default="active"
    )
    
    created_by = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)


class ProjectDetailSchema(ProjectSchema):
    """Project detail schema with calculated metrics."""

    total_spent = fields.Decimal(dump_only=True, as_string=True, places=2)
    remaining_budget = fields.Decimal(dump_only=True, as_string=True, places=2)
    budget_utilization = fields.Float(dump_only=True)
    is_over_budget = fields.Bool(dump_only=True)
    days_elapsed = fields.Int(dump_only=True, allow_none=True)
    days_remaining = fields.Int(dump_only=True, allow_none=True)


class ProjectCreateSchema(Schema):
    """Schema for creating a new project."""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    starting_budget = fields.Decimal(required=True, as_string=True, places=2)
    projected_estimate = fields.Decimal(required=True, as_string=True, places=2)
    currency = fields.Str(validate=validate.Length(equal=3), load_default="USD")
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)
    status = fields.Str(
        validate=validate.OneOf(["active", "completed", "archived", "on_hold"]),
        load_default="active"
    )


class ProjectUpdateSchema(Schema):
    """Schema for updating a project."""

    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    starting_budget = fields.Decimal(as_string=True, places=2)
    projected_estimate = fields.Decimal(as_string=True, places=2)
    currency = fields.Str(validate=validate.Length(equal=3))
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)
    status = fields.Str(validate=validate.OneOf(["active", "completed", "archived", "on_hold"]))


class ProjectListQuerySchema(Schema):
    """Schema for project list query parameters."""

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    status = fields.Str(validate=validate.OneOf(["active", "completed", "archived", "on_hold"]))
    search = fields.Str()
    from_date = fields.Date()
    to_date = fields.Date()
    sort_by = fields.Str(validate=validate.OneOf(["name", "created_at", "start_date", "budget"]))
    sort_order = fields.Str(validate=validate.OneOf(["asc", "desc"]), load_default="desc")
