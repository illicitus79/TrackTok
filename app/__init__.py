"""Flask application factory."""
import uuid

from flask import Flask, g, jsonify, request
from loguru import logger
from redis import Redis

from app.core import api, cors, db, get_config, jwt, limiter, migrate, setup_logging


def create_app(config_name: str = None) -> Flask:
    """
    Flask application factory.

    Args:
        config_name: Configuration name (development, testing, production)

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

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
    # API blueprints
    from app.api.v1 import bp as api_v1_bp

    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")

    # Web UI blueprints
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

    logger.info("CLI commands registered")
