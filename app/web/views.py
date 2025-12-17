"""Web views for server-rendered pages."""
from datetime import datetime, date
from decimal import Decimal
import base64
from uuid import uuid4

from flask import render_template, redirect, url_for, request, flash, session, current_app, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, set_access_cookies
from flask_login import logout_user, login_user, login_required, current_user
from werkzeug.utils import secure_filename

from app.web import bp
from app.web.forms import LoginForm, RegistrationForm
from app.models.user import User
from app.core.extensions import db


def get_currency_options():
    """
    Fetch currency codes dynamically, cached in Redis, with a static fallback that includes THB.
    """
    cache_key = "currencies:list:v1"
    static_fallback = [
        ("USD", "USD - US Dollar"),
        ("EUR", "EUR - Euro"),
        ("GBP", "GBP - British Pound"),
        ("JPY", "JPY - Japanese Yen"),
        ("AUD", "AUD - Australian Dollar"),
        ("CAD", "CAD - Canadian Dollar"),
        ("CHF", "CHF - Swiss Franc"),
        ("INR", "INR - Indian Rupee"),
        ("CNY", "CNY - Chinese Yuan"),
        ("SGD", "SGD - Singapore Dollar"),
        ("THB", "THB - Thai Baht"),
    ]

    try:
        if hasattr(current_app, "redis"):
            cached = current_app.redis.get(cache_key)
            if cached:
                return [tuple(item.split("::", 1)) for item in cached.split("|||")]

        import json
        from urllib.request import urlopen

        with urlopen("https://openexchangerates.org/api/currencies.json", timeout=5) as resp:
            data = json.load(resp)
            options = sorted([(code, f"{code} - {name}") for code, name in data.items()])
            if hasattr(current_app, "redis"):
                serialized = "|||".join([f"{c}::{n}" for c, n in options])
                current_app.redis.setex(cache_key, 86400, serialized)
            return options
    except Exception as e:
        current_app.logger.warning(f"Falling back to static currency list: {e}")

    return static_fallback


# Simple timezone options (IANA)
TIMEZONE_OPTIONS = [
    "UTC",
    "America/New_York",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Paris",
    "Asia/Bangkok",
    "Asia/Singapore",
    "Asia/Kolkata",
    "Australia/Sydney",
]


def get_tenant_preferences():
    """Return tenant currency/timezone with defaults."""
    tenant = getattr(current_user, "tenant", None)
    settings = tenant.settings if tenant else {}
    currency = settings.get("currency", "USD")
    timezone = settings.get("timezone", "UTC")
    return currency, timezone


def ensure_accounts_use_tenant_currency(accounts, tenant_currency: str):
    """
    Force all provided accounts to use the tenant currency.

    This is useful for older accounts that were created before tenant currency
    was introduced or updated.
    """
    changed = False
    for account in accounts or []:
        if account.currency != tenant_currency:
            account.currency = tenant_currency
            changed = True

    if changed:
        db.session.commit()

    return accounts


def _prepare_image_attachments(files):
    """
    Convert uploaded image files to attachment dicts stored in the DB.

    Returns a list of dicts with base64-encoded data and metadata. Raises
    ValueError if a file is too large or not an allowed image type.
    """
    allowed_exts = {"png", "jpg", "jpeg", "gif", "webp"}
    max_per_file = 5 * 1024 * 1024  # 5MB per image to keep rows reasonable
    attachments = []

    for file in files or []:
        if not file or not file.filename:
            continue
        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in allowed_exts:
            raise ValueError("Only image uploads are allowed (png, jpg, jpeg, gif, webp).")

        data = file.read()
        if not data:
            continue
        if len(data) > max_per_file:
            raise ValueError(f"Image {filename} is too large (max 5MB).")

        attachments.append(
            {
                "id": str(uuid4()),
                "filename": filename,
                "content_type": file.mimetype or "application/octet-stream",
                "size": len(data),
                "uploaded_at": datetime.utcnow().isoformat(),
                "data": base64.b64encode(data).decode("utf-8"),
            }
        )

    return attachments


@bp.route("/")
def landing():
    """Landing page."""
    return render_template("landing.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard page (requires authentication)."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.expense import Expense
    from app.models.project import Project
    
    # Get current user's tenant
    tenant_id = current_user.tenant_id
    
    # Calculate current month date range
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start_date = month_start.date()
    
    # Get stats for current month
    monthly_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.tenant_id == tenant_id,
        Expense.expense_date >= month_start_date,
        Expense.is_deleted == False
    ).scalar() or 0
    
    expense_count = db.session.query(func.count(Expense.id)).filter(
        Expense.tenant_id == tenant_id,
        Expense.expense_date >= month_start_date,
        Expense.is_deleted == False
    ).scalar() or 0
    
    # Get active projects count
    project_count = Project.query.filter_by(
        tenant_id=tenant_id,
        is_deleted=False
    ).count()
    
    # Get recent expenses
    recent_expenses = Expense.query.filter_by(
        tenant_id=tenant_id,
        is_deleted=False
    ).order_by(Expense.expense_date.desc()).limit(10).all()
    
    # Get active projects
    active_projects = Project.query.filter_by(
        tenant_id=tenant_id,
        is_deleted=False,
        status='active'
    ).limit(5).all()
    
    return render_template("dashboard.html",
                         monthly_expenses=monthly_expenses,
                         expense_count=expense_count,
                         project_count=project_count,
                         recent_expenses=recent_expenses,
                         active_projects=active_projects)


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
        from app.models.tenant import Tenant
        from app.models.user import User, UserRole
        
        try:
            # Check if subdomain already exists
            existing_tenant = Tenant.query.filter_by(subdomain=form.tenant_slug.data.lower()).first()
            if existing_tenant:
                flash("Subdomain already taken. Please choose another.", "error")
                return render_template("auth/register.html", form=form)
            
            # Create tenant
            tenant = Tenant(
                name=form.tenant_name.data,
                subdomain=form.tenant_slug.data.lower()
            )
            db.session.add(tenant)
            db.session.flush()  # Get tenant ID
            
            # Create owner user
            owner = User(
                tenant_id=tenant.id,
                email=form.email.data,
                first_name=form.email.data.split("@")[0],
                last_name="Owner",
                role=UserRole.OWNER.value,
                is_verified=True,
                is_active=True,
            )
            owner.set_password(form.password.data)
            db.session.add(owner)
            db.session.commit()
            
            # Log the user in
            login_user(owner)
            
            flash(f"Welcome! Your tenant '{tenant.name}' has been created successfully.", "success")
            return redirect(url_for("web.dashboard"))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            flash("Registration failed. Please try again.", "error")
            return render_template("auth/register.html", form=form)
    
    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    """Logout user."""
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("web.landing"))


@bp.route("/profile")
@login_required
def profile():
    """User profile page."""
    return render_template("profile.html")


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page."""
    tenant = current_user.tenant
    currency, timezone = get_tenant_preferences()

    if request.method == "POST":
        try:
            new_currency = request.form.get("currency") or currency
            new_timezone = request.form.get("timezone") or timezone
            tenant.settings = tenant.settings or {}
            tenant.settings.update({"currency": new_currency, "timezone": new_timezone})
            db.session.commit()
            flash("Settings updated.", "success")
            return redirect(url_for("web.settings"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update settings: {exc}", "error")

    return render_template(
        "settings.html",
        currency=currency,
        timezone=timezone,
        currency_options=get_currency_options(),
        timezone_options=TIMEZONE_OPTIONS,
    )


@bp.route("/projects")
@login_required
def projects():
    """Projects list page."""
    from app.models.project import Project

    projects = Project.query.filter_by(
        tenant_id=current_user.tenant_id,
        is_deleted=False,
    ).order_by(Project.created_at.desc()).all()

    return render_template("projects/list.html", projects=projects)


@bp.route("/projects/new", methods=["GET", "POST"])
@login_required
def project_new():
    """Create a new project and link allowed accounts."""
    from app.models.project import Project
    from app.models.account import Account

    tenant_id = current_user.tenant_id
    tenant_currency, _ = get_tenant_preferences()
    accounts = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Account.name).all()

    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            if not name:
                raise ValueError("Project name is required.")

            starting_budget = Decimal(request.form.get("starting_budget", "0") or "0")
            projected_estimate = Decimal(request.form.get("projected_estimate", starting_budget))
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")

            project = Project(
                tenant_id=tenant_id,
                name=name,
                description=request.form.get("description") or None,
                starting_budget=starting_budget,
                projected_estimate=projected_estimate,
                currency=tenant_currency,
                start_date=datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None,
                end_date=datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None,
                status=request.form.get("status", "active"),
                created_by=current_user.id,
            )
            db.session.add(project)
            db.session.commit()

            # Persist allowed accounts for this project in Redis (no schema change)
            allowed_accounts = request.form.getlist("account_ids")
            if allowed_accounts:
                # Enforce currency consistency
                acct_rows = Account.query.filter(Account.id.in_(allowed_accounts), Account.tenant_id == tenant_id).all()
                for acct in acct_rows:
                    if acct.currency != project.currency:
                        raise ValueError("All linked accounts must use the project currency.")
            if allowed_accounts:
                current_app.redis.set(
                    f"project:{project.id}:accounts",
                    ",".join(allowed_accounts)
                )

            flash("Project created successfully.", "success")
            return redirect(url_for("web.projects"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not create project: {exc}", "error")

    return render_template(
        "projects/new.html",
        accounts=accounts,
        today=date.today().isoformat(),
        tenant_currency=tenant_currency,
    )


@bp.route("/projects/<project_id>/edit", methods=["GET", "POST"])
@login_required
def project_edit(project_id):
    """Edit a project and update allowed accounts."""
    from app.models.project import Project
    from app.models.account import Account

    tenant_id = current_user.tenant_id
    tenant_currency, _ = get_tenant_preferences()
    project = Project.query.filter_by(id=project_id, tenant_id=tenant_id, is_deleted=False).first()
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("web.projects"))

    accounts = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Account.name).all()
    allowed_str = current_app.redis.get(f"project:{project.id}:accounts")
    allowed_account_ids = set(allowed_str.split(",")) if allowed_str else set()

    if request.method == "POST":
        try:
            project.name = request.form.get("name", project.name)
            project.description = request.form.get("description") or None
            project.starting_budget = Decimal(request.form.get("starting_budget", project.starting_budget))
            project.projected_estimate = Decimal(request.form.get("projected_estimate", project.projected_estimate))
            project.currency = tenant_currency
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")
            project.start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            project.end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            project.status = request.form.get("status", project.status)

            new_allowed = request.form.getlist("account_ids")
            if new_allowed:
                acct_rows = Account.query.filter(Account.id.in_(new_allowed), Account.tenant_id == tenant_id).all()
                for acct in acct_rows:
                    if acct.currency != project.currency:
                        raise ValueError("All linked accounts must use the project currency.")
            current_app.redis.set(f"project:{project.id}:accounts", ",".join(new_allowed) if new_allowed else "")

            db.session.commit()
            flash("Project updated successfully.", "success")
            return redirect(url_for("web.projects"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update project: {exc}", "error")

    return render_template(
        "projects/edit.html",
        project=project,
        accounts=accounts,
        allowed_account_ids=allowed_account_ids,
        currency_options=get_currency_options(),
        tenant_currency=tenant_currency,
    )


@bp.route("/projects/<project_id>/allowed-accounts")
@login_required
def project_allowed_accounts(project_id):
    """Return allowed accounts for a project."""
    from app.models.account import Account

    tenant_currency, _ = get_tenant_preferences()
    tenant_id = current_user.tenant_id
    allowed_str = current_app.redis.get(f"project:{project_id}:accounts")
    allowed_ids = []
    if allowed_str:
        allowed_ids = [aid for aid in allowed_str.split(",") if aid]

    query = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False)
    if allowed_ids:
        query = query.filter(Account.id.in_(allowed_ids))

    accounts = ensure_accounts_use_tenant_currency(
        query.order_by(Account.name).all(),
        tenant_currency,
    )
    return jsonify(
        [
            {
                "id": account.id,
                "name": account.name,
                "account_type": account.account_type,
                "currency": account.currency,
            }
            for account in accounts
        ]
    )


@bp.route("/projects/<project_id>")
@login_required
def project_detail(project_id):
    """Single project dashboard view."""
    from app.models.project import Project
    from app.models.account import Account
    from app.models.category import Category
    from app.models.expense import Expense
    from sqlalchemy import func, extract
    from collections import defaultdict

    project = Project.query.filter_by(
        id=project_id,
        tenant_id=current_user.tenant_id,
        is_deleted=False,
    ).first()

    if not project:
        flash("Project not found or you do not have access.", "error")
        return redirect(url_for("web.projects"))

    tenant_id = current_user.tenant_id

    # Calculate totals
    total_spend = db.session.query(func.sum(Expense.amount)).filter(
        Expense.tenant_id == tenant_id,
        Expense.project_id == project.id,
        Expense.is_deleted == False
    ).scalar() or Decimal("0.00")

    remaining_budget = Decimal(project.starting_budget or 0) - total_spend
    budget_utilization = float((total_spend / project.starting_budget) * 100) if project.starting_budget else 0.0
    days_elapsed = project.days_elapsed or 1
    burn_rate = float(total_spend) / float(days_elapsed) if days_elapsed else 0.0

    # Get accounts
    accounts = Account.query.filter_by(
        tenant_id=tenant_id,
        is_deleted=False
    ).order_by(Account.name).all()

    # Category breakdown
    category_breakdown = db.session.query(
        Category.name,
        func.sum(Expense.amount)
    ).join(Expense, Expense.category_id == Category.id).filter(
        Expense.tenant_id == tenant_id,
        Expense.project_id == project.id,
        Expense.is_deleted == False
    ).group_by(Category.name).all()

    # Monthly trend
    month_rows = db.session.query(
        extract('year', Expense.expense_date).label('y'),
        extract('month', Expense.expense_date).label('m'),
        Account.name.label('account'),
        func.sum(Expense.amount).label('total')
    ).join(Account, Account.id == Expense.account_id).filter(
        Expense.tenant_id == tenant_id,
        Expense.project_id == project.id,
        Expense.is_deleted == False
    ).group_by('y', 'm', 'account').order_by('y', 'm').all()

    month_totals = defaultdict(dict)
    for row in month_rows:
        ym = f"{int(row.y):04d}-{int(row.m):02d}"
        month_totals[ym][row.account] = float(row.total)

    sorted_months = sorted(month_totals.keys())
    monthly_datasets = []
    if sorted_months:
        accounts_seen = set()
        for _, account_totals in month_totals.items():
            accounts_seen.update(account_totals.keys())
        for account_name in sorted(accounts_seen):
            monthly_datasets.append({
                'label': account_name,
                'data': [month_totals[month].get(account_name, 0.0) for month in sorted_months]
            })

    # Forecast data
    cumulative_actual = []
    running = 0.0
    for month in sorted_months:
        running += sum(month_totals[month].values())
        cumulative_actual.append(running)

    forecast_total = float(project.projected_estimate or project.starting_budget or 0)

    # ------------------------------------------------------------------
    # Additional insights (spend velocity, runway, vendors, recents)
    # ------------------------------------------------------------------
    from datetime import date, timedelta

    today = date.today()
    start_30d = today - timedelta(days=29)

    # Daily spend series (last 30 days)
    daily_rows = (
        db.session.query(Expense.expense_date, func.sum(Expense.amount))
        .filter(
            Expense.tenant_id == tenant_id,
            Expense.project_id == project.id,
            Expense.is_deleted == False,
            Expense.expense_date >= start_30d,
            Expense.expense_date <= today,
        )
        .group_by(Expense.expense_date)
        .order_by(Expense.expense_date)
        .all()
    )
    daily_map = {r[0].isoformat(): float(r[1] or 0) for r in daily_rows}
    daily_labels = [(start_30d + timedelta(days=i)).isoformat() for i in range(30)]
    daily_data = [daily_map.get(d, 0.0) for d in daily_labels]

    spend_7d = float(sum(daily_data[-7:])) if daily_data else 0.0
    spend_30d = float(sum(daily_data)) if daily_data else 0.0
    avg_daily_7d = (spend_7d / 7.0) if spend_7d else 0.0
    avg_daily_30d = (spend_30d / 30.0) if spend_30d else 0.0

    remaining_budget_float = float(remaining_budget)
    runway_days = None
    if avg_daily_30d > 0 and remaining_budget_float > 0:
        runway_days = remaining_budget_float / avg_daily_30d

    # Month-to-date vs previous month (use full previous month total)
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    spend_mtd = (
        db.session.query(func.sum(Expense.amount))
        .filter(
            Expense.tenant_id == tenant_id,
            Expense.project_id == project.id,
            Expense.is_deleted == False,
            Expense.expense_date >= month_start,
            Expense.expense_date <= today,
        )
        .scalar()
        or Decimal("0.00")
    )
    spend_prev_month = (
        db.session.query(func.sum(Expense.amount))
        .filter(
            Expense.tenant_id == tenant_id,
            Expense.project_id == project.id,
            Expense.is_deleted == False,
            Expense.expense_date >= prev_month_start,
            Expense.expense_date <= prev_month_end,
        )
        .scalar()
        or Decimal("0.00")
    )

    mtd_change_pct = None
    if spend_prev_month and float(spend_prev_month) > 0:
        mtd_change_pct = ((float(spend_mtd) - float(spend_prev_month)) / float(spend_prev_month)) * 100.0

    # Top vendors (by spend)
    vendor_rows = (
        db.session.query(Expense.vendor, func.sum(Expense.amount))
        .filter(
            Expense.tenant_id == tenant_id,
            Expense.project_id == project.id,
            Expense.is_deleted == False,
            Expense.vendor != None,
            Expense.vendor != "",
        )
        .group_by(Expense.vendor)
        .order_by(func.sum(Expense.amount).desc())
        .limit(8)
        .all()
    )
    top_vendor_labels = [r[0] for r in vendor_rows]
    top_vendor_data = [float(r[1] or 0) for r in vendor_rows]

    # Largest single expense
    biggest_row = (
        db.session.query(Expense.vendor, Expense.amount, Expense.expense_date)
        .filter(
            Expense.tenant_id == tenant_id,
            Expense.project_id == project.id,
            Expense.is_deleted == False,
        )
        .order_by(Expense.amount.desc())
        .first()
    )
    biggest_expense = None
    if biggest_row:
        biggest_expense = {
            "vendor": biggest_row[0] or "(No vendor)",
            "amount": float(biggest_row[1] or 0),
            "date": biggest_row[2].isoformat() if biggest_row[2] else None,
        }

    # Recent expenses (for quick review)
    recent_rows = (
        db.session.query(
            Expense.id,
            Expense.expense_date,
            Expense.vendor,
            Expense.amount,
            Category.name.label("category"),
            Account.name.label("account"),
        )
        .outerjoin(Category, Category.id == Expense.category_id)
        .join(Account, Account.id == Expense.account_id)
        .filter(
            Expense.tenant_id == tenant_id,
            Expense.project_id == project.id,
            Expense.is_deleted == False,
        )
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(6)
        .all()
    )
    recent_expenses = [
        {
            "id": str(r.id),
            "date": r.expense_date.isoformat() if r.expense_date else None,
            "vendor": r.vendor or "(No vendor)",
            "amount": float(r.amount or 0),
            "category": r.category or "Uncategorized",
            "account": r.account or "—",
        }
        for r in recent_rows
    ]

    # Category concentration
    total_spend_float = float(total_spend or 0)
    top_category_name = None
    top_category_share = None
    if category_breakdown and total_spend_float > 0:
        top_category_name, top_category_total = max(category_breakdown, key=lambda x: float(x[1] or 0))
        top_category_share = (float(top_category_total or 0) / total_spend_float) * 100.0

    # Projected end spend (if project has an end date / duration)
    projected_end_total = None
    projected_end_variance = None
    project_total_days = (project.days_elapsed or 0) + (project.days_remaining or 0)
    if project_total_days > 0:
        projected_end_total = float(burn_rate) * float(project_total_days)
        projected_end_variance = projected_end_total - float(project.starting_budget or 0)

    dashboard_data = {
        'starting_budget': float(project.starting_budget or 0),
        'projected_estimate': float(project.projected_estimate or 0),
        'total_spend': float(total_spend),
        'remaining_budget': float(remaining_budget),
        'budget_utilization': budget_utilization,
        'is_over_budget': remaining_budget < 0,
        'days_remaining': project.days_remaining or 0,
        'burn_rate': burn_rate,
        'insights': {
            'spend_7d': spend_7d,
            'spend_30d': spend_30d,
            'avg_daily_7d': avg_daily_7d,
            'avg_daily_30d': avg_daily_30d,
            'runway_days': runway_days,
            'spend_mtd': float(spend_mtd or 0),
            'spend_prev_month': float(spend_prev_month or 0),
            'mtd_change_pct': mtd_change_pct,
            'top_category_name': top_category_name,
            'top_category_share': top_category_share,
            'projected_end_total': projected_end_total,
            'projected_end_variance': projected_end_variance,
            'biggest_expense': biggest_expense,
        },
        'daily_spend': {
            'labels': daily_labels,
            'data': daily_data,
        },
        'top_vendors': {
            'labels': top_vendor_labels,
            'data': top_vendor_data,
        },
        'recent_expenses': recent_expenses,
        'forecast': {
            'projected_total': forecast_total,
            'confidence': 75,
            'variance': float(forecast_total - float(total_spend))
        },
        'accounts': [{
            'id': str(a.id),
            'name': a.name,
            'type': a.account_type,
            'current_balance': float(a.current_balance or 0),
            'currency': a.currency or 'USD'
        } for a in accounts],
        'category_breakdown': {
            'labels': [row[0] for row in category_breakdown],
            'data': [float(row[1]) for row in category_breakdown]
        },
        'monthly_trend': {
            'labels': sorted_months,
            'datasets': monthly_datasets
        },
        'forecast_vs_actual': {
            'labels': sorted_months,
            'datasets': [
                {'label': 'Actual', 'data': cumulative_actual},
                {'label': 'Forecast', 'data': [forecast_total for _ in sorted_months]}
            ]
        }
    }

    return render_template("dashboard/project.html", project=project, dashboard_data=dashboard_data)


@bp.route("/projects/<project_id>/categories", methods=["GET", "POST"])
@login_required
def project_categories(project_id):
    """Manage categories scoped to a single project."""
    from app.models.project import Project
    from app.models.category import Category

    tenant_id = current_user.tenant_id
    project = Project.query.filter_by(
        id=project_id, tenant_id=tenant_id, is_deleted=False
    ).first()
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("web.projects"))

    categories_query = Category.query.filter_by(
        tenant_id=tenant_id, project_id=project.id, is_deleted=False
    )
    categories = categories_query.order_by(Category.name).all()

    if request.method == "POST":
        try:
            name = (request.form.get("name") or "").strip()
            if not name:
                raise ValueError("Category name is required.")
            color = request.form.get("color") or "#6366F1"

            category = Category(
                tenant_id=tenant_id,
                project_id=project.id,
                name=name,
                description=request.form.get("description") or None,
                color=color,
                icon=request.form.get("icon") or None,
                created_by=current_user.id,
            )
            db.session.add(category)
            db.session.commit()
            flash("Category created.", "success")
            return redirect(url_for("web.project_categories", project_id=project.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not create category: {exc}", "error")

    return render_template(
        "projects/categories.html",
        project=project,
        categories=categories,
    )


@bp.route("/projects/<project_id>/categories/<category_id>", methods=["POST"])
@login_required
def project_category_update(project_id, category_id):
    """Update a category within a project."""
    from app.models.project import Project
    from app.models.category import Category

    tenant_id = current_user.tenant_id
    project = Project.query.filter_by(
        id=project_id, tenant_id=tenant_id, is_deleted=False
    ).first()
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("web.projects"))

    category = Category.query.filter_by(
        id=category_id, tenant_id=tenant_id, project_id=project.id, is_deleted=False
    ).first()
    if not category:
        flash("Category not found.", "error")
        return redirect(url_for("web.project_categories", project_id=project_id))

    try:
        category.name = (request.form.get("name") or category.name).strip() or category.name
        category.color = request.form.get("color") or category.color
        category.icon = request.form.get("icon") or None
        category.description = request.form.get("description") or None
        category.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        flash("Category updated.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not update category: {exc}", "error")

    return redirect(url_for("web.project_categories", project_id=project.id))


@bp.route("/projects/<project_id>/categories/json")
@login_required
def project_categories_json(project_id):
    """Return categories for a project (for dependent dropdowns)."""
    from app.models.project import Project
    from app.models.category import Category

    tenant_id = current_user.tenant_id
    project = Project.query.filter_by(
        id=project_id, tenant_id=tenant_id, is_deleted=False
    ).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    categories = Category.query.filter_by(
        tenant_id=tenant_id, project_id=project.id, is_deleted=False
    ).order_by(Category.name).all()

    return jsonify(
        [
            {
                "id": category.id,
                "name": category.name,
                "color": category.color,
                "icon": category.icon,
                "is_active": category.is_active,
            }
            for category in categories
        ]
    )


@bp.route("/forgot-password")
def forgot_password():
    """Forgot password page."""
    return render_template("auth/forgot_password.html")


@bp.route("/expenses")
@login_required
def expenses():
    """Expenses list page."""
    from app.models.expense import Expense
    from app.models.project import Project
    from app.models.account import Account
    from app.models.category import Category

    tenant_id = current_user.tenant_id

    # Base query
    query = Expense.query.filter_by(
        tenant_id=tenant_id,
        is_deleted=False,
    )

    # Filters
    project_id = request.args.get("project_id") or None
    category_id = request.args.get("category_id") or None
    account_id = request.args.get("account_id") or None
    min_amount = request.args.get("min_amount") or None
    max_amount = request.args.get("max_amount") or None
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None

    if project_id:
        query = query.filter(Expense.project_id == project_id)
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if account_id:
        query = query.filter(Expense.account_id == account_id)
    if min_amount:
        try:
            query = query.filter(Expense.amount >= Decimal(min_amount))
        except Exception:
            flash("Invalid minimum amount", "error")
    if max_amount:
        try:
            query = query.filter(Expense.amount <= Decimal(max_amount))
        except Exception:
            flash("Invalid maximum amount", "error")
    if start_date:
        try:
            query = query.filter(Expense.expense_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
        except Exception:
            flash("Invalid start date", "error")
    if end_date:
        try:
            query = query.filter(Expense.expense_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
        except Exception:
            flash("Invalid end date", "error")

    # Pagination
    try:
        page = int(request.args.get("page", 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get("per_page", 25))
    except Exception:
        per_page = 25
    per_page = max(1, min(per_page, 100))

    pagination = query.order_by(Expense.expense_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    expenses = pagination.items

    projects = Project.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Project.name).all()
    categories_query = Category.query.filter_by(tenant_id=tenant_id, is_deleted=False)
    if project_id:
        categories_query = categories_query.filter_by(project_id=project_id)
    categories = categories_query.order_by(Category.name).all()
    accounts = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Account.name).all()

    return render_template(
        "expenses/list.html",
        expenses=expenses,
        projects=projects,
        categories=categories,
        accounts=accounts,
        pagination=pagination,
        filters={
            "project_id": project_id,
            "category_id": category_id,
            "account_id": account_id,
            "min_amount": min_amount or "",
            "max_amount": max_amount or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
            "per_page": per_page,
        },
    )


@bp.route("/expenses/new", methods=["GET", "POST"])
@login_required
def expense_new():
    """Create a new expense."""
    from app.models.expense import Expense
    from app.models.account import Account
    from app.models.category import Category
    from app.models.project import Project

    tenant_id = current_user.tenant_id
    tenant_currency, _ = get_tenant_preferences()
    accounts_query = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False)
    projects = Project.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Project.name).all()
    categories_query = Category.query.filter_by(tenant_id=tenant_id, is_deleted=False)
    initial_project_id = request.args.get("project_id") or None
    selected_project_id = initial_project_id
    categories = []
    if selected_project_id:
        categories = categories_query.filter_by(project_id=selected_project_id).order_by(Category.name).all()

    # If the expense is tied to a project, restrict accounts based on allowed list from Redis
    allowed_account_ids = None
    if initial_project_id:
        allowed_str = current_app.redis.get(f"project:{initial_project_id}:accounts")
        if allowed_str:
            allowed_account_ids = [aid for aid in allowed_str.split(",") if aid]
            if allowed_account_ids:
                accounts_query = accounts_query.filter(Account.id.in_(allowed_account_ids))

    accounts = ensure_accounts_use_tenant_currency(
        accounts_query.order_by(Account.name).all(),
        tenant_currency,
    )

    if request.method == "POST":
        try:
            amount_raw = request.form.get("amount", "").strip()
            if not amount_raw:
                raise ValueError("Amount is required.")
            amount = Decimal(amount_raw)
            expense_date_str = request.form.get("expense_date")
            if not expense_date_str:
                raise ValueError("Date is required.")
            expense_date_val = datetime.strptime(expense_date_str, "%Y-%m-%d").date()

            account_id = request.form.get("account_id")
            if not account_id:
                raise ValueError("Account is required.")

            project_id = request.form.get("project_id") or None
            selected_project_id = project_id
            category_id = request.form.get("category_id") or None
            if category_id and not project_id:
                raise ValueError("Select a project before assigning a category.")
            if category_id and project_id:
                valid_category = Category.query.filter_by(
                    id=category_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    is_deleted=False,
                ).first()
                if not valid_category:
                    raise ValueError("Category must belong to the selected project.")

            expense = Expense(
                tenant_id=tenant_id,
                amount=amount,
                currency=request.form.get("currency", "USD"),
                vendor=request.form.get("vendor") or None,
                note=request.form.get("note") or None,
                category_id=category_id,
                project_id=project_id,
                is_project_related=bool(project_id),
                account_id=account_id,
                expense_date=expense_date_val,
                payment_method=request.form.get("payment_method", "cash"),
                status="submitted",
                created_by=current_user.id,
            )
            new_attachments = _prepare_image_attachments(request.files.getlist("attachments"))
            if new_attachments:
                expense.attachments = new_attachments

            db.session.add(expense)
            db.session.commit()
            flash("Expense added successfully.", "success")
            return redirect(url_for("web.expenses"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save expense: {exc}", "error")

    accounts_query = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False)
    if selected_project_id:
        allowed_str = current_app.redis.get(f"project:{selected_project_id}:accounts")
        if allowed_str:
            allowed_account_ids = [aid for aid in allowed_str.split(",") if aid]
            if allowed_account_ids:
                accounts_query = accounts_query.filter(Account.id.in_(allowed_account_ids))
    accounts = ensure_accounts_use_tenant_currency(
        accounts_query.order_by(Account.name).all(),
        tenant_currency,
    )

    if selected_project_id:
        categories = categories_query.filter_by(project_id=selected_project_id).order_by(Category.name).all()
    else:
        categories = []

    return render_template(
        "expenses/new.html",
        accounts=accounts,
        categories=categories,
        projects=projects,
        today=date.today().isoformat(),
        initial_project_id=initial_project_id,
        account_meta=[{"id": a.id, "currency": a.currency, "name": a.name, "type": a.account_type} for a in accounts],
        tenant_currency=tenant_currency,
    )


@bp.route("/expenses/<expense_id>")
@login_required
def expense_detail(expense_id):
    """Expense detail page with attachment previews."""
    from app.models.expense import Expense

    tenant_id = current_user.tenant_id
    expense = Expense.query.filter_by(id=expense_id, tenant_id=tenant_id, is_deleted=False).first()
    if not expense:
        flash("Expense not found.", "error")
        return redirect(url_for("web.expenses"))

    return render_template("expenses/detail.html", expense=expense)


@bp.route("/expenses/<expense_id>/edit", methods=["GET", "POST"])
@login_required
def expense_edit(expense_id):
    """Edit an expense with metadata indicator."""
    from app.models.expense import Expense
    from app.models.account import Account
    from app.models.category import Category
    from app.models.project import Project
    from app.models.user import User

    tenant_id = current_user.tenant_id
    tenant_currency, _ = get_tenant_preferences()
    expense = Expense.query.filter_by(id=expense_id, tenant_id=tenant_id, is_deleted=False).first()
    if not expense:
        flash("Expense not found.", "error")
        return redirect(url_for("web.expenses"))

    projects = Project.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Project.name).all()
    categories_query = Category.query.filter_by(tenant_id=tenant_id, is_deleted=False)
    selected_project_id = expense.project_id
    categories = []
    if selected_project_id:
        categories = categories_query.filter_by(project_id=selected_project_id).order_by(Category.name).all()

    # Determine allowed accounts based on selected project
    accounts_query = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False)
    if selected_project_id:
        allowed_str = current_app.redis.get(f"project:{selected_project_id}:accounts")
        if allowed_str:
            allowed_ids = [aid for aid in allowed_str.split(",") if aid]
            if allowed_ids:
                accounts_query = accounts_query.filter(Account.id.in_(allowed_ids))
    accounts = ensure_accounts_use_tenant_currency(
        accounts_query.order_by(Account.name).all(),
        tenant_currency,
    )

    if request.method == "POST":
        try:
            old_amount = float(expense.amount)
            old_account_id = expense.account_id

            project_id = request.form.get("project_id") or None
            selected_project_id = project_id
            # Refresh allowed accounts when project changed
            accounts_query = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False)
            if project_id:
                allowed_str = current_app.redis.get(f"project:{project_id}:accounts")
                if allowed_str:
                    allowed_ids = [aid for aid in allowed_str.split(",") if aid]
                    if allowed_ids:
                        accounts_query = accounts_query.filter(Account.id.in_(allowed_ids))
            accounts = ensure_accounts_use_tenant_currency(
                accounts_query.order_by(Account.name).all(),
                tenant_currency,
            )

            expense.vendor = request.form.get("vendor") or None
            expense.note = request.form.get("note") or None
            expense.amount = Decimal(request.form.get("amount", expense.amount))
            expense.currency = request.form.get("currency", expense.currency)
            expense.expense_date = datetime.strptime(request.form["expense_date"], "%Y-%m-%d").date()
            category_id = request.form.get("category_id") or None
            if category_id and not project_id:
                raise ValueError("Select a project before assigning a category.")
            if category_id and project_id:
                valid_category = Category.query.filter_by(
                    id=category_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    is_deleted=False,
                ).first()
                if not valid_category:
                    raise ValueError("Category must belong to the selected project.")
            expense.category_id = category_id
            expense.project_id = project_id
            expense.is_project_related = bool(project_id)
            expense.account_id = request.form.get("account_id") or None
            expense.payment_method = request.form.get("payment_method", expense.payment_method)
            new_attachments = _prepare_image_attachments(request.files.getlist("attachments"))
            if new_attachments:
                existing_attachments = expense.attachments or []
                expense.attachments = existing_attachments + new_attachments

            # Mark edited metadata
            meta = expense.expense_metadata or {}
            display_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
            meta.update(
                {
                    "edited": True,
                    "last_amount": old_amount,
                    "last_account_id": old_account_id,
                    "last_updated_by": current_user.id,
                    "last_updated_by_name": display_name,
                    "last_updated_at": datetime.utcnow().isoformat(),
                }
            )
            expense.expense_metadata = meta
            expense.updated_by = current_user.id

            db.session.commit()
            flash("Expense updated successfully.", "success")
            return redirect(url_for("web.expenses"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update expense: {exc}", "error")

    if selected_project_id:
        categories = categories_query.filter_by(project_id=selected_project_id).order_by(Category.name).all()
    else:
        categories = []

    return render_template(
        "expenses/edit.html",
        expense=expense,
        accounts=accounts,
        categories=categories,
        projects=projects,
        account_meta=[{"id": a.id, "currency": a.currency, "name": a.name, "type": a.account_type} for a in accounts],
        tenant_currency=tenant_currency,
    )


@bp.route("/accounts")
@login_required
def accounts():
    """Accounts list page."""
    from app.models.account import Account
    from sqlalchemy import func
    from app.models.expense import Expense

    tenant_id = current_user.tenant_id

    # Get all accounts with expense counts
    accounts_list = Account.query.filter_by(
        tenant_id=tenant_id,
        is_deleted=False
    ).order_by(Account.is_active.desc(), Account.name).all()

    # Get total expenses per account
    expense_totals = db.session.query(
        Expense.account_id,
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.tenant_id == tenant_id,
        Expense.is_deleted == False
    ).group_by(Expense.account_id).all()

    expense_dict = {str(row[0]): float(row[1]) for row in expense_totals}

    return render_template("accounts/list.html", 
                         accounts=accounts_list,
                         expense_totals=expense_dict)


@bp.route("/accounts/<account_id>/transactions")
@login_required
def account_transactions(account_id):
    """Return recent account transactions (credits and expenses)."""
    from app.models.account import Account
    from app.models.expense import Expense
    from sqlalchemy import func

    tenant_id = current_user.tenant_id
    kind = request.args.get("kind", "both")  # expenses, topups, both

    account = Account.query.filter_by(
        id=account_id,
        tenant_id=tenant_id,
        is_deleted=False
    ).first()

    if not account:
        return jsonify({"error": "Account not found"}), 404

    # Expenses (debits)
    expense_query = Expense.query.filter_by(
        tenant_id=tenant_id,
        account_id=account.id,
        is_deleted=False,
    ).order_by(Expense.expense_date.desc(), Expense.created_at.desc())

    expenses = []
    if kind in ("both", "expenses"):
        expenses = [
            {
                "type": "expense",
                "date": exp.expense_date.isoformat() if exp.expense_date else "",
                "label": exp.vendor or exp.note or "Expense",
                "amount": float(exp.amount),
                "category": exp.category.name if exp.category else None,
            }
            for exp in expense_query.limit(200).all()
        ]

    # Estimate top-ups as the delta between balance + expenses and opening balance
    topups = []
    if kind in ("both", "topups"):
        total_expense_amount = (
            db.session.query(func.sum(Expense.amount))
            .filter(
                Expense.tenant_id == tenant_id,
                Expense.account_id == account.id,
                Expense.is_deleted == False,
            )
            .scalar()
            or 0
        )
        estimated_topups = float(account.current_balance - account.opening_balance + total_expense_amount)
        if estimated_topups > 0:
            topups = [
                {
                    "type": "topup",
                    "date": (account.updated_at or account.created_at).date().isoformat(),
                    "label": "Account Top-up",
                    "amount": estimated_topups,
                    "category": None,
                }
            ]

    transactions = topups + expenses

    return jsonify(
        {
            "account": {"id": account.id, "name": account.name, "currency": account.currency},
            "transactions": transactions,
        }
    )


@bp.route("/accounts/new", methods=["GET", "POST"])
@login_required
def account_new():
    """Create new account."""
    from app.models.account import Account

    tenant_currency, _ = get_tenant_preferences()

    if request.method == "POST":
        try:
            opening_balance = Decimal(request.form.get("opening_balance", "0") or "0")
            threshold = request.form.get("low_balance_threshold")
            
            account = Account(
                tenant_id=current_user.tenant_id,
                name=request.form.get("name"),
                account_type=request.form.get("account_type", "cash"),
                currency=tenant_currency,
                opening_balance=opening_balance,
                current_balance=opening_balance,
                low_balance_threshold=Decimal(threshold) if threshold else None,
                description=request.form.get("description"),
                account_number_last4=request.form.get("account_number_last4"),
                created_by=current_user.id
            )
            db.session.add(account)
            db.session.commit()
            flash(f"Account '{account.name}' created successfully.", "success")
            return redirect(url_for("web.accounts"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error creating account: {str(exc)}", "error")
    
    return render_template("accounts/new.html", tenant_currency=tenant_currency)


@bp.route("/accounts/<account_id>/adjust", methods=["GET", "POST"])
@login_required
def account_adjust(account_id):
    """Adjust account balance (add/withdraw funds)."""
    from app.models.account import Account

    tenant_currency, _ = get_tenant_preferences()

    account = Account.query.filter_by(
        id=account_id,
        tenant_id=current_user.tenant_id,
        is_deleted=False
    ).first()

    if not account:
        flash("Account not found.", "error")
        return redirect(url_for("web.accounts"))

    # Normalize any legacy account currencies to the tenant currency
    if account.currency != tenant_currency:
        account.currency = tenant_currency
        db.session.commit()

    if request.method == "POST":
        try:
            adjustment_type = request.form.get("adjustment_type")
            amount = Decimal(request.form.get("amount", "0"))
            note = request.form.get("note")

            if adjustment_type == "add":
                account.credit(amount, commit=False)
                flash_msg = f"Added {account.currency} {amount} to {account.name}"
            elif adjustment_type == "withdraw":
                account.debit(amount, commit=False)
                flash_msg = f"Withdrew {account.currency} {amount} from {account.name}"
            else:
                raise ValueError("Invalid adjustment type")

            db.session.commit()
            flash(flash_msg, "success")
            return redirect(url_for("web.accounts"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error adjusting balance: {str(exc)}", "error")

    return render_template("accounts/adjust.html", account=account)


@bp.route("/alerts")
@login_required
def alerts():
    """Alert center page."""
    from app.models.alert import Alert

    alerts = Alert.query.filter_by(
        tenant_id=current_user.tenant_id,
        is_deleted=False,
    ).order_by(Alert.created_at.desc()).limit(20).all()

    return render_template("alerts/list.html", alerts=alerts)


@bp.route("/reports/project/<project_id>/summary")
@login_required
def project_summary_report(project_id):
    """Project summary report page."""
    return render_template("reports/project_summary.html", project_id=project_id)


@bp.route("/reports/project/<project_id>/category-breakdown")
@login_required
def category_breakdown_report(project_id):
    """Category breakdown report page."""
    return render_template("reports/category_breakdown.html", project_id=project_id)


@bp.route("/reports/project/<project_id>/monthly-trend")
@login_required
def monthly_trend_report(project_id):
    """Monthly trend report page."""
    return render_template("reports/monthly_trend.html", project_id=project_id)


@bp.route("/reports/cashflow")
@login_required
def cashflow_report():
    """Tenant cashflow report page."""
    return render_template("reports/cashflow.html")
