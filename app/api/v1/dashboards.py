"""Dashboards API endpoints."""
from collections import defaultdict
from decimal import Decimal
from datetime import date
from datetime import timedelta

from flask import jsonify, g
from flask.views import MethodView
from flask_login import login_required, current_user
from flask_smorest import Blueprint
from loguru import logger
from sqlalchemy import func, extract

from app.core.extensions import db
from app.middleware.tenancy import TenancyMiddleware
from app.models.account import Account
from app.models.category import Category
from app.models.expense import Expense
from app.models.project import Project

bp = Blueprint("dashboards", __name__, url_prefix="/dashboards", description="Dashboard analytics")
# Alias to keep registration consistent with other blueprints
blp = bp


def _get_tenant_id():
    """Resolve tenant id from request context or current user."""
    tenant_id = g.get("tenant_id")
    if not tenant_id and current_user and getattr(current_user, "is_authenticated", False):
        tenant_id = current_user.tenant_id
    return tenant_id


@bp.route("/project/<string:project_id>")
class ProjectDashboard(MethodView):
    """Project-specific dashboard data."""

    @login_required
    @TenancyMiddleware.require_tenant()
    def get(self, project_id):
        """
        Get project dashboard with aggregates.
        
        Returns:
            - totals: starting_budget, projected_estimate, total_spend, remaining_budget
            - per-account balances
            - category breakdown
            - monthly trend
            - forecast vs actual
        """
        tenant_id = _get_tenant_id()
        if not tenant_id:
            return jsonify({"error": "Tenant context required"}), 400

        project = (
            db.session.query(Project)
            .filter_by(id=project_id, tenant_id=tenant_id, is_deleted=False)
            .first()
        )
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Totals
        total_spend = (
            db.session.query(func.sum(Expense.amount))
            .filter(
                Expense.tenant_id == tenant_id,
                Expense.project_id == project.id,
                Expense.is_deleted == False,
            )
            .scalar()
            or Decimal("0.00")
        )
        remaining_budget = Decimal(project.starting_budget) - Decimal(total_spend)
        budget_utilization = float((total_spend / project.starting_budget) * 100) if project.starting_budget else 0.0
        days_remaining = project.days_remaining
        days_elapsed = project.days_elapsed or 1
        burn_rate = float(total_spend) / float(days_elapsed) if days_elapsed else 0.0

        # Accounts snapshot
        accounts = (
            db.session.query(Account)
            .filter_by(tenant_id=tenant_id, is_deleted=False)
            .order_by(Account.name)
            .all()
        )

        # Category breakdown
        category_rows = (
            db.session.query(Category.name, func.sum(Expense.amount))
            .join(Expense, Expense.category_id == Category.id)
            .filter(
                Expense.tenant_id == tenant_id,
                Expense.project_id == project.id,
                Expense.is_deleted == False,
            )
            .group_by(Category.name)
            .all()
        )
        category_labels = [row[0] for row in category_rows]
        category_data = [float(row[1]) for row in category_rows]

        # Fallback so charts render even if there are no categories
        if not category_labels and total_spend:
            category_labels = ["Uncategorized"]
            category_data = [float(total_spend)]

        # Monthly trend grouped by account
        month_rows = (
            db.session.query(
                extract("year", Expense.expense_date).label("y"),
                extract("month", Expense.expense_date).label("m"),
                Account.name.label("account"),
                func.sum(Expense.amount).label("total"),
            )
            .join(Account, Account.id == Expense.account_id)
            .filter(
                Expense.tenant_id == tenant_id,
                Expense.project_id == project.id,
                Expense.is_deleted == False,
            )
            .group_by("y", "m", "account")
            .order_by("y", "m")
            .all()
        )

        month_totals = defaultdict(dict)
        for row in month_rows:
            ym = f"{int(row.y):04d}-{int(row.m):02d}"
            month_totals[ym][row.account] = float(row.total)

        sorted_months = sorted(month_totals.keys())
        datasets = []
        if sorted_months:
            accounts_seen = set()
            for _, account_totals in month_totals.items():
                accounts_seen.update(account_totals.keys())
            for account_name in sorted(accounts_seen):
                datasets.append(
                    {
                        "label": account_name,
                        "data": [month_totals[month].get(account_name, 0.0) for month in sorted_months],
                    }
                )

        # Forecast vs actual (simple projection using projected_estimate or starting_budget)
        forecast_labels = sorted_months
        cumulative_actual = []
        running = 0.0
        for month in forecast_labels:
            running += sum(month_totals[month].values())
            cumulative_actual.append(running)
        forecast_total = float(project.projected_estimate or project.starting_budget or 0)
        forecast_line = [forecast_total for _ in forecast_labels] if forecast_labels else []

        # Fallback for empty monthly trend: collapse totals by account into a single bar
        if not forecast_labels:
            acct_totals = (
                db.session.query(Account.name, func.sum(Expense.amount))
                .join(Expense, Expense.account_id == Account.id)
                .filter(
                    Expense.tenant_id == tenant_id,
                    Expense.project_id == project.id,
                    Expense.is_deleted == False,
                )
                .group_by(Account.name)
                .all()
            )
            if acct_totals:
                forecast_labels = ["Total"]
                datasets = [
                    {"label": name, "data": [float(total)]} for name, total in acct_totals
                ]
                cumulative_actual = [float(total_spend)]
                forecast_line = [forecast_total] if forecast_total else [float(total_spend)]
            elif total_spend:
                forecast_labels = ["Total"]
                datasets = [{"label": "All Accounts", "data": [float(total_spend)]}]
                cumulative_actual = [float(total_spend)]
                forecast_line = [forecast_total] if forecast_total else [float(total_spend)]

        # ------------------------------------------------------------------
        # Additional insights (spend velocity, runway, vendors, recents)
        # ------------------------------------------------------------------
        today = date.today()
        start_30d = today - timedelta(days=29)

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

        total_spend_float = float(total_spend or 0)
        top_category_name = None
        top_category_share = None
        if category_rows and total_spend_float > 0:
            top_category_name, top_category_total = max(category_rows, key=lambda x: float(x[1] or 0))
            top_category_share = (float(top_category_total or 0) / total_spend_float) * 100.0

        projected_end_total = None
        projected_end_variance = None
        project_total_days = (project.days_elapsed or 0) + (project.days_remaining or 0)
        if project_total_days > 0:
            projected_end_total = float(burn_rate) * float(project_total_days)
            projected_end_variance = projected_end_total - float(project.starting_budget or 0)

        data = {
            "project": {
                "id": project.id,
                "name": project.name,
                "starting_budget": float(project.starting_budget),
                "projected_estimate": float(project.projected_estimate),
                "total_spend": float(total_spend),
                "remaining_budget": float(remaining_budget),
                "budget_utilization": budget_utilization,
                "is_over_budget": remaining_budget < 0,
                "days_remaining": days_remaining if days_remaining is not None else 0,
                "burn_rate": burn_rate,
                "forecast": {
                    "projected_total": forecast_total,
                    "confidence": 75,
                    "variance": float(forecast_total - float(total_spend)),
                    "will_exceed": remaining_budget < 0,
                },
            },
            # Flat aliases for the dashboard JS/template (server-rendered data is flat)
            "starting_budget": float(project.starting_budget),
            "projected_estimate": float(project.projected_estimate),
            "total_spend": float(total_spend),
            "remaining_budget": float(remaining_budget),
            "budget_utilization": budget_utilization,
            "is_over_budget": remaining_budget < 0,
            "days_remaining": days_remaining if days_remaining is not None else 0,
            "burn_rate": burn_rate,
            "forecast": {
                "projected_total": forecast_total,
                "confidence": 75,
                "variance": float(forecast_total - float(total_spend)),
            },
            "insights": {
                "spend_7d": spend_7d,
                "spend_30d": spend_30d,
                "avg_daily_7d": avg_daily_7d,
                "avg_daily_30d": avg_daily_30d,
                "runway_days": runway_days,
                "spend_mtd": float(spend_mtd or 0),
                "spend_prev_month": float(spend_prev_month or 0),
                "mtd_change_pct": mtd_change_pct,
                "top_category_name": top_category_name,
                "top_category_share": top_category_share,
                "projected_end_total": projected_end_total,
                "projected_end_variance": projected_end_variance,
                "biggest_expense": biggest_expense,
            },
            "daily_spend": {"labels": daily_labels, "data": daily_data},
            "top_vendors": {"labels": top_vendor_labels, "data": top_vendor_data},
            "recent_expenses": recent_expenses,
            "accounts": [
                {
                    "id": account.id,
                    "name": account.name,
                    "type": account.account_type,
                    "current_balance": float(account.current_balance or 0),
                    "low_balance_threshold": float(account.low_balance_threshold or 0),
                    "currency": account.currency or "USD",
                }
                for account in accounts
            ],
            "category_breakdown": {
                "labels": category_labels,
                "data": category_data,
            },
            "monthly_trend": {
                "labels": forecast_labels,
                "datasets": datasets,
            },
            "forecast_vs_actual": {
                "labels": forecast_labels,
                "datasets": [
                    {"label": "Actual", "data": cumulative_actual},
                    {"label": "Forecast", "data": forecast_line},
                ],
            },
        }

        return jsonify(data), 200


@bp.route("/tenant")
class TenantDashboard(MethodView):
    """Tenant-wide dashboard data."""

    @login_required
    @TenancyMiddleware.require_tenant()
    def get(self):
        """
        Get tenant-wide dashboard.
        
        Returns:
            - total_spend
            - top vendors
            - low-balance accounts
            - alert counts
        """
        tenant_id = _get_tenant_id()
        if not tenant_id:
            return jsonify({"error": "Tenant context required"}), 400

        total_spend = (
            db.session.query(func.sum(Expense.amount))
            .filter(Expense.tenant_id == tenant_id, Expense.is_deleted == False)
            .scalar()
            or 0
        )

        top_vendors = (
            db.session.query(Expense.vendor, func.sum(Expense.amount))
            .filter(Expense.tenant_id == tenant_id, Expense.is_deleted == False, Expense.vendor != None)
            .group_by(Expense.vendor)
            .order_by(func.sum(Expense.amount).desc())
            .limit(5)
            .all()
        )

        low_balance_accounts = (
            db.session.query(Account)
            .filter(
                Account.tenant_id == tenant_id,
                Account.is_deleted == False,
                Account.current_balance <= Account.low_balance_threshold,
            )
            .all()
        )

        # Projects ending soon (next 14 days)
        today = date.today()
        soon = today + timedelta(days=14)
        projects_ending_soon = (
            db.session.query(Project)
            .filter(
                Project.tenant_id == tenant_id,
                Project.is_deleted == False,
                Project.end_date != None,
                Project.end_date >= today,
                Project.end_date <= soon,
            )
            .all()
        )

        # Over-budget projects (total spend exceeds starting budget)
        spend_by_project = dict(
            db.session.query(Project.id, func.coalesce(func.sum(Expense.amount), 0))
            .join(Expense, Expense.project_id == Project.id)
            .filter(
                Expense.tenant_id == tenant_id,
                Expense.is_deleted == False,
            )
            .group_by(Project.id)
            .all()
        )
        project_budgets = dict(
            db.session.query(Project.id, Project.starting_budget)
            .filter(Project.tenant_id == tenant_id, Project.is_deleted == False)
            .all()
        )
        over_budget_projects = [
            pid
            for pid, total in spend_by_project.items()
            if pid in project_budgets and float(total or 0) > float(project_budgets[pid] or 0)
        ]

        alert_total = len(low_balance_accounts) + len(projects_ending_soon) + len(over_budget_projects)

        return jsonify(
            {
                "total_spend": float(total_spend),
                "top_vendors": [{"vendor": v[0], "total": float(v[1])} for v in top_vendors],
                "low_balance_accounts": [
                {
                    "id": a.id,
                    "name": a.name,
                    "current_balance": float(a.current_balance or 0),
                    "threshold": float(a.low_balance_threshold or 0),
                    }
                    for a in low_balance_accounts
                ],
                "alerts": {
                    "total": alert_total,
                    "unread": alert_total,  # mirror total for now
                    "breakdown": {
                        "low_balance_accounts": len(low_balance_accounts),
                        "projects_ending_soon": len(projects_ending_soon),
                        "over_budget_projects": len(over_budget_projects),
                    },
                },
            }
        ), 200
