"""Category model for expense categorization."""
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.models.base import BaseModel


class Category(BaseModel):
    """
    Category model for expense classification.
    
    Allows tenant-specific categorization of expenses.
    """

    __tablename__ = "categories"

    # Tenant relationship
    tenant_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic fields
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    color: Mapped[str] = mapped_column(db.String(7), nullable=False, default="#6366F1")  # Hex color
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    
    # Icon/emoji for UI
    icon: Mapped[Optional[str]] = mapped_column(db.String(10), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    # Audit fields
    created_by: Mapped[Optional[str]] = mapped_column(
        db.String(36), db.ForeignKey("users.id"), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="categories")
    project = relationship("Project", back_populates="categories")
    expenses = relationship("Expense", back_populates="category", lazy="dynamic")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        db.Index("ix_categories_tenant_project", "tenant_id", "project_id"),
        db.UniqueConstraint("tenant_id", "project_id", "name", name="uq_category_project_name"),
    )

    def __repr__(self):
        return f"<Category {self.name}>"

    @property
    def total_expenses(self) -> int:
        """Count total expenses in this category."""
        return self.expenses.filter_by(is_deleted=False).count()

    @property
    def total_amount(self) -> float:
        """Calculate total amount of expenses in this category."""
        from app.models.expense import Expense
        
        total = db.session.query(
            db.func.sum(Expense.amount)
        ).filter(
            Expense.category_id == self.id,
            Expense.is_deleted == False
        ).scalar()
        
        return float(total or 0)

    def to_dict(self, include_metrics: bool = False):
        """
        Convert to dictionary.
        
        Args:
            include_metrics: Include calculated metrics
        """
        data = super().to_dict()
        
        if include_metrics:
            data.update({
                "total_expenses": self.total_expenses,
                "total_amount": self.total_amount,
            })
        
        return data
