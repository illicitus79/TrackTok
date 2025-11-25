"""Web UI blueprint."""
from flask import Blueprint

bp = Blueprint("web", __name__)

from app.web import views

__all__ = ["bp"]
