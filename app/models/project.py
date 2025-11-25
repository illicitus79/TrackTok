"""Project model for tracking budgeted projects."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.models.base import BaseModel


class Project(BaseModel):
    """
    Project model for budget tracking.
    
    Represents a budgeted project or initiative with expenses.
    """

    __tablename__ = "projects"

    # Tenant relationship
    tenant_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic fields
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    
    # Budget fields
    starting_budget: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    projected_estimate: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(db.String(3), nullable=False, default="USD")
    
    # Timeline
    start_date: Mapped[Optional[date]] = mapped_column(db.Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(db.Date, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default="active", index=True
    )  # active, completed, archived, on_hold
    
    # Audit fields
    created_by: Mapped[Optional[str]] = mapped_column(
        db.String(36), db.ForeignKey("users.id"), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    expenses = relationship("Expense", back_populates="project", lazy="dynamic")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        db.Index("ix_projects_tenant_status", "tenant_id", "status"),
        db.Index("ix_projects_tenant_dates", "tenant_id", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<Project {self.name} ({self.status})>"

    @property
    def total_spent(self) -> Decimal:
        """Calculate total amount spent on this project."""
        from app.models.expense import Expense
        
        total = db.session.query(
            db.func.sum(Expense.amount)
        ).filter(
            Expense.project_id == self.id,
            Expense.is_deleted == False
        ).scalar()
        
        return Decimal(total or 0)

    @property
    def remaining_budget(self) -> Decimal:
        """Calculate remaining budget."""
        return self.starting_budget - self.total_spent

    @property
    def budget_utilization(self) -> float:
        """Calculate budget utilization percentage (0-100)."""
        if self.starting_budget == 0:
            return 0.0
        return float((self.total_spent / self.starting_budget) * 100)

    @property
    def is_over_budget(self) -> bool:
        """Check if project is over budget."""
        return self.total_spent > self.starting_budget

    @property
    def days_elapsed(self) -> Optional[int]:
        """Calculate days elapsed since project start."""
        if not self.start_date:
            return None
        
        today = date.today()
        return (today - self.start_date).days

    @property
    def days_remaining(self) -> Optional[int]:
        """Calculate days remaining until project end."""
        if not self.end_date:
            return None
        
        today = date.today()
        remaining = (self.end_date - today).days
        return max(0, remaining)

    def to_dict(self, include_metrics: bool = False):
        """
        Convert to dictionary.
        
        Args:
            include_metrics: Include calculated metrics
        """
        data = super().to_dict()
        data.update({
            "starting_budget": float(self.starting_budget),
            "projected_estimate": float(self.projected_estimate),
        })
        
        if include_metrics:
            data.update({
                "total_spent": float(self.total_spent),
                "remaining_budget": float(self.remaining_budget),
                "budget_utilization": self.budget_utilization,
                "is_over_budget": self.is_over_budget,
                "days_elapsed": self.days_elapsed,
                "days_remaining": self.days_remaining,
            })
        
        return data
