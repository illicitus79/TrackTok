"""Database initialization script."""
import sys
from pathlib import Path

from flask_migrate import upgrade
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app


def init_database():
    """Initialize or update the database schema with Alembic migrations."""
    app = create_app()

    with app.app_context():
        logger.info("Applying database migrations...")
        upgrade()
        logger.info("Database migrations applied successfully")

        print("\nDatabase initialized successfully.")
        print("Schema is at the latest migration.")


if __name__ == "__main__":
    init_database()
