"""User preferences API endpoints."""
import logging

from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.core.extensions import db
from app.models.user import User
from app.models.user_preferences import UserPreferences
from app.schemas.user_preferences import (
    UserPreferencesSchema,
    UserPreferencesUpdateSchema,
)
from app.utils.decorators import roles_required

logger = logging.getLogger(__name__)

blp = Blueprint(
    "user_preferences",
    __name__,
    url_prefix="/api/v1/users",
    description="User preferences management",
)


@blp.route("/<user_id>/preferences")
class UserPreferencesResource(MethodView):
    """User preferences endpoint."""

    @blp.response(200, UserPreferencesSchema)
    @roles_required("Owner", "Admin", "Analyst", "Member")
    def get(self, user_id):
        """
        Get user preferences.
        
        Users can only view their own preferences unless they're Admin/Owner.
        """
        tenant_id = g.tenant_id
        current_user_id = g.user_id
        
        # Verify user exists in tenant
        user = User.query.filter_by(
            id=user_id,
            tenant_id=tenant_id,
            is_deleted=False
        ).first()
        
        if not user:
            abort(404, message="User not found")
        
        # Check permissions: users can view own prefs, admins can view any
        current_user = User.query.get(current_user_id)
        if user_id != current_user_id and current_user.role not in ["admin", "owner"]:
            abort(403, message="You can only view your own preferences")
        
        # Get or create preferences
        prefs = UserPreferences.get_or_create_for_user(user_id)
        
        return prefs

    @blp.arguments(UserPreferencesUpdateSchema)
    @blp.response(200, UserPreferencesSchema)
    @roles_required("Owner", "Admin", "Analyst", "Member")
    def patch(self, update_data, user_id):
        """
        Update user preferences.
        
        Users can only update their own preferences unless they're Admin/Owner.
        """
        tenant_id = g.tenant_id
        current_user_id = g.user_id
        
        # Verify user exists in tenant
        user = User.query.filter_by(
            id=user_id,
            tenant_id=tenant_id,
            is_deleted=False
        ).first()
        
        if not user:
            abort(404, message="User not found")
        
        # Check permissions
        current_user = User.query.get(current_user_id)
        if user_id != current_user_id and current_user.role not in ["admin", "owner"]:
            abort(403, message="You can only update your own preferences")
        
        try:
            # Get or create preferences
            prefs = UserPreferences.get_or_create_for_user(user_id)
            
            # Update fields
            for key, value in update_data.items():
                if hasattr(prefs, key):
                    setattr(prefs, key, value)
            
            db.session.commit()
            
            logger.info(f"Updated preferences for user {user_id}")
            
            return prefs
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update preferences for user {user_id}: {e}")
            abort(500, message="Failed to update preferences")


@blp.route("/me/preferences")
class CurrentUserPreferences(MethodView):
    """Current user preferences endpoint (convenience)."""

    @blp.response(200, UserPreferencesSchema)
    @roles_required("Owner", "Admin", "Analyst", "Member")
    def get(self):
        """Get current user's preferences."""
        user_id = g.user_id
        prefs = UserPreferences.get_or_create_for_user(user_id)
        return prefs

    @blp.arguments(UserPreferencesUpdateSchema)
    @blp.response(200, UserPreferencesSchema)
    @roles_required("Owner", "Admin", "Analyst", "Member")
    def patch(self, update_data):
        """Update current user's preferences."""
        user_id = g.user_id
        
        try:
            prefs = UserPreferences.get_or_create_for_user(user_id)
            
            # Update fields
            for key, value in update_data.items():
                if hasattr(prefs, key):
                    setattr(prefs, key, value)
            
            db.session.commit()
            
            logger.info(f"Updated preferences for current user {user_id}")
            
            return prefs
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update preferences for user {user_id}: {e}")
            abort(500, message="Failed to update preferences")
