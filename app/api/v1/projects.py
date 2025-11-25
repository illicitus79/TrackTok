"""Projects API endpoints."""
from datetime import datetime

from flask import g, jsonify, request
from flask.views import MethodView
from flask_smorest import Blueprint
from loguru import logger
from sqlalchemy import func

from app.core.extensions import db
from app.models.audit import AuditAction, AuditLog
from app.models.expense import Expense
from app.models.project import Project
from app.schemas.project import ProjectCreateSchema, ProjectSchema, ProjectUpdateSchema
from app.utils.decorators import roles_required
from app.utils.pagination import paginate

blp = Blueprint("projects", __name__, url_prefix="/projects", description="Project management")


@blp.route("")
class ProjectList(MethodView):
    """Project collection endpoint."""

    @blp.response(200)
    @roles_required('Member', 'Analyst', 'Admin', 'Owner')
    def get(self):
        """
        List all projects for current tenant.
        
        Query params:
        - status: Filter by status (active/completed/archived)
        - from_date: Filter projects starting after date
        - to_date: Filter projects ending before date
        - search: Search in name/description
        - page: Page number
        - per_page: Items per page
        """
        tenant_id = g.get("tenant_id")
        
        # Build query
        query = Project.query.filter_by(tenant_id=tenant_id, is_deleted=False)
        
        # Apply filters
        status = request.args.get("status")
        if status:
            query = query.filter_by(status=status)
        
        from_date = request.args.get("from_date")
        if from_date:
            query = query.filter(Project.start_date >= datetime.fromisoformat(from_date))
        
        to_date = request.args.get("to_date")
        if to_date:
            query = query.filter(Project.end_date <= datetime.fromisoformat(to_date))
        
        search = request.args.get("search")
        if search:
            query = query.filter(
                db.or_(
                    Project.name.ilike(f"%{search}%"),
                    Project.description.ilike(f"%{search}%"),
                )
            )
        
        # Order by created_at desc
        query = query.order_by(Project.created_at.desc())
        
        # Paginate
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 20)), 100)
        
        result = paginate(query, page, per_page, ProjectSchema())
        
        return jsonify(result)

    @blp.arguments(ProjectCreateSchema)
    @blp.response(201, ProjectSchema)
    @roles_required('Admin', 'Owner')
    def post(self, data):
        """Create a new project (Admin/Owner only)."""
        tenant_id = g.get("tenant_id")
        user_id = g.get("user_id")
        
        try:
            project = Project(
                tenant_id=tenant_id,
                name=data["name"],
                description=data.get("description", ""),
                start_date=data["start_date"],
                end_date=data["end_date"],
                starting_budget=data["starting_budget"],
                projected_estimate=data.get("projected_estimate", data["starting_budget"]),
                status=data.get("status", "active"),
            )
            
            db.session.add(project)
            db.session.commit()
            
            AuditLog.log_action(
                action=AuditAction.CREATE,
                entity_type="project",
                entity_id=project.id,
            )
            
            logger.info(f"Project created", project_id=project.id, created_by=user_id)
            
            return ProjectSchema().dump(project), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Project creation error: {e}")
            return (
                jsonify({"error": "Project creation failed", "code": "CREATION_ERROR"}),
                500,
            )


@blp.route("/<string:project_id>")
class ProjectDetail(MethodView):
    """Individual project endpoint."""

    @blp.response(200, ProjectSchema)
    @roles_required('Member', 'Analyst', 'Admin', 'Owner')
    def get(self, project_id):
        """Get project details with aggregates."""
        tenant_id = g.get("tenant_id")
        
        project = Project.query.filter_by(
            id=project_id, tenant_id=tenant_id, is_deleted=False
        ).first()
        
        if not project:
            return jsonify({"error": "Project not found", "code": "NOT_FOUND"}), 404
        
        # Include aggregates
        result = ProjectSchema().dump(project)
        result["aggregates"] = {
            "total_spent": project.total_spent,
            "remaining_budget": project.remaining_budget,
            "budget_utilization": project.budget_utilization,
            "is_over_budget": project.is_over_budget,
            "days_elapsed": project.days_elapsed,
            "days_remaining": project.days_remaining,
        }
        
        return jsonify(result)

    @blp.arguments(ProjectUpdateSchema)
    @blp.response(200, ProjectSchema)
    @roles_required('Admin', 'Owner')
    def patch(self, data, project_id):
        """Update project fields (Admin/Owner only)."""
        tenant_id = g.get("tenant_id")
        
        project = Project.query.filter_by(
            id=project_id, tenant_id=tenant_id, is_deleted=False
        ).first()
        
        if not project:
            return jsonify({"error": "Project not found", "code": "NOT_FOUND"}), 404
        
        try:
            changes = {}
            
            for field in ["name", "description", "start_date", "end_date", "starting_budget", "projected_estimate", "status"]:
                if field in data:
                    old_value = getattr(project, field)
                    new_value = data[field]
                    if old_value != new_value:
                        changes[field] = {"old": str(old_value), "new": str(new_value)}
                        setattr(project, field, new_value)
            
            db.session.commit()
            
            if changes:
                AuditLog.log_action(
                    action=AuditAction.UPDATE,
                    entity_type="project",
                    entity_id=project.id,
                    details={"changes": changes},
                )
            
            logger.info(f"Project updated", project_id=project.id)
            
            return ProjectSchema().dump(project)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Project update error: {e}")
            return jsonify({"error": "Update failed", "code": "UPDATE_ERROR"}), 500

    @blp.response(204)
    @roles_required('Admin', 'Owner')
    def delete(self, project_id):
        """Soft delete project (Admin/Owner only)."""
        tenant_id = g.get("tenant_id")
        
        project = Project.query.filter_by(
            id=project_id, tenant_id=tenant_id, is_deleted=False
        ).first()
        
        if not project:
            return jsonify({"error": "Project not found", "code": "NOT_FOUND"}), 404
        
        try:
            project.is_deleted = True
            project.deleted_at = datetime.utcnow()
            db.session.commit()
            
            AuditLog.log_action(
                action=AuditAction.DELETE,
                entity_type="project",
                entity_id=project.id,
            )
            
            logger.info(f"Project soft deleted", project_id=project.id)
            
            return "", 204
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Project deletion error: {e}")
            return jsonify({"error": "Deletion failed", "code": "DELETE_ERROR"}), 500
