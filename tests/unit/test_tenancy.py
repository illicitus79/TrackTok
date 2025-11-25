"""Unit tests for multi-tenancy enforcement."""
import pytest
from app.core.extensions import db
from app.core.tenancy import set_tenant_context, get_current_tenant_id
from app.models import Tenant, Expense, Category


@pytest.mark.unit
@pytest.mark.tenancy
class TestTenancyEnforcement:
    """Test tenant isolation and enforcement."""
    
    def test_tenant_context(self, app, tenant):
        """Test tenant context management."""
        with app.app_context():
            set_tenant_context(tenant.id)
            assert get_current_tenant_id() == tenant.id
    
    def test_tenant_scoped_query(self, app, session, tenant, user):
        """Test automatic tenant filtering on queries."""
        # Create another tenant
        tenant2 = Tenant(name="Other Org", subdomain="other")
        session.add(tenant2)
        session.commit()
        
        # Create categories for both tenants
        cat1 = Category(tenant_id=tenant.id, name="Cat 1")
        cat2 = Category(tenant_id=tenant2.id, name="Cat 2")
        session.add_all([cat1, cat2])
        session.commit()
        
        with app.app_context():
            set_tenant_context(tenant.id)
            
            # Query should only return tenant1's categories
            categories = Category.query.all()
            assert len(categories) >= 1
            assert all(c.tenant_id == tenant.id for c in categories)
    
    def test_cross_tenant_access_prevention(self, app, session, tenant):
        """Test that cross-tenant access is prevented."""
        # Create another tenant with data
        tenant2 = Tenant(name="Other Org", subdomain="other")
        session.add(tenant2)
        session.commit()
        
        cat2 = Category(tenant_id=tenant2.id, name="Secret Category")
        session.add(cat2)
        session.commit()
        
        with app.app_context():
            set_tenant_context(tenant.id)
            
            # Attempt to access other tenant's data by ID should fail
            result = Category.query.filter_by(id=cat2.id).first()
            assert result is None  # Should not find it due to tenant filter
