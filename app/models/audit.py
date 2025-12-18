"""Audit log model for immutable audit trail."""
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.core.tenancy import TenantMixin
from app.models.base import TimestampMixin


class AuditAction(str, Enum):
    """Audit action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET = "password_reset"
    USER_INVITED = "user_invited"
    ROLE_CHANGE = "role_change"
    APPROVE = "approve"
    REJECT = "reject"


class AuditLog(db.Model, TimestampMixin, TenantMixin):
    """
    Immutable audit log for compliance and tracking.
    
    Records all financial operations and sensitive actions.
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(db.String(36), primary_key=True)
    
    # Actor (actor_user_id as per spec, keeping user_id for compatibility)
    actor_user_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("users.id"), nullable=True, index=True
    )
    user_email: Mapped[str] = mapped_column(db.String(255), nullable=True)  # Denormalized
    
    # Action details
    action: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)  # resource_type alias
    entity_id: Mapped[str] = mapped_column(db.String(36), nullable=True, index=True)  # resource_id alias
    
    # Changes (changes_json as per spec - for UPDATE actions)
    changes_json: Mapped[dict] = mapped_column(JSON, nullable=True)  # Combined old+new values
    
    # Request context
    ip_address: Mapped[str] = mapped_column(db.String(45), nullable=True)  # IPv6 support
    user_agent: Mapped[str] = mapped_column(db.String(512), nullable=True)
    request_id: Mapped[str] = mapped_column(db.String(36), nullable=True, index=True)
    
    # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    audit_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Relationships
    tenant = relationship("Tenant")

    __table_args__ = (
        db.Index("idx_tenant_action", "tenant_id", "action"),
        db.Index("idx_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        db.Index("idx_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.entity_type}>"
    
    # Properties for backward compatibility
    @property
    def user_id(self):
        """Alias for actor_user_id."""
        return self.actor_user_id
    
    @property
    def resource_type(self):
        """Alias for entity_type."""
        return self.entity_type
    
    @property
    def resource_id(self):
        """Alias for entity_id."""
        return self.entity_id

    @staticmethod
    def log_action(
        action: AuditAction,
        entity_type: str,
        entity_id: str = None,
        old_values: dict = None,
        new_values: dict = None,
        metadata: dict = None,
    ):
        """
        Create an audit log entry.
        
        Args:
            action: Action performed
            entity_type: Type of entity (expense, budget, user, etc.)
            entity_id: ID of affected entity
            old_values: Previous values (for updates)
            new_values: New values (for updates)
            metadata: Additional context
        """
        from flask import g, request

        from app.models.user import User

        import uuid

        user_id = g.get("user_id")
        tenant_id = g.get("tenant_id")

        # Get user email if user_id is available
        user_email = None
        if user_id:
            user = db.session.query(User).filter_by(id=user_id).first()
            user_email = user.email if user else None

        # Combine old and new values for changes_json
        changes_json = None
        if old_values or new_values:
            changes_json = {
                "old": old_values or {},
                "new": new_values or {}
            }

        audit_entry = AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            actor_user_id=user_id,
            user_email=user_email,
            action=action.value,
            entity_type=entity_type,
            entity_id=entity_id,
            changes_json=changes_json,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
            request_id=g.get("request_id"),
            metadata=metadata or {},
            created_at=datetime.utcnow(),
        )

        db.session.add(audit_entry)
        db.session.commit()

        return audit_entry

    @classmethod
    def get_resource_history(cls, entity_type: str, entity_id: str):
        """Get complete audit history for an entity."""
        return (
            db.session.query(cls)
            .filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(cls.created_at.desc())
            .all()
        )

    @classmethod
    def get_user_activity(cls, user_id: str, limit: int = 100):
        """Get recent activity for a user."""
        return (
            db.session.query(cls)
            .filter_by(actor_user_id=user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .all()
        )
