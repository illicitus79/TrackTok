"""Placeholder endpoints for users, tenants, reports."""

# users.py
from flask_smorest import Blueprint
blp_users = Blueprint("users", __name__, url_prefix="/users")

# tenants.py  
from flask_smorest import Blueprint
blp_tenants = Blueprint("tenants", __name__, url_prefix="/tenants")

# reports.py
from flask_smorest import Blueprint
blp_reports = Blueprint("reports", __name__, url_prefix="/reports")
