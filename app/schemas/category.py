"""Category schemas for request/response validation."""
from marshmallow import Schema, fields, validate


class CategorySchema(Schema):
    """Category schema for serialization/deserialization."""

    id = fields.Str(dump_only=True)
    tenant_id = fields.Str(dump_only=True)
    
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    color = fields.Str(
        required=True,
        validate=validate.Regexp(r'^#[0-9A-Fa-f]{6}$', error="Must be valid hex color (e.g., #6366F1)")
    )
    description = fields.Str(allow_none=True)
    icon = fields.Str(validate=validate.Length(max=10), allow_none=True)
    
    is_active = fields.Bool(load_default=True)
    
    created_by = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)


class CategoryDetailSchema(CategorySchema):
    """Category detail schema with metrics."""

    total_expenses = fields.Int(dump_only=True)
    total_amount = fields.Float(dump_only=True)


class CategoryCreateSchema(Schema):
    """Schema for creating a new category."""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    color = fields.Str(
        required=True,
        validate=validate.Regexp(r'^#[0-9A-Fa-f]{6}$', error="Must be valid hex color")
    )
    description = fields.Str(allow_none=True)
    icon = fields.Str(validate=validate.Length(max=10), allow_none=True)


class CategoryUpdateSchema(Schema):
    """Schema for updating a category."""

    name = fields.Str(validate=validate.Length(min=1, max=100))
    color = fields.Str(
        validate=validate.Regexp(r'^#[0-9A-Fa-f]{6}$', error="Must be valid hex color")
    )
    description = fields.Str(allow_none=True)
    icon = fields.Str(validate=validate.Length(max=10), allow_none=True)
    is_active = fields.Bool()


class CategoryListQuerySchema(Schema):
    """Schema for category list query parameters."""

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    is_active = fields.Bool()
    search = fields.Str()
    sort_by = fields.Str(validate=validate.OneOf(["name", "created_at"]))
    sort_order = fields.Str(validate=validate.OneOf(["asc", "desc"]), load_default="asc")
