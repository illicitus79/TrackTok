"""Tenant schemas for API validation and serialization."""
from marshmallow import Schema, ValidationError, fields, validates, validates_schema


class TenantSchema(Schema):
    """Schema for tenant data."""

    id = fields.Str(dump_only=True)
    name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 255)
    subdomain = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 63)
    settings = fields.Dict(missing=dict)
    plan = fields.Str(dump_only=True)
    max_users = fields.Int(dump_only=True)
    max_expenses = fields.Int(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates("subdomain")
    def validate_subdomain(self, value):
        """Validate subdomain format."""
        import re

        if not re.match(r"^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$", value):
            raise ValidationError(
                "Subdomain must contain only lowercase letters, numbers, and hyphens"
            )


class TenantCreateSchema(Schema):
    """Schema for creating a new tenant."""

    name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 255)
    subdomain = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 63)
    owner_email = fields.Email(required=True)
    owner_password = fields.Str(required=True, load_only=True, validate=lambda x: len(x) >= 8)
    owner_first_name = fields.Str(required=True)
    owner_last_name = fields.Str(required=True)

    @validates("owner_password")
    def validate_password(self, value):
        """Validate password strength."""
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in value):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValidationError("Password must contain at least one number")


class TenantUpdateSchema(Schema):
    """Schema for updating tenant settings."""

    name = fields.Str(validate=lambda x: 1 <= len(x) <= 255)
    settings = fields.Dict()


class TenantDomainSchema(Schema):
    """Schema for custom domain."""

    id = fields.Str(dump_only=True)
    domain = fields.Str(required=True)
    is_verified = fields.Bool(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    verified_at = fields.DateTime(dump_only=True)
    verification_token = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
