"""Request ID middleware for request tracing."""
import uuid

from flask import g, request


class RequestIdMiddleware:
    """
    Middleware to inject unique request IDs for tracing.
    
    Supports both generated UUIDs and client-provided X-Request-Id headers.
    """

    @staticmethod
    def add_request_id():
        """Add request ID to Flask g context."""
        # Use client-provided request ID if available, otherwise generate
        g.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))

    @staticmethod
    def inject_request_id_header(response):
        """Inject request ID into response headers."""
        if hasattr(g, "request_id"):
            response.headers["X-Request-Id"] = g.request_id
        return response
