"""Tenant models for multi-tenancy support."""
from datetime import datetime

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.models.base import BaseModel


class Tenant(BaseModel):
    """
    Tenant model for multi-tenant architecture.
    
    Each tenant represents an isolated organization using the platform.
    """

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    subdomain: Mapped[str] = mapped_column(db.String(63), unique=True, nullable=False, index=True)
    
    # Settings stored as JSON
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Plan and limits
    plan: Mapped[str] = mapped_column(
        db.String(50), nullable=False, default="free"
    )  # free, pro, enterprise
    max_users: Mapped[int] = mapped_column(db.Integer, nullable=False, default=5)
    max_expenses: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1000)
    
    # Status
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False, index=True)
    suspended_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    suspension_reason: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="tenant", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="tenant", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="tenant", cascade="all, delete-orphan")
    custom_domains = relationship("TenantDomain", back_populates="tenant", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="tenant", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="tenant", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.name} ({self.subdomain})>"

    def is_within_limits(self, resource_type: str) -> bool:
        """
        Check if tenant is within resource limits.
        
        Args:
            resource_type: 'users' or 'expenses'
        """
        if resource_type == "users":
            return len(self.users) < self.max_users
        elif resource_type == "expenses":
            return len(self.expenses) < self.max_expenses
        return True

    def suspend(self, reason: str):
        """Suspend tenant account."""
        self.is_active = False
        self.suspended_at = datetime.utcnow()
        self.suspension_reason = reason
        db.session.commit()

    def reactivate(self):
        """Reactivate suspended tenant."""
        self.is_active = True
        self.suspended_at = None
        self.suspension_reason = None
        db.session.commit()


class TenantDomain(BaseModel):
    """
    Custom domain mapping for tenants.
    
    Allows tenants to use custom domains (e.g., expenses.acme.com).
    """

    __tablename__ = "tenant_domains"

    tenant_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)

    # DNS verification
    verification_token: Mapped[str] = mapped_column(db.String(255), nullable=True)
    verification_method: Mapped[str] = mapped_column(
        db.String(50), nullable=False, default="dns"
    )  # dns, file

    # SSL certificate info
    ssl_enabled: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    ssl_issued_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="custom_domains")

    def __repr__(self):
        return f"<TenantDomain {self.domain} -> {self.tenant_id}>"
