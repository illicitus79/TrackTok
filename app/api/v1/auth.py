"""Authentication endpoints."""
from flask import g, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint
from loguru import logger
from marshmallow import ValidationError

from app.core.extensions import db
from app.core.security import generate_tokens, hash_password, verify_password
from app.models.audit import AuditAction, AuditLog
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.tenant import TenantCreateSchema
from app.schemas.user import LoginSchema, PasswordChangeSchema, UserCreateSchema, UserSchema

blp = Blueprint("auth", __name__, url_prefix="/auth", description="Authentication operations")


@blp.route("/register")
class TenantRegistration(MethodView):
    """Tenant registration endpoint."""

    @blp.arguments(TenantCreateSchema)
    @blp.response(201)
    def post(self, data):
        """
        Register a new tenant with owner account.
        
        Creates a new tenant organization and owner user.
        """
        try:
            # Check if subdomain already exists
            existing_tenant = Tenant.query.filter_by(subdomain=data["subdomain"]).first()
            if existing_tenant:
                return (
                    jsonify(
                        {
                            "error": "Subdomain already taken",
                            "code": "SUBDOMAIN_EXISTS",
                        }
                    ),
                    409,
                )

            # Create tenant
            tenant = Tenant(name=data["name"], subdomain=data["subdomain"])
            db.session.add(tenant)
            db.session.flush()  # Get tenant ID

            # Create owner user
            owner = User(
                tenant_id=tenant.id,
                email=data["owner_email"],
                first_name=data["owner_first_name"],
                last_name=data["owner_last_name"],
                role=UserRole.OWNER.value,
                is_verified=True,  # Auto-verify for now
            )
            owner.set_password(data["owner_password"])
            db.session.add(owner)
            db.session.commit()

            logger.info(
                f"New tenant registered",
                tenant_id=tenant.id,
                subdomain=tenant.subdomain,
                owner_email=owner.email,
            )

            # Generate tokens
            tokens = generate_tokens(owner)

            return jsonify(
                {
                    "message": "Registration successful",
                    "tenant": {
                        "id": tenant.id,
                        "name": tenant.name,
                        "subdomain": tenant.subdomain,
                    },
                    "user": UserSchema().dump(owner),
                    **tokens,
                }
            )

        except ValidationError as e:
            db.session.rollback()
            return jsonify({"error": "Validation error", "details": e.messages}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return jsonify({"error": "Registration failed", "code": "REGISTRATION_ERROR"}), 500


@blp.route("/login")
class Login(MethodView):
    """Login endpoint."""

    @blp.arguments(LoginSchema)
    @blp.response(200)
    def post(self, credentials):
        """
        Authenticate user and return JWT tokens.
        
        Requires tenant context (subdomain or X-Tenant-Id header).
        """
        tenant_id = g.get("tenant_id")
        if not tenant_id:
            return (
                jsonify(
                    {
                        "error": "Tenant context required",
                        "code": "TENANT_REQUIRED",
                        "message": "Please provide tenant via subdomain or X-Tenant-Id header",
                    }
                ),
                400,
            )

        # Find user by email and tenant
        user = (
            User.query.filter_by(
                email=credentials["email"], tenant_id=tenant_id, is_deleted=False
            )
            .first()
        )

        if not user or not user.check_password(credentials["password"]):
            logger.warning(
                f"Failed login attempt",
                email=credentials["email"],
                tenant_id=tenant_id,
                ip=request.remote_addr,
            )
            return (
                jsonify(
                    {
                        "error": "Invalid credentials",
                        "code": "INVALID_CREDENTIALS",
                    }
                ),
                401,
            )

        if not user.is_active:
            return (
                jsonify(
                    {
                        "error": "Account is inactive",
                        "code": "ACCOUNT_INACTIVE",
                    }
                ),
                403,
            )

        # Update login tracking
        user.update_login()

        # Log login action
        g.user_id = user.id
        g.tenant_id = tenant_id
        AuditLog.log_action(action=AuditAction.LOGIN, resource_type="user", resource_id=user.id)

        # Generate tokens
        tokens = generate_tokens(user)

        logger.info(f"User logged in", user_id=user.id, email=user.email)

        return jsonify(
            {
                "message": "Login successful",
                "user": UserSchema().dump(user),
                **tokens,
            }
        )


@blp.route("/refresh")
class TokenRefresh(MethodView):
    """Token refresh endpoint."""

    @jwt_required(refresh=True)
    @blp.response(200)
    def post(self):
        """Refresh access token using refresh token."""
        user_id = get_jwt_identity()

        user = User.query.filter_by(id=user_id, is_active=True).first()
        if not user:
            return jsonify({"error": "User not found", "code": "USER_NOT_FOUND"}), 404

        # Generate new access token
        from flask_jwt_extended import create_access_token

        additional_claims = {
            "tenant_id": user.tenant_id,
            "role": user.role,
            "email": user.email,
        }

        access_token = create_access_token(identity=user.id, additional_claims=additional_claims)

        return jsonify({"access_token": access_token})


@blp.route("/me")
class CurrentUser(MethodView):
    """Current user endpoint."""

    @jwt_required()
    @blp.response(200, UserSchema)
    def get(self):
        """Get current authenticated user details."""
        user_id = get_jwt_identity()

        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found", "code": "USER_NOT_FOUND"}), 404

        return UserSchema().dump(user)


@blp.route("/change-password")
class ChangePassword(MethodView):
    """Password change endpoint."""

    @jwt_required()
    @blp.arguments(PasswordChangeSchema)
    @blp.response(200)
    def post(self, data):
        """Change user password."""
        user_id = get_jwt_identity()

        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found", "code": "USER_NOT_FOUND"}), 404

        # Verify current password
        if not user.check_password(data["current_password"]):
            return (
                jsonify(
                    {
                        "error": "Invalid current password",
                        "code": "INVALID_PASSWORD",
                    }
                ),
                400,
            )

        # Set new password
        user.set_password(data["new_password"])
        db.session.commit()

        # Log password change
        g.user_id = user.id
        g.tenant_id = user.tenant_id
        AuditLog.log_action(
            action=AuditAction.PASSWORD_CHANGE, resource_type="user", resource_id=user.id
        )

        logger.info(f"Password changed", user_id=user.id)

        return jsonify({"message": "Password changed successfully"})
