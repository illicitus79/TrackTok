"""User and authentication models."""
from datetime import datetime
from enum import Enum

import bcrypt
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.core.tenancy import TenantMixin
from app.models.base import BaseModel


class UserRole(str, Enum):
    """User roles for RBAC."""

    OWNER = "owner"  # Full control, billing
    ADMIN = "admin"  # Manage users, all expenses
    ANALYST = "analyst"  # Read-only access, reports
    MEMBER = "member"  # Manage own expenses


class User(BaseModel, TenantMixin):
    """
    User model with authentication and RBAC.
    
    Users are scoped to tenants and have role-based permissions.
    """

    __tablename__ = "users"

    # Identity
    email: Mapped[str] = mapped_column(db.String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    
    # Profile
    first_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    avatar_url: Mapped[str] = mapped_column(db.String(512), nullable=True)
    
    # Role & Permissions
    role: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default=UserRole.MEMBER.value, index=True
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # Login tracking
    last_login_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    login_count: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)
    
    # Preferences
    preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    budgets = relationship("Budget", back_populates="owner", foreign_keys="Budget.owner_id")
    preferences_model = relationship(
        "UserPreferences", 
        back_populates="user", 
        uselist=False, 
        cascade="all, delete-orphan"
    )

    # Unique constraint: email must be unique within tenant
    __table_args__ = (db.UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

    def set_password(self, password: str):
        """Hash and set user password."""
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    def update_login(self):
        """Update login tracking fields."""
        self.last_login_at = datetime.utcnow()
        self.login_count += 1
        db.session.commit()

    def has_permission(self, required_role: UserRole) -> bool:
        """
        Check if user has required permission level.
        
        Role hierarchy: OWNER > ADMIN > ANALYST > MEMBER
        """
        role_hierarchy = {
            UserRole.OWNER: 4,
            UserRole.ADMIN: 3,
            UserRole.ANALYST: 2,
            UserRole.MEMBER: 1,
        }
        user_level = role_hierarchy.get(UserRole(self.role), 0)
        required_level = role_hierarchy.get(required_role, 0)
        return user_level >= required_level

    def can_manage_expenses(self, expense_user_id: str = None) -> bool:
        """Check if user can manage expenses (own or all)."""
        if self.role in [UserRole.OWNER.value, UserRole.ADMIN.value]:
            return True
        return expense_user_id == self.id if expense_user_id else False

    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.role in [UserRole.OWNER.value, UserRole.ADMIN.value]

    def can_view_reports(self) -> bool:
        """Check if user can view reports."""
        return True  # All users can view reports

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    # Flask-Login integration methods
    @property
    def is_authenticated(self) -> bool:
        """Return True if user is authenticated."""
        return True

    @property
    def is_active_user(self) -> bool:
        """Return True if user account is active."""
        return self.is_active

    @property
    def is_anonymous(self) -> bool:
        """Return False as this is not an anonymous user."""
        return False

    def get_id(self) -> str:
        """Return user ID as string for Flask-Login."""
        return str(self.id)


class PasswordResetToken(BaseModel):
    """Password reset tokens for account recovery."""

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False)
    used_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.used_at and datetime.utcnow() < self.expires_at

    def mark_used(self, commit: bool = True):
        """Mark token as used."""
        self.used_at = datetime.utcnow()
        if commit:
            db.session.commit()
