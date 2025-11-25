"""Security utilities for authentication and authorization."""
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

import bcrypt
from flask import g, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity
from loguru import logger

from app.models.user import User, UserRole


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Hashed password to check against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def generate_tokens(user: User) -> dict:
    """
    Generate JWT access and refresh tokens for user.
    
    Args:
        user: User instance
        
    Returns:
        Dictionary with access_token and refresh_token
    """
    additional_claims = {
        "tenant_id": user.tenant_id,
        "role": user.role,
        "email": user.email,
    }

    access_token = create_access_token(identity=user.id, additional_claims=additional_claims)

    refresh_token = create_refresh_token(identity=user.id, additional_claims=additional_claims)

    return {"access_token": access_token, "refresh_token": refresh_token}


def get_current_user() -> Optional[User]:
    """
    Get current authenticated user from JWT token.
    
    Returns:
        User instance if authenticated, None otherwise
    """
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return None

        from app.core.extensions import db

        user = db.session.query(User).filter_by(id=user_id, is_active=True).first()

        if user:
            # Set user context
            g.user_id = user.id
            g.tenant_id = user.tenant_id

        return user
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None


def generate_password_reset_token(user: User) -> str:
    """
    Generate password reset token.
    
    Args:
        user: User instance
        
    Returns:
        Reset token string
    """
    import secrets

    from app.core.extensions import db
    from app.models.user import PasswordResetToken

    token = secrets.token_urlsafe(32)

    reset_token = PasswordResetToken(
        user_id=user.id, token=token, expires_at=datetime.utcnow() + timedelta(hours=24)
    )

    db.session.add(reset_token)
    db.session.commit()

    return token


def verify_password_reset_token(token: str) -> Optional[User]:
    """
    Verify password reset token and return associated user.
    
    Args:
        token: Reset token string
        
    Returns:
        User instance if token is valid, None otherwise
    """
    from app.core.extensions import db
    from app.models.user import PasswordResetToken

    reset_token = (
        db.session.query(PasswordResetToken).filter_by(token=token, used_at=None).first()
    )

    if not reset_token or not reset_token.is_valid():
        return None

    user = db.session.query(User).filter_by(id=reset_token.user_id).first()

    return user


def check_rate_limit(user_id: str, action: str, limit: int, window: int = 3600) -> bool:
    """
    Check if user has exceeded rate limit for action.
    
    Args:
        user_id: User ID
        action: Action identifier (e.g., 'login_attempt')
        limit: Maximum allowed actions
        window: Time window in seconds
        
    Returns:
        True if within limit, False if exceeded
    """
    from flask import current_app

    redis_client = current_app.redis
    key = f"ratelimit:{user_id}:{action}"

    try:
        count = redis_client.get(key)
        if count and int(count) >= limit:
            return False

        # Increment counter
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        pipe.execute()

        return True
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        return True  # Fail open


def sanitize_input(data: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        data: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not data:
        return ""

    # Truncate to max length
    data = data[:max_length]

    # Remove null bytes
    data = data.replace("\x00", "")

    # Strip leading/trailing whitespace
    data = data.strip()

    return data
