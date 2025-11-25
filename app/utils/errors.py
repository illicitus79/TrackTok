"""Custom error classes and error handling utilities."""
from typing import Any, Dict, Optional

from flask import jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Base class for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize API error.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(APIError):
    """Validation error (400)."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR", details=details)


class AuthenticationError(APIError):
    """Authentication error (401)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401, error_code="AUTHENTICATION_ERROR")


class AuthorizationError(APIError):
    """Authorization error (403)."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403, error_code="AUTHORIZATION_ERROR")


class NotFoundError(APIError):
    """Resource not found error (404)."""

    def __init__(self, message: str = "Resource not found", resource: str = None):
        details = {"resource": resource} if resource else {}
        super().__init__(message, status_code=404, error_code="NOT_FOUND", details=details)


class ConflictError(APIError):
    """Conflict error (409)."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, status_code=409, error_code="CONFLICT", details=details)


class TenantError(APIError):
    """Tenant-related errors."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code=status_code, error_code="TENANT_ERROR")


class TenantRequiredError(TenantError):
    """Tenant context required but not provided."""

    def __init__(self):
        super().__init__(
            "Tenant context required. Provide via subdomain or X-Tenant-Id header.",
            status_code=400
        )


class TenantMismatchError(TenantError):
    """Cross-tenant access violation."""

    def __init__(self, message: str = "Cross-tenant access not allowed"):
        super().__init__(message, status_code=403)


class RateLimitError(APIError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED", details=details)


def register_error_handlers(app):
    """
    Register error handlers with Flask app.
    
    Args:
        app: Flask application instance
    """

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """Handle custom API errors."""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """Handle Werkzeug HTTP exceptions."""
        return jsonify({
            "error": error.name.upper().replace(" ", "_"),
            "message": error.description,
            "details": {}
        }), error.code

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors."""
        return jsonify({
            "error": "NOT_FOUND",
            "message": "The requested resource was not found",
            "details": {}
        }), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors."""
        from loguru import logger
        logger.error(f"Internal server error: {error}")
        
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "An internal server error occurred",
            "details": {}
        }), 500
