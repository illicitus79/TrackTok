"""Alerts API endpoints."""
import logging
from typing import Optional

from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import desc

from app.core.extensions import db
from app.models.alert import Alert
from app.schemas.alert import (
    AlertListQuerySchema,
    AlertSchema,
    AlertUpdateSchema,
)
from app.utils.decorators import roles_required

logger = logging.getLogger(__name__)

blp = Blueprint(
    "alerts",
    __name__,
    url_prefix="/api/v1/alerts",
    description="Alert notifications management",
)


@blp.route("")
class AlertList(MethodView):
    """Alert list endpoint."""

    @blp.arguments(AlertListQuerySchema, location="query")
    @blp.response(200, AlertSchema(many=True))
    @roles_required("Owner", "Admin", "Analyst", "Member")
    def get(self, query_params):
        """
        List alerts with filters.
        
        Returns paginated list of alerts for the current tenant.
        Supports filtering by type, severity, read status, etc.
        """
        tenant_id = g.tenant_id
        page = query_params.get("page", 1)
        per_page = query_params.get("per_page", 20)
        
        # Build query
        query = Alert.query.filter_by(
            tenant_id=tenant_id,
            is_deleted=False
        )
        
        # Apply filters
        if "alert_type" in query_params:
            query = query.filter_by(alert_type=query_params["alert_type"])
        
        if "severity" in query_params:
            query = query.filter_by(severity=query_params["severity"])
        
        if "entity_type" in query_params:
            query = query.filter_by(entity_type=query_params["entity_type"])
        
        if "is_read" in query_params:
            query = query.filter_by(is_read=query_params["is_read"])
        
        if "is_dismissed" in query_params:
            query = query.filter_by(is_dismissed=query_params["is_dismissed"])
        
        # Sorting
        sort_by = query_params.get("sort_by", "created_at")
        sort_order = query_params.get("sort_order", "desc")
        
        if sort_by == "created_at":
            order_col = Alert.created_at
        elif sort_by == "severity":
            # Custom severity order: critical, error, warning, info
            severity_order = db.case(
                {
                    "critical": 1,
                    "error": 2,
                    "warning": 3,
                    "info": 4,
                },
                value=Alert.severity,
                else_=5
            )
            order_col = severity_order
        else:
            order_col = Alert.created_at
        
        if sort_order == "desc":
            query = query.order_by(desc(order_col))
        else:
            query = query.order_by(order_col)
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get unread count for header
        unread_count = Alert.get_unread_count(tenant_id)
        
        logger.info(
            f"Listed alerts for tenant {tenant_id}: {paginated.total} total, {unread_count} unread"
        )
        
        return {
            "items": paginated.items,
            "total": paginated.total,
            "page": page,
            "per_page": per_page,
            "pages": paginated.pages,
            "unread_count": unread_count,
        }


@blp.route("/<alert_id>")
class AlertDetail(MethodView):
    """Alert detail endpoint."""

    @blp.response(200, AlertSchema)
    @roles_required("Owner", "Admin", "Analyst", "Member")
    def get(self, alert_id):
        """Get alert details."""
        tenant_id = g.tenant_id
        
        alert = Alert.query.filter_by(
            id=alert_id,
            tenant_id=tenant_id,
            is_deleted=False
        ).first()
        
        if not alert:
            abort(404, message="Alert not found")
        
        return alert

    @blp.arguments(AlertUpdateSchema)
    @blp.response(200, AlertSchema)
    @roles_required("Owner", "Admin", "Analyst", "Member")
    def patch(self, update_data, alert_id):
        """
        Update alert status.
        
        Allows marking alerts as read or dismissed.
        """
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        alert = Alert.query.filter_by(
            id=alert_id,
            tenant_id=tenant_id,
            is_deleted=False
        ).first()
        
        if not alert:
            abort(404, message="Alert not found")
        
        try:
            # Mark as read
            if "is_read" in update_data and update_data["is_read"]:
                if not alert.is_read:
                    alert.mark_as_read(user_id=user_id, commit=False)
                    logger.info(f"Alert {alert_id} marked as read by user {user_id}")
            
            # Mark as dismissed
            if "is_dismissed" in update_data and update_data["is_dismissed"]:
                if not alert.is_dismissed:
                    alert.dismiss(commit=False)
                    logger.info(f"Alert {alert_id} dismissed by user {user_id}")
            
            db.session.commit()
            
            return alert
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update alert {alert_id}: {e}")
            abort(500, message="Failed to update alert")


@blp.route("/bulk/mark-read", methods=["POST"])
@roles_required("Owner", "Admin", "Analyst", "Member")
def mark_all_as_read():
    """
    Mark all unread alerts as read for current user.
    
    Useful for "mark all as read" functionality.
    """
    tenant_id = g.tenant_id
    user_id = g.user_id
    
    try:
        # Get all unread alerts
        unread_alerts = Alert.query.filter_by(
            tenant_id=tenant_id,
            is_read=False,
            is_deleted=False
        ).all()
        
        count = 0
        for alert in unread_alerts:
            alert.mark_as_read(user_id=user_id, commit=False)
            count += 1
        
        db.session.commit()
        
        logger.info(f"Marked {count} alerts as read for user {user_id}")
        
        return {
            "message": f"Marked {count} alerts as read",
            "count": count
        }, 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to mark alerts as read: {e}")
        abort(500, message="Failed to mark alerts as read")


@blp.route("/stats")
@blp.response(200)
@roles_required("Owner", "Admin", "Analyst", "Member")
def get_alert_stats():
    """
    Get alert statistics.
    
    Returns counts by type, severity, and read status.
    """
    from sqlalchemy import func
    
    tenant_id = g.tenant_id
    
    try:
        # Count by type
        type_counts = db.session.query(
            Alert.alert_type,
            func.count(Alert.id).label("count")
        ).filter_by(
            tenant_id=tenant_id,
            is_deleted=False,
            is_read=False
        ).group_by(Alert.alert_type).all()
        
        # Count by severity
        severity_counts = db.session.query(
            Alert.severity,
            func.count(Alert.id).label("count")
        ).filter_by(
            tenant_id=tenant_id,
            is_deleted=False,
            is_read=False
        ).group_by(Alert.severity).all()
        
        # Total counts
        total = Alert.query.filter_by(
            tenant_id=tenant_id,
            is_deleted=False
        ).count()
        
        unread = Alert.query.filter_by(
            tenant_id=tenant_id,
            is_deleted=False,
            is_read=False
        ).count()
        
        dismissed = Alert.query.filter_by(
            tenant_id=tenant_id,
            is_deleted=False,
            is_dismissed=True
        ).count()
        
        return {
            "total": total,
            "unread": unread,
            "dismissed": dismissed,
            "by_type": {item.alert_type: item.count for item in type_counts},
            "by_severity": {item.severity: item.count for item in severity_counts},
        }
        
    except Exception as e:
        logger.error(f"Failed to get alert stats: {e}")
        abort(500, message="Failed to get alert statistics")
