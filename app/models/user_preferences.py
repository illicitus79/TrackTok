"""User preferences model for notification settings."""
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.models.base import BaseModel


class UserPreferences(BaseModel):
    """
    User notification and display preferences.
    
    Stores per-user settings for notifications, email, and UI preferences.
    """

    __tablename__ = "user_preferences"

    # User relationship (one-to-one)
    user_id: Mapped[str] = mapped_column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Email notification preferences
    email_notifications_enabled: Mapped[bool] = mapped_column(
        db.Boolean, nullable=False, default=True
    )
    email_frequency: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default="instant"
    )  # instant, daily_digest, weekly_digest
    
    # Alert preferences
    notify_low_balance: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    notify_forecast_overspend: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    notify_budget_exceeded: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    notify_project_deadline: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    
    # Notification channels
    in_app_notifications: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    email_alerts: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    push_notifications: Mapped[bool] = mapped_column(
        db.Boolean, nullable=False, default=False
    )  # Future: web push or mobile
    
    # Digest preferences
    daily_summary_enabled: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    daily_summary_time: Mapped[Optional[str]] = mapped_column(
        db.String(5), nullable=True, default="09:00"
    )  # HH:MM format
    
    weekly_report_enabled: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    weekly_report_day: Mapped[Optional[str]] = mapped_column(
        db.String(10), nullable=True, default="monday"
    )  # Day of week
    
    # UI preferences
    theme: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default="dark"
    )  # dark, light, auto
    
    dashboard_layout: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    chart_preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timezone
    timezone: Mapped[str] = mapped_column(
        db.String(50), nullable=False, default="UTC"
    )
    
    # Language/locale
    locale: Mapped[str] = mapped_column(
        db.String(10), nullable=False, default="en_US"
    )
    
    # Additional custom settings
    custom_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="preferences_model")

    def __repr__(self):
        return f"<UserPreferences user_id={self.user_id}>"

    def should_send_email_for_alert(self, alert_type: str) -> bool:
        """
        Check if email should be sent for given alert type.
        
        Args:
            alert_type: Type of alert (LOW_BALANCE, FORECAST_OVERSPEND, etc.)
            
        Returns:
            True if email should be sent
        """
        if not self.email_notifications_enabled or not self.email_alerts:
            return False
        
        # Check specific alert type preferences
        if alert_type == "LOW_BALANCE" and not self.notify_low_balance:
            return False
        elif alert_type == "FORECAST_OVERSPEND" and not self.notify_forecast_overspend:
            return False
        elif alert_type == "BUDGET_EXCEEDED" and not self.notify_budget_exceeded:
            return False
        elif alert_type == "PROJECT_DEADLINE" and not self.notify_project_deadline:
            return False
        
        # Check frequency setting
        if self.email_frequency == "instant":
            return True
        else:
            # For digest modes, alerts are queued and sent in batches
            # The Celery task handles this
            return False
    
    def should_show_in_app(self, alert_type: str) -> bool:
        """
        Check if alert should be shown in-app.
        
        Args:
            alert_type: Type of alert
            
        Returns:
            True if alert should be shown in-app
        """
        return self.in_app_notifications
    
    @classmethod
    def get_or_create_for_user(cls, user_id: str) -> "UserPreferences":
        """
        Get or create preferences for user.
        
        Args:
            user_id: User ID
            
        Returns:
            UserPreferences instance
        """
        prefs = cls.query.filter_by(user_id=user_id).first()
        
        if not prefs:
            prefs = cls(user_id=user_id)
            db.session.add(prefs)
            db.session.commit()
        
        return prefs
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_notifications_enabled": self.email_notifications_enabled,
            "email_frequency": self.email_frequency,
            "notify_low_balance": self.notify_low_balance,
            "notify_forecast_overspend": self.notify_forecast_overspend,
            "notify_budget_exceeded": self.notify_budget_exceeded,
            "notify_project_deadline": self.notify_project_deadline,
            "in_app_notifications": self.in_app_notifications,
            "email_alerts": self.email_alerts,
            "push_notifications": self.push_notifications,
            "daily_summary_enabled": self.daily_summary_enabled,
            "daily_summary_time": self.daily_summary_time,
            "weekly_report_enabled": self.weekly_report_enabled,
            "weekly_report_day": self.weekly_report_day,
            "theme": self.theme,
            "timezone": self.timezone,
            "locale": self.locale,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
