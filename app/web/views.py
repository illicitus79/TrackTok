"""Web views for server-rendered pages."""
from datetime import datetime, date
from decimal import Decimal

from flask import render_template, redirect, url_for, request, flash, session, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, set_access_cookies
from flask_login import logout_user, login_user, login_required, current_user

from app.web import bp
from app.web.forms import LoginForm, RegistrationForm
from app.models.user import User
from app.core.extensions import db


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
    from app.models.budget import Budget
    
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
@login_required
def profile():
    """User profile page."""
    return render_template("profile.html")


@bp.route("/settings")
@login_required
def settings():
    """User settings page."""
    return render_template("settings.html")


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

    dashboard_data = {
        'starting_budget': float(project.starting_budget or 0),
        'projected_estimate': float(project.projected_estimate or 0),
        'total_spend': float(total_spend),
        'remaining_budget': float(remaining_budget),
        'budget_utilization': budget_utilization,
        'is_over_budget': remaining_budget < 0,
        'days_remaining': project.days_remaining or 0,
        'burn_rate': burn_rate,
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

    expenses = query.order_by(Expense.expense_date.desc()).limit(200).all()

    projects = Project.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Project.name).all()
    categories = Category.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Category.name).all()
    accounts = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False).order_by(Account.name).all()

    return render_template(
        "expenses/list.html",
        expenses=expenses,
        projects=projects,
        categories=categories,
        accounts=accounts,
        filters={
            "project_id": project_id,
            "category_id": category_id,
            "account_id": account_id,
            "min_amount": min_amount or "",
            "max_amount": max_amount or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
        },
    )


@bp.route("/expenses/new", methods=["GET", "POST"])
@login_required
def expense_new():
    """Create a new expense."""
    from app.models.expense import Expense
    from app.models.account import Account
    from app.models.category import Category

    tenant_id = current_user.tenant_id
    accounts = Account.query.filter_by(tenant_id=tenant_id, is_deleted=False).all()
    categories = Category.query.filter_by(tenant_id=tenant_id, is_deleted=False).all()

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

            expense = Expense(
                tenant_id=tenant_id,
                amount=amount,
                currency=request.form.get("currency", "USD"),
                vendor=request.form.get("vendor") or None,
                note=request.form.get("note") or None,
                category_id=request.form.get("category_id") or None,
                project_id=request.args.get("project_id") or None,
                is_project_related=bool(request.args.get("project_id")),
                account_id=account_id,
                expense_date=expense_date_val,
                payment_method=request.form.get("payment_method", "cash"),
                status="submitted",
                created_by=current_user.id,
            )
            db.session.add(expense)
            db.session.commit()
            flash("Expense added successfully.", "success")
            return redirect(url_for("web.expenses"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save expense: {exc}", "error")

    return render_template(
        "expenses/new.html",
        accounts=accounts,
        categories=categories,
        today=date.today().isoformat(),
    )


@bp.route("/budgets")
@login_required
def budgets():
    """Budgets page."""
    from app.models.budget import Budget

    budgets = Budget.query.filter_by(
        tenant_id=current_user.tenant_id,
        is_deleted=False,
    ).order_by(Budget.start_date.desc()).all()

    return render_template("budgets/list.html", budgets=budgets)


@bp.route("/budgets/new", methods=["GET", "POST"])
@login_required
def budget_new():
    """Create a new budget."""
    from app.models.budget import Budget
    from app.models.category import Category

    tenant_id = current_user.tenant_id
    categories = Category.query.filter_by(tenant_id=tenant_id, is_deleted=False).all()

    if request.method == "POST":
        try:
            amount_raw = request.form.get("amount", "").strip()
            if not amount_raw:
                raise ValueError("Amount is required.")
            amount = Decimal(amount_raw)
            start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()

            budget = Budget(
                tenant_id=tenant_id,
                name=request.form.get("name", "Untitled budget"),
                description=request.form.get("description") or None,
                amount=amount,
                currency=request.form.get("currency", "USD"),
                period=request.form.get("period", "monthly"),
                start_date=start_date,
                end_date=end_date,
                category_id=request.form.get("category_id") or None,
                alert_threshold=int(request.form.get("alert_threshold", 80)),
                alert_enabled=bool(request.form.get("alert_enabled")),
                owner_id=current_user.id,
            )
            db.session.add(budget)
            db.session.commit()
            flash("Budget created.", "success")
            return redirect(url_for("web.budgets"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not create budget: {exc}", "error")

    return render_template("budgets/form.html", categories=categories, mode="create", today=date.today().isoformat())


@bp.route("/budgets/<budget_id>/edit", methods=["GET", "POST"])
@login_required
def budget_edit(budget_id):
    """Edit an existing budget."""
    from app.models.budget import Budget
    from app.models.category import Category

    tenant_id = current_user.tenant_id
    budget = Budget.query.filter_by(id=budget_id, tenant_id=tenant_id, is_deleted=False).first()
    if not budget:
        flash("Budget not found.", "error")
        return redirect(url_for("web.budgets"))

    categories = Category.query.filter_by(tenant_id=tenant_id, is_deleted=False).all()

    if request.method == "POST":
        try:
            budget.name = request.form.get("name", budget.name)
            budget.description = request.form.get("description") or None
            budget.amount = Decimal(request.form.get("amount", budget.amount))
            budget.currency = request.form.get("currency", budget.currency)
            budget.period = request.form.get("period", budget.period)
            budget.start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
            budget.end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()
            budget.category_id = request.form.get("category_id") or None
            budget.alert_threshold = int(request.form.get("alert_threshold", budget.alert_threshold))
            budget.alert_enabled = bool(request.form.get("alert_enabled"))
            db.session.commit()
            flash("Budget updated.", "success")
            return redirect(url_for("web.budgets"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update budget: {exc}", "error")

    return render_template("budgets/form.html", categories=categories, budget=budget, mode="edit", today=date.today().isoformat())


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


@bp.route("/accounts/new", methods=["GET", "POST"])
@login_required
def account_new():
    """Create new account."""
    from app.models.account import Account

    if request.method == "POST":
        try:
            opening_balance = Decimal(request.form.get("opening_balance", "0") or "0")
            threshold = request.form.get("low_balance_threshold")
            
            account = Account(
                tenant_id=current_user.tenant_id,
                name=request.form.get("name"),
                account_type=request.form.get("account_type", "cash"),
                currency=request.form.get("currency", "USD"),
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
    
    return render_template("accounts/new.html")


@bp.route("/accounts/<account_id>/adjust", methods=["GET", "POST"])
@login_required
def account_adjust(account_id):
    """Adjust account balance (add/withdraw funds)."""
    from app.models.account import Account

    account = Account.query.filter_by(
        id=account_id,
        tenant_id=current_user.tenant_id,
        is_deleted=False
    ).first()

    if not account:
        flash("Account not found.", "error")
        return redirect(url_for("web.accounts"))

    if request.method == "POST":
        try:
            adjustment_type = request.form.get("adjustment_type")
            amount = Decimal(request.form.get("amount", "0"))
            note = request.form.get("note")

            if adjustment_type == "add":
                account.credit(amount, commit=False)
                flash_msg = f"Added ${amount} to {account.name}"
            elif adjustment_type == "withdraw":
                account.debit(amount, commit=False)
                flash_msg = f"Withdrew ${amount} from {account.name}"
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
