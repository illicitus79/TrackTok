"""Accounts API endpoints."""
from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from loguru import logger

from app.core.extensions import db
from app.middleware.tenancy import TenancyMiddleware

bp = Blueprint("accounts", __name__, url_prefix="/accounts", description="Account management")


@bp.route("")
class AccountList(MethodView):
    """Account collection endpoint."""

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def get(self):
        """List all accounts for current tenant."""
        # TODO: Implement after Account model is created
        return jsonify({"message": "Accounts list - implementation pending"}), 200

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def post(self):
        """Create a new account."""
        # TODO: Implement after Account model and schema are created
        return jsonify({"message": "Create account - implementation pending"}), 201


@bp.route("/<string:account_id>")
class AccountDetail(MethodView):
    """Individual account endpoint."""

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def get(self, account_id):
        """Get account details with current balance."""
        # TODO: Implement after Account model is created
        return jsonify({"message": f"Get account {account_id} - implementation pending"}), 200

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def patch(self, account_id):
        """Update account fields."""
        # TODO: Implement after Account model and schema are created
        return jsonify({"message": f"Update account {account_id} - implementation pending"}), 200


@bp.route("/<string:account_id>/adjust_balance")
class AccountBalanceAdjustment(MethodView):
    """Account balance adjustment endpoint (admin only)."""

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def post(self, account_id):
        """Manually adjust account balance."""
        # TODO: Implement with RBAC check for admin role
        return jsonify({"message": f"Adjust balance for {account_id} - implementation pending"}), 200
