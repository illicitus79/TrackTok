"""Tenant management endpoints."""
from flask import g, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint
from loguru import logger

from app.core.extensions import db
from app.models.tenant import Tenant, TenantDomain
from app.schemas.tenant import TenantSchema, TenantUpdateSchema
from app.utils.decorators import roles_required

blp = Blueprint("tenants", __name__, url_prefix="/tenants", description="Tenant management")


@blp.route("")
class TenantList(MethodView):
    """Tenant creation endpoint."""

    @blp.arguments(TenantSchema)
    @blp.response(201, TenantSchema)
    @roles_required('Owner')
    def post(self, data):
        """
        Create a new tenant (Owner only, used for multi-tenant provisioning).
        
        Note: Most users should use /api/v1/auth/register instead.
        """
        # Check if subdomain already exists
        existing = Tenant.query.filter_by(subdomain=data["subdomain"]).first()
        if existing:
            return (
                jsonify(
                    {
                        "error": "Subdomain already taken",
                        "code": "SUBDOMAIN_EXISTS",
                    }
                ),
                409,
            )

        try:
            tenant = Tenant(
                name=data["name"],
                subdomain=data["subdomain"],
                settings=data.get("settings", {}),
            )
            db.session.add(tenant)
            db.session.commit()

            logger.info(f"Tenant created", tenant_id=tenant.id, subdomain=tenant.subdomain)

            return TenantSchema().dump(tenant), 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"Tenant creation error: {e}")
            return (
                jsonify({"error": "Tenant creation failed", "code": "CREATION_ERROR"}),
                500,
            )


@blp.route("/<string:tenant_id>")
class TenantDetail(MethodView):
    """Tenant detail operations."""

    @blp.response(200, TenantSchema)
    @roles_required('Owner')
    def get(self, tenant_id):
        """Get tenant details (Owner only)."""
        # Verify user belongs to this tenant
        if g.tenant_id != tenant_id:
            return (
                jsonify(
                    {
                        "error": "Access denied",
                        "code": "FORBIDDEN",
                        "message": "You can only access your own tenant",
                    }
                ),
                403,
            )

        tenant = Tenant.query.filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"error": "Tenant not found", "code": "NOT_FOUND"}), 404

        return TenantSchema().dump(tenant)

    @blp.arguments(TenantUpdateSchema)
    @blp.response(200, TenantSchema)
    @roles_required('Owner')
    def patch(self, data, tenant_id):
        """Update tenant settings (Owner only)."""
        # Verify user belongs to this tenant
        if g.tenant_id != tenant_id:
            return (
                jsonify(
                    {
                        "error": "Access denied",
                        "code": "FORBIDDEN",
                        "message": "You can only update your own tenant",
                    }
                ),
                403,
            )

        tenant = Tenant.query.filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"error": "Tenant not found", "code": "NOT_FOUND"}), 404

        try:
            if "name" in data:
                tenant.name = data["name"]
            if "settings" in data:
                tenant.settings = {**tenant.settings, **data["settings"]}

            db.session.commit()

            logger.info(f"Tenant updated", tenant_id=tenant.id)

            return TenantSchema().dump(tenant)

        except Exception as e:
            db.session.rollback()
            logger.error(f"Tenant update error: {e}")
            return jsonify({"error": "Update failed", "code": "UPDATE_ERROR"}), 500
