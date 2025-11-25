"""Alert model for notifications and warnings."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.models.base import BaseModel


class AlertType(str, Enum):
    """Alert types."""
    
    LOW_BALANCE = "low_balance"
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_WARNING = "budget_warning"
    FORECAST_OVERSPEND = "forecast_overspend"
    EXPENSE_REJECTED = "expense_rejected"
    EXPENSE_APPROVED = "expense_approved"
    UNUSUAL_SPENDING = "unusual_spending"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert(BaseModel):
    """
    Alert model for notifications.
    
    Tracks low balance alerts, budget warnings, etc.
    """

    __tablename__ = "alerts"

    # Tenant relationship
    tenant_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Alert type and severity
    alert_type: Mapped[str] = mapped_column(
        db.String(50), nullable=False, index=True
    )  # LOW_BALANCE, FORECAST_OVERSPEND, BUDGET_EXCEEDED, etc.
    
    severity: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default="warning"
    )  # info, warning, error, critical
    
    # Entity reference
    entity_type: Mapped[str] = mapped_column(db.String(50), nullable=False)  # account, project, budget
    entity_id: Mapped[str] = mapped_column(db.String(36), nullable=False, index=True)
    
    # Alert content
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    message: Mapped[str] = mapped_column(db.Text, nullable=False)
    
    # Additional data (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    alert_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Status
    is_read: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True)
    read_by: Mapped[Optional[str]] = mapped_column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    
    is_dismissed: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True)
    
    # Notification sent
    notification_sent: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    notification_sent_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="alerts")
    reader = relationship("User", foreign_keys=[read_by])

    # Indexes
    __table_args__ = (
        db.Index("ix_alerts_tenant_type", "tenant_id", "alert_type"),
        db.Index("ix_alerts_tenant_unread", "tenant_id", "is_read"),
        db.Index("ix_alerts_entity", "entity_type", "entity_id"),
    )

    def __repr__(self):
        return f"<Alert {self.alert_type} - {self.severity}>"

    def mark_as_read(self, user_id: Optional[str] = None, commit: bool = True) -> None:
        """
        Mark alert as read.
        
        Args:
            user_id: ID of user who read the alert
            commit: Whether to commit transaction
        """
        self.is_read = True
        self.read_at = datetime.utcnow()
        if user_id:
            self.read_by = user_id
        if commit:
            db.session.commit()

    def dismiss(self, commit: bool = True) -> None:
        """
        Dismiss alert.
        
        Args:
            commit: Whether to commit transaction
        """
        self.is_dismissed = True
        self.dismissed_at = datetime.utcnow()
        if commit:
            db.session.commit()

    def mark_notification_sent(self, commit: bool = True) -> None:
        """
        Mark that notification was sent.
        
        Args:
            commit: Whether to commit transaction
        """
        self.notification_sent = True
        self.notification_sent_at = datetime.utcnow()
        if commit:
            db.session.commit()

    @classmethod
    def get_unread_count(cls, tenant_id: str) -> int:
        """Get count of unread alerts for tenant."""
        return db.session.query(cls).filter_by(
            tenant_id=tenant_id,
            is_read=False,
            is_deleted=False
        ).count()

    @classmethod
    def get_recent_alerts(cls, tenant_id: str, limit: int = 10):
        """Get recent alerts for tenant."""
        return db.session.query(cls).filter_by(
            tenant_id=tenant_id,
            is_deleted=False
        ).order_by(cls.created_at.desc()).limit(limit).all()

    def to_dict(self):
        """Convert to dictionary."""
        data = super().to_dict()
        return data
