"""Pytest configuration and fixtures."""
import pytest
from app import create_app
from app.core.extensions import db as _db
from app.models import Tenant, User, UserRole


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    app = create_app("testing")
    
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def db(app):
    """Create database for testing."""
    _db.app = app
    _db.create_all()
    
    yield _db
    
    _db.drop_all()


@pytest.fixture(scope="function")
def session(db):
    """Create a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    session = db.create_scoped_session(options={"bind": connection})
    db.session = session
    
    yield session
    
    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def tenant(session):
    """Create a test tenant."""
    tenant = Tenant(name="Test Org", subdomain="test")
    session.add(tenant)
    session.commit()
    return tenant


@pytest.fixture
def user(session, tenant):
    """Create a test user."""
    user = User(
        tenant_id=tenant.id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.OWNER.value,
        is_verified=True,
    )
    user.set_password("Password123")
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def auth_headers(client, user, tenant):
    """Get authentication headers."""
    from flask import g
    from app.core.security import generate_tokens
    
    # Set tenant context
    g.tenant_id = tenant.id
    
    tokens = generate_tokens(user)
    
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-Tenant-Id": tenant.id,
    }
