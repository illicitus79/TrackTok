"""Utility decorators for RBAC and common functionality."""
from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from loguru import logger

from app.models.user import UserRole


def roles_required(*allowed_roles):
    """
    Decorator to enforce role-based access control.
    
    Args:
        *allowed_roles: Variable number of allowed roles (Owner, Admin, Analyst, Member)
        
    Usage:
        @roles_required('Owner', 'Admin')
        def admin_endpoint():
            pass
            
        @roles_required('Owner')  # Owner only
        def owner_endpoint():
            pass
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Ensure JWT is verified first
            verify_jwt_in_request()
            
            # Get JWT claims
            claims = get_jwt()
            user_role = claims.get('role')
            
            # Set context
            g.user_id = claims.get('sub')
            g.tenant_id = claims.get('tenant_id')
            g.user_role = user_role
            
            if not user_role:
                return (
                    jsonify(
                        {
                            "error": "Authentication required",
                            "code": "AUTHENTICATION_REQUIRED",
                        }
                    ),
                    401,
                )
            
            # Check if user has one of the allowed roles
            role_hierarchy = {
                'Owner': 4,
                'Admin': 3,
                'Analyst': 2,
                'Member': 1,
            }
            
            user_level = role_hierarchy.get(user_role, 0)
            max_allowed_level = max(role_hierarchy.get(role, 0) for role in allowed_roles)
            
            if user_level < max_allowed_level:
                logger.warning(
                    f"Insufficient permissions",
                    user_id=g.get("user_id"),
                    user_role=user_role,
                    required_roles=allowed_roles,
                )
                return (
                    jsonify(
                        {
                            "error": "Insufficient permissions",
                            "code": "FORBIDDEN",
                            "required_roles": list(allowed_roles),
                            "your_role": user_role,
                        }
                    ),
                    403,
                )
            
            return fn(*args, **kwargs)
        
        return wrapper
    
    return decorator


def jwt_required_with_tenant(fn):
    """
    Decorator combining JWT authentication with tenant context.
    
    Verifies JWT token and sets user/tenant context in g.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Verify JWT token
        verify_jwt_in_request()

        # Get JWT claims
        claims = get_jwt()

        # Set context
        g.user_id = claims.get("sub")  # 'sub' is the identity
        g.tenant_id = claims.get("tenant_id")
        g.user_role = claims.get("role")

        return fn(*args, **kwargs)

    return wrapper


def require_role(required_role: UserRole):
    """
    Decorator to enforce role-based access control.
    
    Args:
        required_role: Minimum required role
        
    Usage:
        @require_role(UserRole.ADMIN)
        def admin_only_endpoint():
            pass
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Ensure JWT is verified first
            if not hasattr(g, "user_role"):
                return (
                    jsonify(
                        {
                            "error": "Authentication required",
                            "code": "AUTHENTICATION_REQUIRED",
                        }
                    ),
                    401,
                )

            # Check role hierarchy
            role_hierarchy = {
                UserRole.OWNER: 4,
                UserRole.ADMIN: 3,
                UserRole.ANALYST: 2,
                UserRole.MEMBER: 1,
            }

            user_level = role_hierarchy.get(UserRole(g.user_role), 0)
            required_level = role_hierarchy.get(required_role, 0)

            if user_level < required_level:
                logger.warning(
                    f"Insufficient permissions",
                    user_id=g.get("user_id"),
                    user_role=g.user_role,
                    required_role=required_role.value,
                )
                return (
                    jsonify(
                        {
                            "error": "Insufficient permissions",
                            "code": "FORBIDDEN",
                            "required_role": required_role.value,
                        }
                    ),
                    403,
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def owner_or_admin_required(fn):
    """Shortcut decorator for owner or admin access."""
    return require_role(UserRole.ADMIN)(fn)


def owner_only(fn):
    """Shortcut decorator for owner-only access."""
    return require_role(UserRole.OWNER)(fn)


def tenant_required(fn):
    """
    Decorator to ensure tenant context exists.
    
    Should be used after jwt_required_with_tenant.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not hasattr(g, "tenant_id") or not g.tenant_id:
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
        return fn(*args, **kwargs)

    return wrapper


def check_resource_ownership(resource_user_id: str = None):
    """
    Decorator to check if user owns resource or has admin privileges.
    
    Args:
        resource_user_id: ID of user who owns the resource
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = g.get("user_id")
            user_role = g.get("user_role")

            # Admins and owners can access any resource
            if user_role in [UserRole.OWNER.value, UserRole.ADMIN.value]:
                return fn(*args, **kwargs)

            # Regular users can only access their own resources
            if resource_user_id and resource_user_id != user_id:
                return (
                    jsonify(
                        {
                            "error": "Access denied",
                            "code": "FORBIDDEN",
                            "message": "You can only access your own resources",
                        }
                    ),
                    403,
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def validate_tenant_access(fn):
    """
    Decorator to validate user belongs to the tenant in context.
    
    Prevents cross-tenant access attempts.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        from app.core.extensions import db
        from app.models.user import User

        user_id = g.get("user_id")
        tenant_id = g.get("tenant_id")

        if not user_id or not tenant_id:
            return (
                jsonify(
                    {
                        "error": "Invalid context",
                        "code": "INVALID_CONTEXT",
                    }
                ),
                400,
            )

        # Verify user belongs to tenant
        user = db.session.query(User).filter_by(id=user_id, tenant_id=tenant_id).first()

        if not user:
            logger.warning(
                f"Cross-tenant access attempt",
                user_id=user_id,
                requested_tenant=tenant_id,
            )
            return (
                jsonify(
                    {
                        "error": "Access denied",
                        "code": "FORBIDDEN",
                        "message": "You do not have access to this tenant",
                    }
                ),
                403,
            )

        return fn(*args, **kwargs)

    return wrapper


def log_api_call(fn):
    """Decorator to log API calls for audit purposes."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask import request

        logger.info(
            f"API call",
            endpoint=request.endpoint,
            method=request.method,
            path=request.path,
            user_id=g.get("user_id"),
            tenant_id=g.get("tenant_id"),
        )

        result = fn(*args, **kwargs)

        logger.info(
            f"API response",
            endpoint=request.endpoint,
            status_code=result[1] if isinstance(result, tuple) else 200,
            user_id=g.get("user_id"),
        )

        return result

    return wrapper
