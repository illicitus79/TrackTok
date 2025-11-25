"""Web views for server-rendered pages."""
from flask import render_template, redirect, url_for, request, flash, session, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, set_access_cookies
from flask_login import logout_user, login_user

from app.web import bp
from app.web.forms import LoginForm, RegistrationForm
from app.models.user import User
from app.core.extensions import db


@bp.route("/")
def landing():
    """Landing page."""
    return render_template("landing.html")


@bp.route("/dashboard")
@jwt_required(optional=True)
def dashboard():
    """Dashboard page (requires authentication)."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("dashboard.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    form = LoginForm()
    
    if form.validate_on_submit():
        # Authenticate user
        email = form.email.data
        password = form.password.data
        
        # Find user in database
        user = User.query.filter_by(email=email, is_deleted=False).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account is inactive. Please contact support.", "error")
                return redirect(url_for("web.login"))
            
            # Log in user with Flask-Login
            login_user(user, remember=form.remember_me.data)
            
            # Update login tracking
            user.update_login()
            db.session.commit()
            
            flash(f"Welcome back, {user.first_name or user.email}!", "success")
            
            # Redirect to next page or dashboard
            next_page = request.args.get("next")
            return redirect(next_page if next_page else url_for("web.dashboard"))
        else:
            flash("Invalid email or password. Please try again.", "error")
    
    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Registration page."""
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Form submitted - redirect to API endpoint or handle registration
        # For now, just show a message
        flash("Please use the API endpoint /api/v1/auth/register for tenant registration", "info")
        return redirect(url_for("web.register"))
    
    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    """Logout user."""
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("web.landing"))


@bp.route("/profile")
@jwt_required(optional=True)
def profile():
    """User profile page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("profile.html")


@bp.route("/settings")
@jwt_required(optional=True)
def settings():
    """User settings page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("settings.html")


@bp.route("/projects")
@jwt_required(optional=True)
def projects():
    """Projects list page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("projects/list.html")


@bp.route("/forgot-password")
def forgot_password():
    """Forgot password page."""
    return render_template("auth/forgot_password.html")


@bp.route("/expenses")
@jwt_required(optional=True)
def expenses():
    """Expenses list page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("expenses/list.html")


@bp.route("/budgets")
@jwt_required(optional=True)
def budgets():
    """Budgets page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("budgets/list.html")


@bp.route("/reports/project/<project_id>/summary")
@jwt_required(optional=True)
def project_summary_report(project_id):
    """Project summary report page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("reports/project_summary.html", project_id=project_id)


@bp.route("/reports/project/<project_id>/category-breakdown")
@jwt_required(optional=True)
def category_breakdown_report(project_id):
    """Category breakdown report page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("reports/category_breakdown.html", project_id=project_id)


@bp.route("/reports/project/<project_id>/monthly-trend")
@jwt_required(optional=True)
def monthly_trend_report(project_id):
    """Monthly trend report page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("reports/monthly_trend.html", project_id=project_id)


@bp.route("/reports/cashflow")
@jwt_required(optional=True)
def cashflow_report():
    """Tenant cashflow report page."""
    user_id = get_jwt_identity()
    
    if not user_id:
        return redirect(url_for("web.login"))
    
    return render_template("reports/cashflow.html")
