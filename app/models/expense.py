"""Expense tracking models."""
from datetime import date, datetime, timezone
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


class Expense(BaseModel, TenantMixin, AuditMixin):
    """
    Core expense tracking model.
    
    Immutable audit trail - updates create new audit log entries.
    Supports project-related and unrelated expenses with cross-project references.
    """

    __tablename__ = "expenses"

    # Financial details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, index=True
    )  # Support up to 999,999,999,999.99
    currency: Mapped[str] = mapped_column(db.String(3), nullable=False, default="USD")
    
    # Description (vendor + note from spec)
    vendor: Mapped[str] = mapped_column(db.String(255), nullable=True)
    note: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Categorization (nullable as per spec)
    category_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("categories.id"), nullable=True, index=True
    )
    
    # Project relationship (nullable for unrelated expenses)
    project_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("projects.id"), nullable=True, index=True
    )
    is_project_related: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    
    # Account relationship (required - where money comes from)
    account_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("accounts.id"), nullable=False, index=True
    )
    
    # Cross-project reference (optional)
    cross_project_ref_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("expenses.id"), nullable=True
    )
    
    # Date tracking (stored in UTC)
    expense_date: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, index=True)
    
    # Payment details (kept for compatibility)
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
    
    # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    expense_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Soft delete field (soft_deleted_at as per spec)
    deleted_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")
    project = relationship("Project", back_populates="expenses")
    account = relationship("Account", back_populates="expenses")
    creator = relationship("User", foreign_keys="Expense.created_by", backref="created_expenses")
    updater = relationship("User", foreign_keys="Expense.updated_by", backref="updated_expenses")
    cross_project_ref = relationship("Expense", remote_side="Expense.id", foreign_keys=[cross_project_ref_id])

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_expense_amount_positive"),
        db.Index("idx_tenant_date", "tenant_id", "expense_date"),
        db.Index("idx_tenant_category", "tenant_id", "category_id"),
        db.Index("idx_tenant_status", "tenant_id", "status"),
        db.Index("idx_tenant_project", "tenant_id", "project_id"),
        db.Index("idx_tenant_account", "tenant_id", "account_id"),
    )

    def __repr__(self):
        return f"<Expense {self.vendor or 'N/A'} - {self.amount} {self.currency}>"

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
            self.note = f"Rejection reason: {reason}\n{self.note or ''}"
        db.session.commit()
    
    def soft_delete(self, deleted_by: str = None):
        """Soft delete expense and reverse account balance impact."""
        from app.models.account import Account
        
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        if deleted_by:
            self.updated_by = deleted_by
        
        # Reverse account balance impact (credit back)
        if self.account_id:
            account = db.session.query(Account).filter_by(id=self.account_id).first()
            if account:
                account.credit(self.amount, commit=False)
        
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
