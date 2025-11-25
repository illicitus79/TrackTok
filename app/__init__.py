"""Flask application factory."""
import os
import uuid

from flask import Flask, g, jsonify, request
from loguru import logger
from redis import Redis

from app.core import api, cors, csrf, db, get_config, jwt, limiter, login_manager, mail, migrate, setup_logging


def create_app(config_name: str = None) -> Flask:
    """
    Flask application factory.

    Args:
        config_name: Configuration name (development, testing, production)

    Returns:
        Configured Flask application instance
    """
    # Get the root directory (parent of app folder)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(__name__,
                static_folder=os.path.join(root_dir, 'static'),
                template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))

    # Load configuration
    if config_name:
        from app.core.config import config_by_name

        app.config.from_object(config_by_name[config_name])
    else:
        app.config.from_object(get_config())

    # Setup logging
    setup_logging(app)
    logger.info("Starting TrackTok application", env=app.config.get("FLASK_ENV"))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, origins=app.config["CORS_ORIGINS"])
    api.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "web.login"
    login_manager.login_message = "Please log in to access this page."
    
    # Configure Flask-Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        from app.models.user import User
        return db.session.get(User, user_id)
    
    # Initialize CSRF protection (exempt API routes, protect web forms)
    csrf.init_app(app)
    # Exempt all /api/* routes from CSRF (they use JWT)
    csrf.exempt('app.api.v1.auth')
    csrf.exempt('app.api.v1.users')
    csrf.exempt('app.api.v1.tenants')
    csrf.exempt('app.api.v1.projects')
    csrf.exempt('app.api.v1.accounts')
    csrf.exempt('app.api.v1.expenses')
    csrf.exempt('app.api.v1.categories')
    csrf.exempt('app.api.v1.budgets')
    csrf.exempt('app.api.v1.reports')
    csrf.exempt('app.api.v1.dashboards')
    csrf.exempt('app.api.v1.alerts')

    # Initialize Redis
    app.redis = Redis.from_url(app.config["REDIS_URL"], decode_responses=True)

    # Register middleware
    register_middleware(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register CLI commands
    register_cli_commands(app)

    # Health check endpoint
    @app.route("/api/v1/health")
    def health_check():
        """Health check endpoint for container orchestration."""
        try:
            # Check database connection
            db.session.execute(db.select(1))
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = "unhealthy"

        try:
            # Check Redis connection
            app.redis.ping()
            redis_status = "healthy"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            redis_status = "unhealthy"

        status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"

        return jsonify(
            {
                "status": status,
                "database": db_status,
                "redis": redis_status,
                "version": app.config.get("API_VERSION", "v1"),
            }
        ), 200 if status == "healthy" else 503

    logger.info("Application initialized successfully")
    return app


def register_middleware(app: Flask) -> None:
    """Register application middleware."""
    from app.middleware.request_id import RequestIdMiddleware
    from app.middleware.tenancy import TenancyMiddleware

    # Request ID middleware (must be first)
    @app.before_request
    def add_request_id():
        """Add unique request ID to g context."""
        g.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))

    @app.after_request
    def inject_request_id(response):
        """Inject request ID into response headers."""
        response.headers["X-Request-Id"] = g.get("request_id")
        return response

    # Tenancy middleware
    app.before_request(TenancyMiddleware.resolve_tenant)

    # Request logging
    @app.before_request
    def log_request():
        """Log incoming request."""
        logger.info(
            "Incoming request",
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
            tenant_id=g.get("tenant_id"),
        )

    @app.after_request
    def log_response(response):
        """Log outgoing response."""
        logger.info(
            "Outgoing response",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            tenant_id=g.get("tenant_id"),
        )
        return response

    logger.info("Middleware registered")


def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""
    # Get the Api instance from core
    from app.core import api as smorest_api
    
    # Import flask-smorest blueprints from API v1
    from app.api.v1 import (
        alerts,
        auth,
        budgets,
        expenses,
        preferences,
        projects,
        reports,
        tenants,
        users,
    )
    
    # Register each with the Api object
    smorest_api.register_blueprint(auth.blp)
    smorest_api.register_blueprint(users.blp)
    smorest_api.register_blueprint(tenants.blp)
    smorest_api.register_blueprint(projects.blp)
    smorest_api.register_blueprint(expenses.blp)
    smorest_api.register_blueprint(budgets.blp)
    smorest_api.register_blueprint(alerts.blp)
    smorest_api.register_blueprint(preferences.blp)
    smorest_api.register_blueprint(reports.blp)
    
    # TODO: Register remaining blueprints when created:
    # api.register_blueprint(accounts.blp)
    # api.register_blueprint(categories.blp)
    # api.register_blueprint(dashboards.blp)

    # Web UI blueprints (regular Flask blueprint)
    from app.web import bp as web_bp

    app.register_blueprint(web_bp)

    logger.info("Blueprints registered")


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found", "code": "NOT_FOUND"}), 404
        return jsonify({"error": "Page not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {error}")
        db.session.rollback()
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions."""
        logger.exception("Unhandled exception", error=str(error))
        db.session.rollback()
        return jsonify({"error": "An unexpected error occurred", "code": "UNEXPECTED_ERROR"}), 500

    logger.info("Error handlers registered")


def register_cli_commands(app: Flask) -> None:
    """Register custom CLI commands."""
    import click

    @app.cli.command("init-db")
    def init_db():
        """Initialize database with tables."""
        db.create_all()
        logger.info("Database initialized")
        print("✓ Database initialized successfully")

    @app.cli.command("seed-db")
    def seed_db():
        """Seed database with sample data."""
        from scripts.seed import seed_database

        seed_database()
        print("✓ Database seeded successfully")

    @app.cli.group()
    def tenants():
        """Tenant management commands."""
        pass

    @tenants.command("create")
    @click.option("--name", required=True, help="Tenant name")
    @click.option("--slug", required=True, help="Tenant subdomain slug")
    @click.option("--custom-domain", help="Optional custom domain")
    @click.option("--plan", default="free", help="Subscription plan (free/pro/enterprise)")
    @click.option("--owner-email", help="Owner email address")
    @click.option("--owner-password", help="Owner password")
    def create_tenant(name, slug, custom_domain, plan, owner_email, owner_password):
        """Create a new tenant with optional owner account."""
        from app.models.tenant import Tenant, TenantDomain
        from app.models.user import User
        from werkzeug.security import generate_password_hash
        import uuid

        # Validate slug format
        if not slug.isalnum() and "-" not in slug:
            print("✗ Error: Slug must contain only alphanumeric characters and hyphens")
            return

        # Check if slug already exists
        existing = Tenant.query.filter_by(subdomain=slug).first()
        if existing:
            print(f"✗ Error: Tenant with slug '{slug}' already exists")
            return

        try:
            # Create tenant
            tenant = Tenant(
                name=name,
                subdomain=slug,
                plan=plan,
                settings={},
            )
            db.session.add(tenant)
            db.session.flush()  # Get tenant.id

            # Create custom domain if provided
            if custom_domain:
                domain = TenantDomain(
                    tenant_id=tenant.id,
                    domain=custom_domain,
                    verification_token=str(uuid.uuid4()),
                )
                db.session.add(domain)

            # Create owner user if credentials provided
            if owner_email and owner_password:
                owner = User(
                    tenant_id=tenant.id,
                    email=owner_email,
                    password_hash=generate_password_hash(owner_password),
                    role="Owner",
                    is_active=True,
                )
                db.session.add(owner)

            db.session.commit()

            print(f"✓ Tenant created successfully!")
            print(f"  Name: {name}")
            print(f"  Subdomain: {slug}.{app.config.get('BASE_DOMAIN', 'localhost:5000')}")
            print(f"  ID: {tenant.id}")
            print(f"  Plan: {plan}")
            if custom_domain:
                print(f"  Custom Domain: {custom_domain} (unverified)")
            if owner_email:
                print(f"  Owner: {owner_email}")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating tenant: {e}")

    @tenants.command("list")
    @click.option("--active-only", is_flag=True, help="Show only active tenants")
    @click.option("--plan", help="Filter by plan")
    def list_tenants(active_only, plan):
        """List all tenants."""
        from app.models.tenant import Tenant

        query = Tenant.query

        if active_only:
            query = query.filter_by(is_active=True)
        if plan:
            query = query.filter_by(plan=plan)

        tenants = query.order_by(Tenant.created_at.desc()).all()

        if not tenants:
            print("No tenants found")
            return

        print(f"\n{'ID':<38} {'Name':<25} {'Subdomain':<20} {'Plan':<12} {'Users':<6} {'Status'}")
        print("-" * 120)

        for tenant in tenants:
            status = "Active" if tenant.is_active else "Suspended"
            user_count = len(tenant.users)
            print(
                f"{tenant.id:<38} {tenant.name[:24]:<25} {tenant.subdomain:<20} "
                f"{tenant.plan:<12} {user_count:<6} {status}"
            )

        print(f"\nTotal: {len(tenants)} tenant(s)")

    @tenants.command("seed")
    @click.option("--demo-data", is_flag=True, help="Include demo data (users, projects, expenses)")
    @click.option("--name", default="Demo Company", help="Tenant name")
    @click.option("--slug", default="demo", help="Tenant subdomain slug")
    def seed_tenant(demo_data, name, slug):
        """Create a demo tenant with optional sample data."""
        from app.models.tenant import Tenant
        from app.models.user import User
        from app.models.project import Project
        from app.models.account import Account
        from app.models.category import Category
        from app.models.expense import Expense
        from werkzeug.security import generate_password_hash
        from datetime import datetime, timedelta
        import random

        # Check if tenant exists
        existing = Tenant.query.filter_by(subdomain=slug).first()
        if existing:
            print(f"✗ Error: Tenant with slug '{slug}' already exists")
            return

        try:
            # Create tenant
            tenant = Tenant(
                name=name,
                subdomain=slug,
                plan="pro",
                settings={"currency": "USD", "timezone": "UTC"},
            )
            db.session.add(tenant)
            db.session.flush()

            # Create owner user
            owner = User(
                tenant_id=tenant.id,
                email=f"owner@{slug}.com",
                password_hash=generate_password_hash("password123"),
                role="Owner",
                is_active=True,
            )
            db.session.add(owner)

            if demo_data:
                # Create additional users
                admin = User(
                    tenant_id=tenant.id,
                    email=f"admin@{slug}.com",
                    password_hash=generate_password_hash("password123"),
                    role="Admin",
                    is_active=True,
                )
                analyst = User(
                    tenant_id=tenant.id,
                    email=f"analyst@{slug}.com",
                    password_hash=generate_password_hash("password123"),
                    role="Analyst",
                    is_active=True,
                )
                db.session.add_all([admin, analyst])
                db.session.flush()

                # Create accounts
                accounts = [
                    Account(
                        tenant_id=tenant.id,
                        name="Operating Account",
                        account_type="checking",
                        currency="USD",
                        opening_balance=50000.00,
                        current_balance=50000.00,
                        low_balance_threshold=5000.00,
                    ),
                    Account(
                        tenant_id=tenant.id,
                        name="Credit Card",
                        account_type="credit_card",
                        currency="USD",
                        opening_balance=0.00,
                        current_balance=0.00,
                        low_balance_threshold=0.00,
                    ),
                ]
                db.session.add_all(accounts)
                db.session.flush()

                # Create categories
                categories = [
                    Category(tenant_id=tenant.id, name="Software & SaaS", color="#3b82f6"),
                    Category(tenant_id=tenant.id, name="Hardware", color="#10b981"),
                    Category(tenant_id=tenant.id, name="Travel", color="#f59e0b"),
                    Category(tenant_id=tenant.id, name="Marketing", color="#ec4899"),
                    Category(tenant_id=tenant.id, name="Office Supplies", color="#8b5cf6"),
                ]
                db.session.add_all(categories)
                db.session.flush()

                # Create projects
                projects = [
                    Project(
                        tenant_id=tenant.id,
                        name="Website Redesign",
                        description="Complete overhaul of company website",
                        start_date=datetime.utcnow() - timedelta(days=60),
                        end_date=datetime.utcnow() + timedelta(days=30),
                        starting_budget=25000.00,
                        projected_estimate=24000.00,
                        status="active",
                    ),
                    Project(
                        tenant_id=tenant.id,
                        name="Mobile App Development",
                        description="iOS and Android app",
                        start_date=datetime.utcnow() - timedelta(days=90),
                        end_date=datetime.utcnow() + timedelta(days=60),
                        starting_budget=80000.00,
                        projected_estimate=85000.00,
                        status="active",
                    ),
                ]
                db.session.add_all(projects)
                db.session.flush()

                # Create sample expenses
                vendors = ["AWS", "GitHub", "Figma", "Adobe", "Microsoft", "Apple", "Dell"]
                expenses = []

                for i in range(50):
                    project = random.choice(projects + [None, None])  # Some unrelated expenses
                    category = random.choice(categories)
                    account = random.choice(accounts)
                    amount = round(random.uniform(50, 5000), 2)
                    expense_date = datetime.utcnow() - timedelta(days=random.randint(0, 90))

                    expense = Expense(
                        tenant_id=tenant.id,
                        project_id=project.id if project else None,
                        account_id=account.id,
                        category_id=category.id,
                        amount=amount,
                        currency="USD",
                        expense_date=expense_date,
                        vendor=random.choice(vendors),
                        note=f"Sample expense #{i+1}",
                        is_project_related=project is not None,
                        created_by=owner.id,
                    )
                    expenses.append(expense)

                    # Update account balance
                    account.current_balance -= amount

                db.session.add_all(expenses)

            db.session.commit()

            print(f"\n✓ Demo tenant created successfully!")
            print(f"  Name: {name}")
            print(f"  Subdomain: {slug}.{app.config.get('BASE_DOMAIN', 'localhost:5000')}")
            print(f"  ID: {tenant.id}")
            print(f"\n  Owner credentials:")
            print(f"    Email: owner@{slug}.com")
            print(f"    Password: password123")

            if demo_data:
                print(f"\n  Demo data created:")
                print(f"    Users: 3 (Owner, Admin, Analyst)")
                print(f"    Accounts: 2")
                print(f"    Categories: 5")
                print(f"    Projects: 2")
                print(f"    Expenses: 50")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating demo tenant: {e}")
            import traceback
            traceback.print_exc()

    logger.info("CLI commands registered")
