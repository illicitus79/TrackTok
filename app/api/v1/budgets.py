"""Budget API endpoints."""
from flask import g, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint

from app.core.extensions import db
from app.models.budget import Budget
from app.schemas.budget import BudgetSchema, BudgetCreateSchema, BudgetUpdateSchema, BudgetStatusSchema

blp = Blueprint("budgets", __name__, url_prefix="/budgets", description="Budget operations")


@blp.route("/")
class BudgetList(MethodView):
    """Budget list endpoint."""

    @jwt_required()
    @blp.response(200)
    def get(self):
        """Get all budgets for tenant."""
        tenant_id = g.get("tenant_id")

        budgets = Budget.query.filter_by(tenant_id=tenant_id, is_deleted=False).all()

        return jsonify({"budgets": BudgetSchema(many=True).dump(budgets)})

    @jwt_required()
    @blp.arguments(BudgetCreateSchema)
    @blp.response(201)
    def post(self, data):
        """Create a new budget."""
        user_id = get_jwt_identity()
        tenant_id = g.get("tenant_id")

        budget = Budget(**data, tenant_id=tenant_id)
        db.session.add(budget)
        db.session.commit()

        return jsonify(BudgetSchema().dump(budget)), 201


@blp.route("/<budget_id>")
class BudgetDetail(MethodView):
    """Individual budget endpoint."""

    @jwt_required()
    @blp.response(200, BudgetSchema)
    def get(self, budget_id):
        """Get budget by ID."""
        tenant_id = g.get("tenant_id")

        budget = Budget.query.filter_by(
            id=budget_id, tenant_id=tenant_id, is_deleted=False
        ).first()

        if not budget:
            return jsonify({"error": "Budget not found"}), 404

        return BudgetSchema().dump(budget)

    @jwt_required()
    @blp.arguments(BudgetUpdateSchema)
    @blp.response(200)
    def patch(self, data, budget_id):
        """Update a budget."""
        tenant_id = g.get("tenant_id")

        budget = Budget.query.filter_by(
            id=budget_id, tenant_id=tenant_id, is_deleted=False
        ).first()

        if not budget:
            return jsonify({"error": "Budget not found"}), 404

        for key, value in data.items():
            setattr(budget, key, value)

        db.session.commit()

        return jsonify(BudgetSchema().dump(budget))


@blp.route("/<budget_id>/status")
class BudgetStatus(MethodView):
    """Budget status endpoint."""

    @jwt_required()
    @blp.response(200)
    def get(self, budget_id):
        """Get budget utilization status."""
        tenant_id = g.get("tenant_id")

        budget = Budget.query.filter_by(
            id=budget_id, tenant_id=tenant_id, is_deleted=False
        ).first()

        if not budget:
            return jsonify({"error": "Budget not found"}), 404

        status = {
            "budget_id": budget.id,
            "name": budget.name,
            "amount": str(budget.amount),
            "spent": str(budget.get_spent_amount()),
            "remaining": str(budget.get_remaining_amount()),
            "utilization_percentage": budget.get_utilization_percentage(),
            "is_exceeded": budget.is_exceeded(),
            "alert_threshold": budget.alert_threshold,
            "should_alert": budget.should_alert(),
        }

        return jsonify(status)
