"""Core configuration module for TrackTok application."""
import os
from datetime import timedelta
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration class."""

    # Flask Core
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://tracktok:tracktok@localhost:5432/tracktok"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = "UTC"
    CELERY_ENABLE_UTC = True

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "2592000"))
    )
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # Multi-tenancy
    TENANT_RESOLUTION = os.getenv("TENANT_RESOLUTION", "subdomain")  # subdomain or header
    TENANT_HEADER = os.getenv("TENANT_HEADER", "X-Tenant-Id")
    BASE_DOMAIN = os.getenv("BASE_DOMAIN", "localhost:5000")
    ENABLE_CUSTOM_DOMAINS = os.getenv("ENABLE_CUSTOM_DOMAINS", "True").lower() == "true"

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "X-Tenant-Id"]
    CORS_EXPOSE_HEADERS = ["X-Total-Count", "X-Request-Id"]

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "redis://localhost:6379/1")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "100 per hour")
    RATELIMIT_HEADERS_ENABLED = True

    # Pagination
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))

    # File Upload
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "16777216"))  # 16MB
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "csv"}

    # Email
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@tracktok.com")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # json or text

    # Observability
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "False").lower() == "true"

    # Feature Flags
    ENABLE_REGISTRATION = os.getenv("ENABLE_REGISTRATION", "True").lower() == "true"
    ENABLE_EMAIL_NOTIFICATIONS = (
        os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "True").lower() == "true"
    )

    # API Documentation
    API_TITLE = "TrackTok API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api/docs"
    OPENAPI_SWAGGER_UI_PATH = "/swagger"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    OPENAPI_REDOC_PATH = "/redoc"
    OPENAPI_REDOC_URL = (
        "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
    )
    API_URL_PREFIX = "/api/v1"


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False

    # Override with stricter production settings
    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self) -> Dict[str, Any]:
        """Production database engine options."""
        return {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_size": 20,
            "max_overflow": 40,
        }


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config() -> Config:
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)()
