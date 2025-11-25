"""Web views for server-rendered pages."""
from flask import render_template, redirect, url_for, request, flash, session
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.web import bp


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


@bp.route("/login")
def login():
    """Login page."""
    return render_template("auth/login.html")


@bp.route("/register")
def register():
    """Registration page."""
    return render_template("auth/register.html")


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
