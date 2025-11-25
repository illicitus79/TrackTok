"""Multi-tenancy core implementation with scoped sessions."""
from typing import Optional

from flask import g, has_app_context
from sqlalchemy import event
from sqlalchemy.orm import Query, Session

from app.core.extensions import db


class TenantScopedQuery(Query):
    """
    Custom Query class that automatically filters by tenant_id.
    
    All queries will be scoped to the current tenant unless explicitly disabled.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Auto-apply tenant filter if tenant context exists
        if has_app_context() and hasattr(g, "tenant_id") and g.tenant_id:
            # Only apply filter to models that have tenant_id attribute
            if hasattr(self._mapper_zero().class_, "tenant_id"):
                self._criterion = db.and_(
                    self._criterion, self._mapper_zero().class_.tenant_id == g.tenant_id
                )


def get_current_tenant_id() -> Optional[str]:
    """Get current tenant ID from request context."""
    if has_app_context():
        return g.get("tenant_id")
    return None


def set_tenant_context(tenant_id: str) -> None:
    """Set tenant context for current request."""
    if has_app_context():
        g.tenant_id = tenant_id


def clear_tenant_context() -> None:
    """Clear tenant context."""
    if has_app_context() and hasattr(g, "tenant_id"):
        delattr(g, "tenant_id")


@event.listens_for(Session, "before_flush")
def receive_before_flush(session, flush_context, instances):
    """
    Automatically set tenant_id on INSERT operations.
    
    This ensures all tenant-scoped models get the correct tenant_id
    before being persisted to the database.
    """
    tenant_id = get_current_tenant_id()
    
    if not tenant_id:
        return
    
    for instance in session.new:
        if hasattr(instance, "tenant_id") and instance.tenant_id is None:
            instance.tenant_id = tenant_id


@event.listens_for(Session, "before_flush")
def validate_tenant_fk_consistency(session, flush_context, instances):
    """
    Prevent cross-tenant FK mismatches.
    
    Validates that all foreign key relationships maintain tenant consistency.
    Raises error if trying to link entities from different tenants.
    """
    from sqlalchemy.orm import object_mapper
    from sqlalchemy.orm.properties import RelationshipProperty
    
    current_tenant_id = get_current_tenant_id()
    
    if not current_tenant_id:
        return
    
    # Check new and updated instances
    for instance in session.new | session.dirty:
        if not hasattr(instance, "tenant_id"):
            continue
        
        instance_tenant = instance.tenant_id
        if not instance_tenant:
            continue
        
        # Get all relationships for this model
        mapper = object_mapper(instance)
        for prop in mapper.iterate_properties:
            if not isinstance(prop, RelationshipProperty):
                continue
            
            # Get related object(s)
            related = getattr(instance, prop.key)
            if related is None:
                continue
            
            # Handle collections
            if isinstance(related, list):
                related_objects = related
            else:
                related_objects = [related]
            
            # Validate each related object
            for related_obj in related_objects:
                if not hasattr(related_obj, "tenant_id"):
                    continue
                
                related_tenant = related_obj.tenant_id
                if related_tenant and related_tenant != instance_tenant:
                    raise ValueError(
                        f"Cross-tenant FK violation: {instance.__class__.__name__} "
                        f"(tenant={instance_tenant}) cannot reference "
                        f"{related_obj.__class__.__name__} (tenant={related_tenant})"
                    )


def enforce_tenant_isolation(model_class, tenant_id: str):
    """
    Decorator to enforce tenant isolation on model queries.
    
    Usage:
        @enforce_tenant_isolation(Expense, tenant_id)
        def get_expenses():
            return Expense.query.all()  # Auto-filtered by tenant
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            original_tenant = get_current_tenant_id()
            set_tenant_context(tenant_id)
            try:
                return func(*args, **kwargs)
            finally:
                if original_tenant:
                    set_tenant_context(original_tenant)
                else:
                    clear_tenant_context()

        return wrapper

    return decorator


class TenantMixin:
    """
    Mixin class for tenant-scoped models.
    
    Adds tenant_id column and helper methods for tenant operations.
    """

    @db.declared_attr
    def tenant_id(cls):
        """Tenant foreign key column."""
        return db.Column(
            db.String(36),
            db.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

    @classmethod
    def get_for_tenant(cls, tenant_id: str):
        """Get all records for a specific tenant."""
        return cls.query.filter_by(tenant_id=tenant_id).all()

    @classmethod
    def count_for_tenant(cls, tenant_id: str) -> int:
        """Count records for a specific tenant."""
        return cls.query.filter_by(tenant_id=tenant_id).count()

    def verify_tenant_access(self, tenant_id: str) -> bool:
        """Verify if instance belongs to given tenant."""
        return self.tenant_id == tenant_id
