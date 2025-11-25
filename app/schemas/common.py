"""Common schemas for API documentation."""
from marshmallow import Schema, fields


class ErrorResponseSchema(Schema):
    """Standard error response schema."""
    
    code = fields.String(required=True, metadata={"description": "Error code identifier"})
    message = fields.String(required=True, metadata={"description": "Human-readable error message"})
    errors = fields.Dict(
        keys=fields.String(),
        values=fields.List(fields.String()),
        metadata={"description": "Field-specific validation errors"}
    )
    details = fields.Dict(metadata={"description": "Additional error details"})


class ValidationErrorSchema(Schema):
    """Validation error response schema."""
    
    code = fields.String(
        required=True, 
        default="VALIDATION_ERROR",
        metadata={"description": "Error code"}
    )
    message = fields.String(
        required=True,
        metadata={"description": "Error message"}
    )
    errors = fields.Dict(
        required=True,
        keys=fields.String(),
        values=fields.List(fields.String()),
        metadata={"description": "Field-specific validation errors"}
    )


class UnauthorizedErrorSchema(Schema):
    """Unauthorized error response schema."""
    
    code = fields.String(
        required=True,
        default="UNAUTHORIZED",
        metadata={"description": "Error code"}
    )
    message = fields.String(
        required=True,
        default="Authentication required",
        metadata={"description": "Error message"}
    )


class ForbiddenErrorSchema(Schema):
    """Forbidden error response schema."""
    
    code = fields.String(
        required=True,
        default="FORBIDDEN",
        metadata={"description": "Error code"}
    )
    message = fields.String(
        required=True,
        default="Insufficient permissions",
        metadata={"description": "Error message"}
    )


class NotFoundErrorSchema(Schema):
    """Not found error response schema."""
    
    code = fields.String(
        required=True,
        default="NOT_FOUND",
        metadata={"description": "Error code"}
    )
    message = fields.String(
        required=True,
        default="Resource not found",
        metadata={"description": "Error message"}
    )


class ConflictErrorSchema(Schema):
    """Conflict error response schema."""
    
    code = fields.String(
        required=True,
        default="CONFLICT",
        metadata={"description": "Error code"}
    )
    message = fields.String(
        required=True,
        metadata={"description": "Error message"}
    )
    details = fields.Dict(metadata={"description": "Conflict details"})


class RateLimitErrorSchema(Schema):
    """Rate limit error response schema."""
    
    code = fields.String(
        required=True,
        default="RATE_LIMIT_EXCEEDED",
        metadata={"description": "Error code"}
    )
    message = fields.String(
        required=True,
        default="Too many requests",
        metadata={"description": "Error message"}
    )
    retry_after = fields.Integer(metadata={"description": "Seconds until retry allowed"})


class PaginationMetaSchema(Schema):
    """Pagination metadata schema."""
    
    page = fields.Integer(required=True, metadata={"description": "Current page number"})
    per_page = fields.Integer(required=True, metadata={"description": "Items per page"})
    total = fields.Integer(required=True, metadata={"description": "Total number of items"})
    pages = fields.Integer(required=True, metadata={"description": "Total number of pages"})
    has_next = fields.Boolean(required=True, metadata={"description": "Whether there is a next page"})
    has_prev = fields.Boolean(required=True, metadata={"description": "Whether there is a previous page"})
    next_page = fields.Integer(allow_none=True, metadata={"description": "Next page number"})
    prev_page = fields.Integer(allow_none=True, metadata={"description": "Previous page number"})


def PaginatedResponseSchema(item_schema):
    """
    Factory function to create paginated response schemas.
    
    Usage:
        ExpensePaginatedSchema = PaginatedResponseSchema(ExpenseSchema)
    """
    class _PaginatedResponseSchema(Schema):
        items = fields.List(fields.Nested(item_schema), required=True)
        meta = fields.Nested(PaginationMetaSchema, required=True)
    
    return _PaginatedResponseSchema


class HealthCheckSchema(Schema):
    """Health check response schema."""
    
    status = fields.String(
        required=True,
        metadata={"description": "Overall health status", "enum": ["healthy", "unhealthy"]}
    )
    database = fields.String(
        required=True,
        metadata={"description": "Database health status", "enum": ["healthy", "unhealthy"]}
    )
    redis = fields.String(
        required=True,
        metadata={"description": "Redis health status", "enum": ["healthy", "unhealthy"]}
    )
    version = fields.String(required=True, metadata={"description": "API version"})


class MessageResponseSchema(Schema):
    """Generic message response schema."""
    
    message = fields.String(required=True, metadata={"description": "Response message"})
    data = fields.Dict(metadata={"description": "Additional response data"})
