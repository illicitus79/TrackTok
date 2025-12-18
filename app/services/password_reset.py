"""Password reset service helpers."""
from datetime import datetime
from typing import Optional, Tuple

from flask import current_app, g, render_template, url_for
from flask_mail import Message
from loguru import logger

from app.core.extensions import db, mail
from app.core.security import generate_password_reset_token, verify_password_reset_token
from app.models.audit import AuditAction, AuditLog
from app.models.user import PasswordResetToken, User


def _build_reset_url(token: str) -> str:
    """Build absolute URL for password reset."""
    try:
        return url_for("web.reset_password", token=token, _external=True)
    except Exception:
        # Fallback to relative path if URL building fails (should not happen in request context)
        return f"/reset-password/{token}"


def _log_action(user: User, action: AuditAction) -> None:
    """Log audit action with tenant context when available."""
    try:
        if not getattr(g, "tenant_id", None):
            g.tenant_id = user.tenant_id
        if not getattr(g, "user_id", None):
            g.user_id = user.id
        AuditLog.log_action(action=action, entity_type="user", entity_id=user.id)
    except Exception as exc:
        logger.warning(f"Failed to log audit for password event: {exc}")


def _invalidate_existing_tokens(user_id: str) -> None:
    """Mark existing active tokens as used."""
    try:
        db.session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.is_deleted.is_(False),
        ).update({"used_at": datetime.utcnow()})
        db.session.commit()
    except Exception as exc:
        logger.warning(f"Could not invalidate existing reset tokens: {exc}")
        db.session.rollback()


def send_password_reset_email(user: User, reset_url: str) -> bool:
    """Send the password reset email with branding."""
    if not current_app.config.get("ENABLE_EMAIL_NOTIFICATIONS", True):
        logger.info("Email notifications disabled; skipping password reset email.")
        return False

    try:
        html_body = render_template(
            "emails/password_reset.html",
            user=user,
            reset_url=reset_url,
        )
        text_body = render_template(
            "emails/password_reset.txt",
            user=user,
            reset_url=reset_url,
        )

        msg = Message(
            subject="Reset your TrackTok password",
            recipients=[user.email],
            html=html_body,
            body=text_body,
        )
        mail.send(msg)
        return True
    except Exception as exc:
        logger.error(f"Failed to send password reset email: {exc}")
        return False


def send_password_reset_confirmation_email(user: User) -> bool:
    """Send confirmation email after successful password reset."""
    if not current_app.config.get("ENABLE_EMAIL_NOTIFICATIONS", True):
        logger.info("Email notifications disabled; skipping password reset confirmation email.")
        return False

    try:
        html_body = render_template("emails/password_reset_confirmation.html", user=user)
        text_body = render_template("emails/password_reset_confirmation.txt", user=user)

        msg = Message(
            subject="Your TrackTok password was reset",
            recipients=[user.email],
            html=html_body,
            body=text_body,
        )
        mail.send(msg)
        return True
    except Exception as exc:
        logger.error(f"Failed to send password reset confirmation email: {exc}")
        return False


def request_password_reset(user: User) -> Optional[str]:
    """
    Issue a password reset token and send the reset email.

    Returns token if created, otherwise None.
    """
    if not user or getattr(user, "is_deleted", False):
        return None

    _invalidate_existing_tokens(user.id)
    token = generate_password_reset_token(user)
    reset_url = _build_reset_url(token)
    send_password_reset_email(user, reset_url)
    _log_action(user, AuditAction.PASSWORD_RESET_REQUEST)
    return token


def complete_password_reset(
    token: str, new_password: str, expected_tenant_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Complete password reset using token.

    Returns tuple of success flag and message.
    """
    try:
        reset_token = verify_password_reset_token(token)
        if not reset_token:
            return False, "Invalid or expired token."

        user = (
            db.session.query(User)
            .filter_by(id=reset_token.user_id, is_deleted=False)
            .first()
        )
        if not user or not user.is_active:
            return False, "Invalid or expired token."

        if expected_tenant_id and user.tenant_id != expected_tenant_id:
            return False, "Invalid or expired token."

        # Ensure tenant context for audit logging
        if not getattr(g, "tenant_id", None):
            g.tenant_id = user.tenant_id
        g.user_id = user.id

        user.set_password(new_password)
        reset_token.mark_used(commit=False)

        # Invalidate any other outstanding tokens
        db.session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.id != reset_token.id,
        ).update({"used_at": datetime.utcnow()})

        db.session.commit()

        _log_action(user, AuditAction.PASSWORD_RESET)
        send_password_reset_confirmation_email(user)
        return True, "Password has been reset."
    except Exception as exc:
        logger.error(f"Error completing password reset: {exc}")
        db.session.rollback()
        return False, "Unable to reset password at this time."
