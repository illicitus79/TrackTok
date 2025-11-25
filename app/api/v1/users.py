"""User management endpoints."""
from flask import g, jsonify, request
from flask.views import MethodView
from flask_smorest import Blueprint
from loguru import logger

from app.core.extensions import db
from app.models.audit import AuditAction, AuditLog
from app.models.user import User
from app.schemas.user import UserRoleUpdateSchema, UserSchema, UserUpdateSchema
from app.utils.decorators import roles_required
from app.utils.pagination import paginate

blp = Blueprint("users", __name__, url_prefix="/users", description="User management")


@blp.route("")
class UserList(MethodView):
    """User listing endpoint."""

    @blp.response(200)
    @roles_required('Owner', 'Admin')
    def get(self):
        """
        List all users in tenant (Owner/Admin only).
        
        Query params:
        - role: Filter by role
        - is_active: Filter by active status
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
        """
        tenant_id = g.get("tenant_id")
        
        # Build query
        query = User.query.filter_by(tenant_id=tenant_id, is_deleted=False)
        
        # Apply filters
        role_filter = request.args.get("role")
        if role_filter:
            query = query.filter_by(role=role_filter)
        
        is_active = request.args.get("is_active")
        if is_active is not None:
            query = query.filter_by(is_active=is_active.lower() == 'true')
        
        # Order by created_at desc
        query = query.order_by(User.created_at.desc())
        
        # Paginate
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 20)), 100)
        
        result = paginate(query, page, per_page, UserSchema())
        
        return jsonify(result)


@blp.route("/<string:user_id>")
class UserDetail(MethodView):
    """User detail operations."""

    @blp.response(200, UserSchema)
    @roles_required('Owner', 'Admin')
    def get(self, user_id):
        """Get user details (Owner/Admin only)."""
        tenant_id = g.get("tenant_id")
        
        user = User.query.filter_by(id=user_id, tenant_id=tenant_id, is_deleted=False).first()
        if not user:
            return jsonify({"error": "User not found", "code": "NOT_FOUND"}), 404
        
        return UserSchema().dump(user)

    @blp.arguments(UserUpdateSchema)
    @blp.response(200, UserSchema)
    @roles_required('Owner', 'Admin')
    def patch(self, data, user_id):
        """
        Update user (Owner/Admin only).
        
        Can update: first_name, last_name, avatar_url, preferences, is_active
        """
        tenant_id = g.get("tenant_id")
        current_user_id = g.get("user_id")
        
        user = User.query.filter_by(id=user_id, tenant_id=tenant_id, is_deleted=False).first()
        if not user:
            return jsonify({"error": "User not found", "code": "NOT_FOUND"}), 404
        
        # Prevent deactivating yourself
        if "is_active" in data and user_id == current_user_id:
            if not data["is_active"]:
                return (
                    jsonify(
                        {
                            "error": "Cannot deactivate your own account",
                            "code": "INVALID_OPERATION",
                        }
                    ),
                    400,
                )
        
        try:
            # Track changes for audit
            changes = {}
            
            if "first_name" in data:
                changes["first_name"] = {"old": user.first_name, "new": data["first_name"]}
                user.first_name = data["first_name"]
            
            if "last_name" in data:
                changes["last_name"] = {"old": user.last_name, "new": data["last_name"]}
                user.last_name = data["last_name"]
            
            if "avatar_url" in data:
                user.avatar_url = data["avatar_url"]
            
            if "preferences" in data:
                user.preferences = {**user.preferences, **data["preferences"]}
            
            db.session.commit()
            
            # Log audit
            if changes:
                AuditLog.log_action(
                    action=AuditAction.UPDATE,
                    entity_type="user",
                    entity_id=user.id,
                    details={"changes": changes},
                )
            
            logger.info(f"User updated", user_id=user.id, updated_by=current_user_id)
            
            return UserSchema().dump(user)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"User update error: {e}")
            return jsonify({"error": "Update failed", "code": "UPDATE_ERROR"}), 500


@blp.route("/<string:user_id>/activate")
class UserActivation(MethodView):
    """User activation/deactivation."""

    @blp.response(200)
    @roles_required('Owner', 'Admin')
    def post(self, user_id):
        """Activate user (Owner/Admin only)."""
        tenant_id = g.get("tenant_id")
        current_user_id = g.get("user_id")
        
        if user_id == current_user_id:
            return (
                jsonify(
                    {
                        "error": "Cannot modify your own activation status",
                        "code": "INVALID_OPERATION",
                    }
                ),
                400,
            )
        
        user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first()
        if not user:
            return jsonify({"error": "User not found", "code": "NOT_FOUND"}), 404
        
        user.is_active = True
        db.session.commit()
        
        AuditLog.log_action(
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user.id,
            details={"action": "activated"},
        )
        
        logger.info(f"User activated", user_id=user.id, by=current_user_id)
        
        return jsonify({"message": "User activated successfully", "user": UserSchema().dump(user)})


@blp.route("/<string:user_id>/deactivate")
class UserDeactivation(MethodView):
    """User deactivation."""

    @blp.response(200)
    @roles_required('Owner', 'Admin')
    def post(self, user_id):
        """Deactivate user (Owner/Admin only)."""
        tenant_id = g.get("tenant_id")
        current_user_id = g.get("user_id")
        
        if user_id == current_user_id:
            return (
                jsonify(
                    {
                        "error": "Cannot deactivate your own account",
                        "code": "INVALID_OPERATION",
                    }
                ),
                400,
            )
        
        user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first()
        if not user:
            return jsonify({"error": "User not found", "code": "NOT_FOUND"}), 404
        
        user.is_active = False
        db.session.commit()
        
        AuditLog.log_action(
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user.id,
            details={"action": "deactivated"},
        )
        
        logger.info(f"User deactivated", user_id=user.id, by=current_user_id)
        
        return jsonify({"message": "User deactivated successfully", "user": UserSchema().dump(user)})


@blp.route("/<string:user_id>/role")
class UserRoleChange(MethodView):
    """User role management."""

    @blp.arguments(UserRoleUpdateSchema)
    @blp.response(200)
    @roles_required('Owner')
    def patch(self, data, user_id):
        """Change user role (Owner only)."""
        tenant_id = g.get("tenant_id")
        current_user_id = g.get("user_id")
        
        if user_id == current_user_id:
            return (
                jsonify(
                    {
                        "error": "Cannot change your own role",
                        "code": "INVALID_OPERATION",
                    }
                ),
                400,
            )
        
        user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first()
        if not user:
            return jsonify({"error": "User not found", "code": "NOT_FOUND"}), 404
        
        old_role = user.role
        new_role = data["role"]
        
        user.role = new_role
        db.session.commit()
        
        AuditLog.log_action(
            action=AuditAction.ROLE_CHANGE,
            entity_type="user",
            entity_id=user.id,
            details={"old_role": old_role, "new_role": new_role},
        )
        
        logger.info(f"User role changed", user_id=user.id, old_role=old_role, new_role=new_role)
        
        return jsonify(
            {
                "message": "Role updated successfully",
                "user": UserSchema().dump(user),
                "old_role": old_role,
                "new_role": new_role,
            }
        )
