"""Expense API endpoints."""
from flask import g, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint
from loguru import logger

from app.core.extensions import db
from app.models.expense import Expense, Category
from app.models.audit import AuditLog, AuditAction
from app.schemas.expense import (
    ExpenseSchema,
    ExpenseCreateSchema,
    ExpenseUpdateSchema,
    ExpenseFilterSchema,
    CategorySchema,
)
from app.utils.decorators import jwt_required_with_tenant, require_role
from app.models.user import UserRole

blp = Blueprint("expenses", __name__, url_prefix="/expenses", description="Expense operations")


@blp.route("/")
class ExpenseList(MethodView):
    """Expense list endpoint."""

    @jwt_required()
    @blp.arguments(ExpenseFilterSchema, location="query")
    @blp.response(200)
    def get(self, filter_args):
        """Get list of expenses with filtering and pagination."""
        user_id = get_jwt_identity()
        tenant_id = g.get("tenant_id")

        query = Expense.query.filter_by(tenant_id=tenant_id, is_deleted=False)

        # Apply filters
        if filter_args.get("category_id"):
            query = query.filter_by(category_id=filter_args["category_id"])
        if filter_args.get("status"):
            query = query.filter_by(status=filter_args["status"])
        if filter_args.get("min_amount"):
            query = query.filter(Expense.amount >= filter_args["min_amount"])
        if filter_args.get("max_amount"):
            query = query.filter(Expense.amount <= filter_args["max_amount"])
        if filter_args.get("start_date"):
            query = query.filter(Expense.expense_date >= filter_args["start_date"])
        if filter_args.get("end_date"):
            query = query.filter(Expense.expense_date <= filter_args["end_date"])

        # Pagination
        page = filter_args.get("page", 1)
        per_page = filter_args.get("per_page", 20)

        # Sorting
        sort_by = filter_args.get("sort_by", "expense_date")
        sort_order = filter_args.get("sort_order", "desc")
        
        sort_column = getattr(Expense, sort_by)
        if sort_order == "desc":
            sort_column = sort_column.desc()
        
        query = query.order_by(sort_column)
        
        # Execute pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify(
            {
                "expenses": ExpenseSchema(many=True).dump(paginated.items),
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": paginated.total,
                    "pages": paginated.pages,
                },
            }
        )

    @jwt_required()
    @blp.arguments(ExpenseCreateSchema)
    @blp.response(201)
    def post(self, data):
        """Create a new expense."""
        user_id = get_jwt_identity()
        tenant_id = g.get("tenant_id")

        expense = Expense(**data, tenant_id=tenant_id, created_by=user_id)
        db.session.add(expense)
        db.session.commit()

        # Log audit trail
        g.user_id = user_id
        AuditLog.log_action(
            action=AuditAction.CREATE,
            resource_type="expense",
            resource_id=expense.id,
            new_values=data,
        )

        logger.info(f"Expense created", expense_id=expense.id, user_id=user_id)

        return jsonify(ExpenseSchema().dump(expense)), 201


@blp.route("/<expense_id>")
class ExpenseDetail(MethodView):
    """Individual expense endpoint."""

    @jwt_required()
    @blp.response(200, ExpenseSchema)
    def get(self, expense_id):
        """Get expense by ID."""
        tenant_id = g.get("tenant_id")

        expense = Expense.query.filter_by(
            id=expense_id, tenant_id=tenant_id, is_deleted=False
        ).first()

        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        return ExpenseSchema().dump(expense)

    @jwt_required()
    @blp.arguments(ExpenseUpdateSchema)
    @blp.response(200)
    def patch(self, data, expense_id):
        """Update an expense."""
        user_id = get_jwt_identity()
        tenant_id = g.get("tenant_id")

        expense = Expense.query.filter_by(
            id=expense_id, tenant_id=tenant_id, is_deleted=False
        ).first()

        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        old_values = ExpenseSchema().dump(expense)

        for key, value in data.items():
            setattr(expense, key, value)

        expense.updated_by = user_id
        db.session.commit()

        # Log audit trail
        g.user_id = user_id
        AuditLog.log_action(
            action=AuditAction.UPDATE,
            resource_type="expense",
            resource_id=expense.id,
            old_values=old_values,
            new_values=data,
        )

        return jsonify(ExpenseSchema().dump(expense))

    @jwt_required()
    @blp.response(204)
    def delete(self, expense_id):
        """Soft delete an expense."""
        user_id = get_jwt_identity()
        tenant_id = g.get("tenant_id")

        expense = Expense.query.filter_by(
            id=expense_id, tenant_id=tenant_id, is_deleted=False
        ).first()

        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        expense.delete(soft=True)

        # Log audit trail
        g.user_id = user_id
        AuditLog.log_action(
            action=AuditAction.DELETE, resource_type="expense", resource_id=expense.id
        )

        logger.info(f"Expense deleted", expense_id=expense.id)

        return "", 204


@blp.route("/categories")
class CategoryList(MethodView):
    """Category list endpoint."""

    @jwt_required()
    @blp.response(200)
    def get(self):
        """Get all categories for tenant."""
        tenant_id = g.get("tenant_id")

        categories = Category.query.filter_by(tenant_id=tenant_id, is_deleted=False).all()

        return jsonify({"categories": CategorySchema(many=True).dump(categories)})

    @jwt_required()
    @blp.arguments(CategorySchema)
    @blp.response(201)
    def post(self, data):
        """Create a new category."""
        user_id = get_jwt_identity()
        tenant_id = g.get("tenant_id")

        category = Category(**data, tenant_id=tenant_id)
        db.session.add(category)
        db.session.commit()

        logger.info(f"Category created", category_id=category.id)

        return jsonify(CategorySchema().dump(category)), 201
