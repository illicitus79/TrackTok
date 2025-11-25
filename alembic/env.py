"""Alembic environment configuration for Flask-Migrate compatibility."""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add app to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.core.extensions import db

# Import all models to ensure they're registered with SQLAlchemy
from app.models import (  # noqa: F401
    Account,
    Alert,
    AuditLog,
    Budget,
    BudgetAlert,
    Category,
    Expense,
    PasswordResetToken,
    Project,
    RecurringExpense,
    Tenant,
    TenantDomain,
    User,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get Flask app and configure
flask_app = create_app()
config.set_main_option("sqlalchemy.url", flask_app.config["SQLALCHEMY_DATABASE_URI"])

# Metadata for autogenerate
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    An Engine is created and associated with a connection.
    """

    def process_revision_directives(context, revision, directives):
        """Custom revision directive processor."""
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                print("No changes detected. Skipping migration creation.")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
