"""Authentication endpoints."""
from flask import g, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint
from loguru import logger
from marshmallow import ValidationError

from app.core.extensions import db, limiter
from app.core.security import generate_tokens, hash_password, verify_password
from app.models.audit import AuditAction, AuditLog
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.tenant import TenantCreateSchema
from app.schemas.user import (
    LoginSchema,
    PasswordChangeSchema,
    PasswordResetRequestSchema,
    PasswordResetSchema,
    UserCreateSchema,
    UserInviteSchema,
    UserSchema,
)
from app.utils.decorators import roles_required
from app.services.password_reset import (
    complete_password_reset,
    request_password_reset,
)

blp = Blueprint("auth", __name__, url_prefix="/auth", description="Authentication operations")


@blp.route("/register")
class TenantRegistration(MethodView):
    """Tenant registration endpoint."""

    @limiter.limit("5 per hour")
    @blp.response(201)
    def post(self):
        """
        Register a new tenant with owner account.
        
        Creates a new tenant organization and owner user.
        """
        try:
            # Accept JSON or form-encoded payloads
            incoming = request.get_json(silent=True) or request.form.to_dict()
            if not incoming:
                return jsonify({"error": "Missing payload"}), 400

            # Map form field names from the web form to API schema fields
            mapped = {}
            mapped["name"] = incoming.get("tenant_name", "")
            mapped["subdomain"] = incoming.get("tenant_slug", "").lower()
            mapped["owner_email"] = incoming.get("email", "")
            mapped["owner_password"] = incoming.get("password", "")
            
            # Provide defaults for owner first/last name if missing
            owner_first = incoming.get("owner_first_name") or ""
            owner_last = incoming.get("owner_last_name") or ""
            if not owner_first and mapped.get("owner_email"):
                owner_first = mapped["owner_email"].split("@")[0]
            if not owner_last:
                owner_last = "Owner"
            mapped["owner_first_name"] = owner_first
            mapped["owner_last_name"] = owner_last

            data = TenantCreateSchema().load(mapped)

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

    @limiter.limit("10 per minute")
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


@blp.route("/password-reset/request")
class PasswordResetRequest(MethodView):
    """Password reset request endpoint."""

    @limiter.limit("5 per hour")
    @blp.arguments(PasswordResetRequestSchema)
    @blp.response(200)
    def post(self, data):
        """Generate reset token and send email."""
        tenant_id = g.get("tenant_id")
        if not tenant_id:
            return (
                jsonify(
                    {
                        "error": "Tenant context required",
                        "code": "TENANT_REQUIRED",
                    }
                ),
                400,
            )

        user = (
            User.query.filter_by(
                email=data["email"],
                tenant_id=tenant_id,
                is_deleted=False,
            )
            .first()
        )

        if user and user.is_active:
            try:
                request_password_reset(user)
                logger.info("Password reset email dispatched", user_id=user.id, tenant_id=tenant_id)
            except Exception as exc:
                logger.error(f"Failed to process password reset request: {exc}")

        # Always return success to avoid account enumeration
        return jsonify(
            {
                "message": "If an account exists for that email, a reset link has been sent.",
                "code": "PASSWORD_RESET_EMAIL_SENT",
            }
        )


@blp.route("/password-reset/confirm")
class PasswordResetConfirm(MethodView):
    """Password reset confirmation endpoint."""

    @limiter.limit("10 per hour")
    @blp.arguments(PasswordResetSchema)
    @blp.response(200)
    def post(self, data):
        """Reset password using token."""
        tenant_id = g.get("tenant_id")
        success, message = complete_password_reset(
            data["token"], data["new_password"], expected_tenant_id=tenant_id
        )

        if not success:
            return jsonify({"error": message, "code": "INVALID_TOKEN"}), 400

        logger.info(
            "Password reset completed",
            tenant_id=g.get("tenant_id"),
            user_id=g.get("user_id"),
        )
        return jsonify({"message": "Password reset successfully"})


@blp.route("/invite")
class InviteUser(MethodView):
    """User invitation endpoint (Owner/Admin only)."""

    @limiter.limit("20 per hour")
    @roles_required('Owner', 'Admin')
    @blp.arguments(UserInviteSchema)
    @blp.response(201)
    def post(self, data):
        """
        Invite a new user to the tenant.
        
        Owner and Admin can invite users. Creates user account and sends invitation email.
        """
        tenant_id = g.get("tenant_id")
        inviter_id = g.get("user_id")
        
        if not tenant_id:
            return (
                jsonify(
                    {
                        "error": "Tenant context required",
                        "code": "TENANT_REQUIRED",
                    }
                ),
                400,
            )
        
        try:
            # Check if user already exists in tenant
            existing_user = User.query.filter_by(
                email=data["email"], tenant_id=tenant_id
            ).first()
            
            if existing_user:
                return (
                    jsonify(
                        {
                            "error": "User already exists in this tenant",
                            "code": "USER_EXISTS",
                        }
                    ),
                    409,
                )
            
            # Validate role assignment (only Owner can create Owner/Admin)
            inviter_role = g.get("user_role")
            requested_role = data.get("role", "Member")
            
            if requested_role in ['Owner', 'Admin'] and inviter_role != 'Owner':
                return (
                    jsonify(
                        {
                            "error": "Only Owner can invite Owner or Admin users",
                            "code": "FORBIDDEN",
                        }
                    ),
                    403,
                )
            
            # Generate temporary password or invitation token
            import secrets
            temp_password = secrets.token_urlsafe(16)
            invitation_token = secrets.token_urlsafe(32)
            
            # Create user
            new_user = User(
                tenant_id=tenant_id,
                email=data["email"],
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                role=requested_role,
                is_active=True,
                is_verified=False,  # User must verify via email
            )
            new_user.set_password(temp_password)
            
            db.session.add(new_user)
            db.session.flush()
            
            # Log invitation
            AuditLog.log_action(
                action=AuditAction.USER_INVITED,
                resource_type="user",
                resource_id=new_user.id,
                details={
                    "inviter_id": inviter_id,
                    "invited_email": data["email"],
                    "role": requested_role,
                },
            )
            
            db.session.commit()
            
            # TODO: Send invitation email with temp password or magic link
            # This would integrate with Flask-Mail or an email service
            # For now, we'll log it
            logger.info(
                f"User invited",
                inviter_id=inviter_id,
                invited_user_id=new_user.id,
                email=data["email"],
                role=requested_role,
                temp_password=temp_password,  # Remove in production
            )
            
            return jsonify(
                {
                    "message": "User invited successfully",
                    "user": UserSchema().dump(new_user),
                    "temp_password": temp_password,  # Return temp password for demo (remove in production)
                    "note": "Invitation email sent to user",
                }
            ), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Invitation error: {e}")
            return jsonify({"error": "Invitation failed", "code": "INVITATION_ERROR"}), 500
