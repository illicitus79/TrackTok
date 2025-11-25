"""Report generation tasks."""
from datetime import datetime, timedelta

from loguru import logger

from app.models.tenant import Tenant
from app.tasks.celery_app import celery


@celery.task(name="app.tasks.reports.generate_monthly_reports")
def generate_monthly_reports():
    """
    Generate monthly expense reports for all tenants.
    
    Runs on the 1st of each month.
    """
    logger.info("Starting monthly report generation")

    tenants = Tenant.query.filter_by(is_active=True).all()

    total_reports = 0

    for tenant in tenants:
        try:
            # Generate report for previous month
            last_month = datetime.utcnow().replace(day=1) - timedelta(days=1)

            generate_tenant_monthly_report.delay(tenant.id, last_month.year, last_month.month)

            total_reports += 1

        except Exception as e:
            logger.error(f"Error scheduling report for tenant {tenant.id}: {e}")
            continue

    logger.info(f"Scheduled {total_reports} monthly reports")

    return {"reports_scheduled": total_reports}


@celery.task(name="app.tasks.reports.generate_tenant_monthly_report")
def generate_tenant_monthly_report(tenant_id: str, year: int, month: int):
    """
    Generate monthly report for a specific tenant.
    
    Args:
        tenant_id: Tenant ID
        year: Report year
        month: Report month
    """
    try:
        from app.models.expense import Expense
        from sqlalchemy import func

        # Calculate date range
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

        # Query expenses for the month
        expenses = Expense.query.filter(
            Expense.tenant_id == tenant_id,
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
            Expense.is_deleted == False,
        ).all()

        total_amount = sum(exp.amount for exp in expenses)
        expense_count = len(expenses)

        logger.info(
            f"Monthly report generated",
            tenant_id=tenant_id,
            year=year,
            month=month,
            total_amount=float(total_amount),
            count=expense_count,
        )

        # TODO: Store report, send email, etc.

        return {
            "tenant_id": tenant_id,
            "period": f"{year}-{month:02d}",
            "total_amount": float(total_amount),
            "expense_count": expense_count,
        }

    except Exception as e:
        logger.error(f"Error generating report for tenant {tenant_id}: {e}")
        raise
