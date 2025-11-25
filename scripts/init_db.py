"""Database initialization script."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.core.extensions import db
from loguru import logger


def init_database():
    """Initialize database with all tables."""
    app = create_app()

    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("✓ Database tables created successfully")

        print("\n✅ Database initialized successfully!")
        print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")


if __name__ == "__main__":
    init_database()
