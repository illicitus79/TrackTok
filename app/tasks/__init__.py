"""Tasks package."""

# Expose celery_app so Celery CLI can resolve "-A app.tasks.celery_app"
from importlib import import_module

celery_app = import_module("app.tasks.celery_app")

__all__ = ["celery_app"]
