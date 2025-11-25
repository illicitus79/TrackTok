"""User schemas for API validation and serialization."""
from marshmallow import Schema, ValidationError, fields, validates


class UserSchema(Schema):
    """Schema for user data."""

    id = fields.Str(dump_only=True)
    email = fields.Email(required=True)
    first_name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 100)
    last_name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 100)
    avatar_url = fields.Str(allow_none=True)
    role = fields.Str(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    is_verified = fields.Bool(dump_only=True)
    last_login_at = fields.DateTime(dump_only=True)
    preferences = fields.Dict(missing=dict)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class UserCreateSchema(Schema):
    """Schema for creating a new user."""

    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True, validate=lambda x: len(x) >= 8)
    first_name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 100)
    last_name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 100)
    role = fields.Str(
        missing="member",
        validate=lambda x: x in ["owner", "admin", "analyst", "member"],
    )

    @validates("password")
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


class UserUpdateSchema(Schema):
    """Schema for updating user profile."""

    first_name = fields.Str(validate=lambda x: 1 <= len(x) <= 100)
    last_name = fields.Str(validate=lambda x: 1 <= len(x) <= 100)
    avatar_url = fields.Str(allow_none=True)
    preferences = fields.Dict()


class UserRoleUpdateSchema(Schema):
    """Schema for updating user role (admin only)."""

    role = fields.Str(
        required=True,
        validate=lambda x: x in ["owner", "admin", "analyst", "member"],
    )


class LoginSchema(Schema):
    """Schema for login credentials."""

    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)


class PasswordChangeSchema(Schema):
    """Schema for password change."""

    current_password = fields.Str(required=True, load_only=True)
    new_password = fields.Str(required=True, load_only=True, validate=lambda x: len(x) >= 8)

    @validates("new_password")
    def validate_new_password(self, value):
        """Validate new password strength."""
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in value):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValidationError("Password must contain at least one number")


class PasswordResetRequestSchema(Schema):
    """Schema for password reset request."""

    email = fields.Email(required=True)


class PasswordResetSchema(Schema):
    """Schema for password reset with token."""

    token = fields.Str(required=True)
    new_password = fields.Str(required=True, load_only=True, validate=lambda x: len(x) >= 8)

    @validates("new_password")
    def validate_new_password(self, value):
        """Validate new password strength."""
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters long")
