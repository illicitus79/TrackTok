"""Tenancy middleware for multi-tenant request resolution."""
from typing import Optional

from flask import current_app, g, request
from loguru import logger

from app.core.extensions import db


class TenancyMiddleware:
    """
    Middleware to resolve and enforce tenant context.
    
    Supports multiple tenant resolution strategies:
    - Subdomain-based (e.g., acme.tracktok.com)
    - Header-based (X-Tenant-Id)
    - Custom domain mapping
    """

    @staticmethod
    def resolve_tenant():
        """
        Resolve tenant from request and set in context.
        
        Resolution order:
        1. Custom domain mapping (if enabled)
        2. Subdomain extraction
        3. X-Tenant-Id header (fallback)
        """
        # Skip tenant resolution for health check and auth endpoints
        if request.path in ["/api/v1/health", "/api/v1/auth/login", "/api/v1/auth/register"]:
            return

        tenant_id = None
        resolution_method = current_app.config.get("TENANT_RESOLUTION", "subdomain")

        if resolution_method == "subdomain":
            tenant_id = TenancyMiddleware._resolve_from_subdomain()
        elif resolution_method == "header":
            tenant_id = TenancyMiddleware._resolve_from_header()
        elif resolution_method == "custom_domain":
            tenant_id = TenancyMiddleware._resolve_from_custom_domain()

        # Fallback to header if subdomain resolution fails
        if not tenant_id and resolution_method != "header":
            tenant_id = TenancyMiddleware._resolve_from_header()

        # Final fallback: use logged-in user's tenant (for server-rendered pages)
        try:
            from flask_login import current_user

            if not tenant_id and current_user and getattr(current_user, "is_authenticated", False):
                tenant_id = getattr(current_user, "tenant_id", None)
        except Exception:
            pass

        if tenant_id:
            g.tenant_id = tenant_id
            logger.debug(f"Tenant resolved: {tenant_id}", method=resolution_method)
        else:
            # For API endpoints, tenant is required
            if request.path.startswith("/api/v1/") and request.path not in [
                "/api/v1/health",
                "/api/v1/auth/login",
                "/api/v1/auth/register",
            ]:
                logger.warning("Tenant not resolved for API request", path=request.path)
                # Allow request to proceed - will be caught by endpoint-level checks

    @staticmethod
    def _resolve_from_subdomain() -> Optional[str]:
        """
        Extract tenant from subdomain.
        
        Example: acme.tracktok.com -> acme
        """
        host = request.host.lower()
        base_domain = current_app.config.get("BASE_DOMAIN", "localhost:5000").lower()

        # Remove port from host if present
        host_without_port = host.split(":")[0]
        base_without_port = base_domain.split(":")[0]

        # Extract subdomain
        if host_without_port.endswith(f".{base_without_port}"):
            subdomain = host_without_port.replace(f".{base_without_port}", "")
            return TenancyMiddleware._get_tenant_id_by_subdomain(subdomain)

        # Handle localhost development (e.g., acme.localhost)
        if "localhost" in host_without_port and "." in host_without_port:
            subdomain = host_without_port.split(".")[0]
            if subdomain != "localhost":
                return TenancyMiddleware._get_tenant_id_by_subdomain(subdomain)

        return None

    @staticmethod
    def _resolve_from_header() -> Optional[str]:
        """Extract tenant from X-Tenant-Id header."""
        tenant_header = current_app.config.get("TENANT_HEADER", "X-Tenant-Id")
        return request.headers.get(tenant_header)

    @staticmethod
    def _resolve_from_custom_domain() -> Optional[str]:
        """
        Resolve tenant from custom domain mapping.
        
        Example: expenses.acmecorp.com -> acme tenant
        """
        if not current_app.config.get("ENABLE_CUSTOM_DOMAINS"):
            return None

        host = request.host.lower().split(":")[0]

        # Query custom domain mapping
        try:
            from app.models.tenant import TenantDomain

            domain = db.session.query(TenantDomain).filter_by(domain=host, is_active=True).first()
            if domain:
                return domain.tenant_id
        except Exception as e:
            logger.error(f"Error resolving custom domain: {e}")

        return None

    @staticmethod
    def _get_tenant_id_by_subdomain(subdomain: str) -> Optional[str]:
        """
        Look up tenant ID by subdomain.
        
        Args:
            subdomain: Subdomain string (e.g., 'acme')
            
        Returns:
            Tenant ID if found, None otherwise
        """
        try:
            from app.models.tenant import Tenant

            tenant = db.session.query(Tenant).filter_by(subdomain=subdomain, is_active=True).first()
            return tenant.id if tenant else None
        except Exception as e:
            logger.error(f"Error looking up tenant by subdomain: {e}")
            return None

    @staticmethod
    def require_tenant():
        """
        Decorator to enforce tenant context on endpoints.
        
        Usage:
            @bp.route('/expenses')
            @TenancyMiddleware.require_tenant()
            def get_expenses():
                # g.tenant_id is guaranteed to exist
                pass
        """

        def decorator(f):
            from functools import wraps

            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not hasattr(g, "tenant_id") or not g.tenant_id:
                    from flask import jsonify

                    return (
                        jsonify(
                            {
                                "error": "Tenant context required",
                                "code": "TENANT_REQUIRED",
                                "message": "Please provide tenant via subdomain or X-Tenant-Id header",
                            }
                        ),
                        400,
                    )
                return f(*args, **kwargs)

            return decorated_function

        return decorator
