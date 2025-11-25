"""Dashboards API endpoints."""
from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from loguru import logger

from app.core.extensions import db
from app.middleware.tenancy import TenancyMiddleware

bp = Blueprint("dashboards", __name__, url_prefix="/dashboards", description="Dashboard analytics")


@bp.route("/project/<string:project_id>")
class ProjectDashboard(MethodView):
    """Project-specific dashboard data."""

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def get(self, project_id):
        """
        Get project dashboard with aggregates.
        
        Returns:
            - totals: starting_budget, projected_estimate, total_spend, remaining_budget
            - per-account balances
            - category breakdown
            - monthly trend
            - forecast vs actual
        """
        # TODO: Implement after Project, Expense, Account models are created
        return jsonify({
            "project": {"id": project_id, "name": "Sample Project"},
            "starting_budget": 50000,
            "projected_estimate": 52000,
            "total_spend": 0,
            "remaining_budget": 50000,
            "accounts": [],
            "category_breakdown": {"labels": [], "data": []},
            "monthly_trend": {"labels": [], "datasets": []},
            "forecast_vs_actual": {"labels": [], "datasets": []}
        }), 200


@bp.route("/tenant")
class TenantDashboard(MethodView):
    """Tenant-wide dashboard data."""

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def get(self):
        """
        Get tenant-wide dashboard.
        
        Returns:
            - total_spend
            - top vendors
            - low-balance accounts
            - alert counts
        """
        # TODO: Implement after models are created
        return jsonify({
            "total_spend": 0,
            "top_vendors": [],
            "low_balance_accounts": [],
            "alerts": {"total": 0, "unread": 0}
        }), 200
