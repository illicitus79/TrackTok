"""Base model with common fields and soft delete functionality."""
import uuid
from datetime import datetime

from sqlalchemy import event
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.extensions import db


class BaseModel(db.Model):
    """
    Abstract base model with common fields.
    
    Provides:
    - UUID primary key
    - Created/updated timestamps
    - Soft delete functionality
    - Helper methods
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Soft delete fields
    is_deleted: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)

    def save(self):
        """Save instance to database."""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self, soft: bool = True):
        """
        Delete instance from database.
        
        Args:
            soft: If True, perform soft delete. If False, hard delete.
        """
        if soft:
            self.is_deleted = True
            self.deleted_at = datetime.utcnow()
            db.session.commit()
        else:
            db.session.delete(self)
            db.session.commit()

    def restore(self):
        """Restore soft-deleted instance."""
        self.is_deleted = False
        self.deleted_at = None
        db.session.commit()

    @classmethod
    def get_by_id(cls, record_id: str):
        """Get record by ID (excluding soft-deleted)."""
        return db.session.query(cls).filter_by(id=record_id, is_deleted=False).first()

    @classmethod
    def get_all(cls, include_deleted: bool = False):
        """Get all records."""
        query = db.session.query(cls)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.all()

    def to_dict(self, exclude: list = None):
        """
        Convert model instance to dictionary.
        
        Args:
            exclude: List of fields to exclude from output
        """
        exclude = exclude or []
        data = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    value = value.isoformat()
                data[column.name] = value
        return data

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"


class AuditMixin:
    """
    Mixin for audit trail fields.
    
    Tracks who created/updated records for compliance.
    """

    @declared_attr
    def created_by(cls):
        """User who created the record."""
        return mapped_column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    @declared_attr
    def updated_by(cls):
        """User who last updated the record."""
        return mapped_column(db.String(36), db.ForeignKey("users.id"), nullable=True)


class TimestampMixin:
    """Mixin for timestamp fields only (for immutable models)."""

    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, nullable=False)


# Event listeners for automatic timestamp updates
@event.listens_for(BaseModel, "before_update", propagate=True)
def receive_before_update(mapper, connection, target):
    """Update updated_at timestamp before update."""
    target.updated_at = datetime.utcnow()
