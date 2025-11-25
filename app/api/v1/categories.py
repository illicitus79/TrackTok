"""Categories API endpoints."""
from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from loguru import logger

from app.core.extensions import db
from app.middleware.tenancy import TenancyMiddleware

bp = Blueprint("categories", __name__, url_prefix="/categories", description="Expense categories")


@bp.route("")
class CategoryList(MethodView):
    """Category collection endpoint."""

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def get(self):
        """List all categories for current tenant."""
        # TODO: Implement after Category model is created
        return jsonify({"message": "Categories list - implementation pending"}), 200

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def post(self):
        """Create a new category."""
        # TODO: Implement after Category model and schema are created
        return jsonify({"message": "Create category - implementation pending"}), 201


@bp.route("/<string:category_id>")
class CategoryDetail(MethodView):
    """Individual category endpoint."""

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def get(self, category_id):
        """Get category details."""
        # TODO: Implement after Category model is created
        return jsonify({"message": f"Get category {category_id} - implementation pending"}), 200

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def patch(self, category_id):
        """Update category fields."""
        # TODO: Implement after Category model and schema are created
        return jsonify({"message": f"Update category {category_id} - implementation pending"}), 200

    @jwt_required()
    @TenancyMiddleware.require_tenant()
    def delete(self, category_id):
        """Delete category."""
        # TODO: Implement after Category model is created
        return jsonify({"message": f"Delete category {category_id} - implementation pending"}), 204
