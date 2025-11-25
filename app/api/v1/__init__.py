"""API v1 blueprint."""
from flask import Blueprint
from flask_smorest import Api

bp = Blueprint("api_v1", __name__)

# Import and register resource blueprints
from app.api.v1 import (
    accounts,
    alerts,
    auth,
    budgets,
    categories,
    dashboards,
    expenses,
    preferences,
    projects,
    reports,
    tenants,
    users,
)

__all__ = ["bp"]
