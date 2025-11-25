"""Expense tracking models."""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import JSON, CheckConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.core.tenancy import TenantMixin
from app.models.base import AuditMixin, BaseModel


class ExpenseStatus(str, Enum):
    """Expense status."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentMethod(str, Enum):
    """Payment methods."""

    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class Category(BaseModel, TenantMixin):
    """Expense categories (tenant-specific)."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    color: Mapped[str] = mapped_column(db.String(7), nullable=True)  # Hex color code
    icon: Mapped[str] = mapped_column(db.String(50), nullable=True)  # Icon name/emoji
    
    # Budget tracking
    is_budget_enabled: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    monthly_budget: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Parent category for hierarchical categories
    parent_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("categories.id"), nullable=True
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="categories")
    expenses = relationship("Expense", back_populates="category")
    subcategories = relationship("Category", backref=db.backref("parent", remote_side="Category.id"))

    __table_args__ = (db.UniqueConstraint("tenant_id", "name", name="uq_tenant_category"),)

    def __repr__(self):
        return f"<Category {self.name}>"


class Expense(BaseModel, TenantMixin, AuditMixin):
    """
    Core expense tracking model.
    
    Immutable audit trail - updates create new audit log entries.
    """

    __tablename__ = "expenses"

    # Financial details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, index=True
    )  # Support up to 999,999,999,999.99
    currency: Mapped[str] = mapped_column(db.String(3), nullable=False, default="USD")
    
    # Description
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Categorization
    category_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("categories.id"), nullable=False, index=True
    )
    
    # Date tracking
    expense_date: Mapped[date] = mapped_column(db.Date, nullable=False, index=True)
    
    # Payment details
    payment_method: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default=PaymentMethod.CASH.value
    )
    payment_reference: Mapped[str] = mapped_column(db.String(255), nullable=True)
    
    # Status & approval workflow
    status: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default=ExpenseStatus.SUBMITTED.value, index=True
    )
    
    # Attachments
    receipt_url: Mapped[str] = mapped_column(db.String(512), nullable=True)
    attachments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    
    # Tags for flexible filtering
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    
    # Notes and metadata
    notes: Mapped[str] = mapped_column(db.Text, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")
    user = relationship("User", back_populates="expenses", foreign_keys=[AuditMixin.created_by])

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_expense_amount_positive"),
        db.Index("idx_tenant_date", "tenant_id", "expense_date"),
        db.Index("idx_tenant_category", "tenant_id", "category_id"),
        db.Index("idx_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self):
        return f"<Expense {self.title} - {self.amount} {self.currency}>"

    def approve(self, approved_by: str):
        """Approve expense."""
        self.status = ExpenseStatus.APPROVED.value
        self.updated_by = approved_by
        db.session.commit()

    def reject(self, rejected_by: str, reason: str = None):
        """Reject expense."""
        self.status = ExpenseStatus.REJECTED.value
        self.updated_by = rejected_by
        if reason:
            self.notes = f"Rejection reason: {reason}\n{self.notes or ''}"
        db.session.commit()

    def add_tag(self, tag: str):
        """Add tag to expense."""
        if tag not in self.tags:
            tags = self.tags or []
            tags.append(tag)
            self.tags = tags
            db.session.commit()

    def remove_tag(self, tag: str):
        """Remove tag from expense."""
        if tag in self.tags:
            tags = self.tags or []
            tags.remove(tag)
            self.tags = tags
            db.session.commit()


class RecurringExpense(BaseModel, TenantMixin, AuditMixin):
    """Recurring expense template."""

    __tablename__ = "recurring_expenses"

    # Financial details
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(db.String(3), nullable=False, default="USD")
    
    # Description
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Categorization
    category_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("categories.id"), nullable=False
    )
    
    # Recurrence pattern
    frequency: Mapped[str] = mapped_column(
        db.String(20), nullable=False
    )  # daily, weekly, monthly, yearly
    interval: Mapped[int] = mapped_column(db.Integer, nullable=False, default=1)  # Every N periods
    
    # Date range
    start_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    end_date: Mapped[date] = mapped_column(db.Date, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False)
    last_generated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    next_generation_date: Mapped[date] = mapped_column(db.Date, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    category = relationship("Category")

    __table_args__ = (CheckConstraint("amount > 0", name="check_recurring_amount_positive"),)

    def __repr__(self):
        return f"<RecurringExpense {self.title} - {self.frequency}>"
