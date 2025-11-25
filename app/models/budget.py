"""Budget management models."""
from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.core.tenancy import TenantMixin
from app.models.base import BaseModel


class BudgetPeriod(str, Enum):
    """Budget period types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class Budget(BaseModel, TenantMixin):
    """
    Budget tracking model.
    
    Budgets can be set for categories, users, or overall.
    """

    __tablename__ = "budgets"

    # Budget details
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Amount
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(db.String(3), nullable=False, default="USD")
    
    # Period
    period: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default=BudgetPeriod.MONTHLY.value
    )
    start_date: Mapped[date] = mapped_column(db.Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(db.Date, nullable=False, index=True)
    
    # Scope (optional filters)
    category_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("categories.id"), nullable=True, index=True
    )
    owner_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("users.id"), nullable=True, index=True
    )  # Budget for specific user
    
    # Alert settings
    alert_threshold: Mapped[int] = mapped_column(
        db.Integer, nullable=False, default=80
    )  # Alert at 80%
    alert_enabled: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="budgets")
    category = relationship("Category")
    owner = relationship("User", back_populates="budgets", foreign_keys=[owner_id])
    alerts = relationship("BudgetAlert", back_populates="budget", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_budget_amount_positive"),
        CheckConstraint("start_date <= end_date", name="check_budget_dates"),
        CheckConstraint(
            "alert_threshold >= 0 AND alert_threshold <= 100", name="check_alert_threshold"
        ),
        db.Index("idx_tenant_period", "tenant_id", "period"),
        db.Index("idx_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self):
        return f"<Budget {self.name} - {self.amount} {self.currency}>"

    def get_spent_amount(self) -> Decimal:
        """Calculate total spent against this budget."""
        from sqlalchemy import func

        from app.models.expense import Expense

        query = (
            db.session.query(func.sum(Expense.amount))
            .filter(
                Expense.tenant_id == self.tenant_id,
                Expense.is_deleted == False,
                Expense.expense_date >= self.start_date,
                Expense.expense_date <= self.end_date,
            )
        )

        # Apply category filter if budget is category-specific
        if self.category_id:
            query = query.filter(Expense.category_id == self.category_id)

        # Apply user filter if budget is user-specific
        if self.owner_id:
            query = query.filter(Expense.created_by == self.owner_id)

        spent = query.scalar() or Decimal("0.00")
        return spent

    def get_remaining_amount(self) -> Decimal:
        """Calculate remaining budget."""
        return self.amount - self.get_spent_amount()

    def get_utilization_percentage(self) -> float:
        """Calculate budget utilization as percentage."""
        if self.amount == 0:
            return 0.0
        return float((self.get_spent_amount() / self.amount) * 100)

    def should_alert(self) -> bool:
        """Check if budget has exceeded alert threshold."""
        if not self.alert_enabled or not self.is_active:
            return False
        return self.get_utilization_percentage() >= self.alert_threshold

    def is_exceeded(self) -> bool:
        """Check if budget is exceeded."""
        return self.get_spent_amount() > self.amount


class BudgetAlert(BaseModel, TenantMixin):
    """Budget alert history."""

    __tablename__ = "budget_alerts"

    budget_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Alert details
    threshold_percentage: Mapped[int] = mapped_column(db.Integer, nullable=False)
    amount_spent: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Notification tracking
    is_sent: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    sent_at: Mapped[date] = mapped_column(db.Date, nullable=True)
    notification_method: Mapped[str] = mapped_column(db.String(50), nullable=True)  # email, in-app
    
    # Relationships
    budget = relationship("Budget", back_populates="alerts")
    tenant = relationship("Tenant")

    def __repr__(self):
        return f"<BudgetAlert {self.budget_id} - {self.threshold_percentage}%>"
