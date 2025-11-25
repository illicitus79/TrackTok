"""Flask extensions initialization."""
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from redis import Redis
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


# Initialize extensions (without app)
db = SQLAlchemy(model_class=Base)
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
api = Api()
csrf = CSRFProtect()
mail = Mail()
login_manager = LoginManager()
redis_client: Redis = None  # Will be initialized in app factory


def get_redis_connection():
    """Get Redis connection from Flask app config."""
    from flask import current_app

    if not hasattr(current_app, "redis"):
        current_app.redis = Redis.from_url(
            current_app.config["REDIS_URL"], decode_responses=True
        )
    return current_app.redis


# Rate limiter with Redis storage
# Note: storage_uri will be overridden by RATELIMIT_STORAGE_URL in app config
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"],
)
