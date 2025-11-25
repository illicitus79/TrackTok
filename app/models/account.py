"""Account model for managing financial accounts."""
from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.models.base import BaseModel


class Account(BaseModel):
    """
    Account model for financial accounts.
    
    Represents bank accounts, cash, credit cards, etc.
    """

    __tablename__ = "accounts"

    # Tenant relationship
    tenant_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic fields
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        db.String(50), nullable=False, default="cash"
    )  # cash, bank, credit_card, digital_wallet
    
    # Balance fields
    currency: Mapped[str] = mapped_column(db.String(3), nullable=False, default="USD")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    low_balance_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    is_archived: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False, index=True)
    
    # Additional info
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    account_number_last4: Mapped[Optional[str]] = mapped_column(db.String(4), nullable=True)

    # Audit fields
    created_by: Mapped[Optional[str]] = mapped_column(
        db.String(36), db.ForeignKey("users.id"), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="accounts")
    expenses = relationship("Expense", back_populates="account", lazy="dynamic")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        db.Index("ix_accounts_tenant_active", "tenant_id", "is_active"),
        db.Index("ix_accounts_tenant_type", "tenant_id", "account_type"),
    )

    def __repr__(self):
        return f"<Account {self.name} ({self.currency} {self.current_balance})>"

    @property
    def is_low_balance(self) -> bool:
        """Check if account is below low balance threshold."""
        if self.low_balance_threshold is None:
            return False
        return self.current_balance <= self.low_balance_threshold

    @property
    def balance_change(self) -> Decimal:
        """Calculate change from opening balance."""
        return self.current_balance - self.opening_balance

    @property
    def balance_change_percentage(self) -> float:
        """Calculate percentage change from opening balance."""
        if self.opening_balance == 0:
            return 0.0
        return float((self.balance_change / self.opening_balance) * 100)

    def debit(self, amount: Decimal, commit: bool = True) -> None:
        """
        Debit (subtract) amount from account.
        
        Args:
            amount: Amount to debit
            commit: Whether to commit transaction
        """
        self.current_balance -= amount
        if commit:
            db.session.commit()

    def credit(self, amount: Decimal, commit: bool = True) -> None:
        """
        Credit (add) amount to account.
        
        Args:
            amount: Amount to credit
            commit: Whether to commit transaction
        """
        self.current_balance += amount
        if commit:
            db.session.commit()

    def adjust_balance(self, new_balance: Decimal, commit: bool = True) -> None:
        """
        Manually adjust balance (admin only).
        
        Args:
            new_balance: New balance amount
            commit: Whether to commit transaction
        """
        self.current_balance = new_balance
        if commit:
            db.session.commit()

    def to_dict(self, include_metrics: bool = False):
        """
        Convert to dictionary.
        
        Args:
            include_metrics: Include calculated metrics
        """
        data = super().to_dict()
        data.update({
            "opening_balance": float(self.opening_balance),
            "current_balance": float(self.current_balance),
            "low_balance_threshold": float(self.low_balance_threshold) if self.low_balance_threshold else None,
        })
        
        if include_metrics:
            data.update({
                "is_low_balance": self.is_low_balance,
                "balance_change": float(self.balance_change),
                "balance_change_percentage": self.balance_change_percentage,
            })
        
        return data
