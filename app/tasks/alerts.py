"""Budget alert tasks."""
from datetime import datetime

from loguru import logger

from app.core.extensions import db
from app.models.budget import Budget, BudgetAlert
from app.models.tenant import Tenant
from app.tasks.celery_app import celery


@celery.task(name="app.tasks.alerts.check_budget_alerts")
def check_budget_alerts():
    """
    Check all active budgets and create alerts for those exceeding thresholds.
    
    Runs daily to monitor budget utilization.
    """
    logger.info("Starting budget alert check")

    tenants = Tenant.query.filter_by(is_active=True).all()

    total_alerts = 0

    for tenant in tenants:
        budgets = Budget.query.filter_by(
            tenant_id=tenant.id, is_active=True, alert_enabled=True, is_deleted=False
        ).all()

        for budget in budgets:
            try:
                if budget.should_alert():
                    # Check if alert already sent today
                    existing_alert = (
                        BudgetAlert.query.filter_by(
                            budget_id=budget.id, is_sent=True, sent_at=datetime.utcnow().date()
                        )
                        .first()
                    )

                    if not existing_alert:
                        # Create alert
                        alert = BudgetAlert(
                            tenant_id=tenant.id,
                            budget_id=budget.id,
                            threshold_percentage=budget.alert_threshold,
                            amount_spent=budget.get_spent_amount(),
                            budget_amount=budget.amount,
                            is_sent=False,
                        )
                        db.session.add(alert)
                        db.session.commit()

                        # Send notification (async)
                        send_budget_alert_notification.delay(alert.id)

                        total_alerts += 1
                        logger.info(
                            f"Budget alert created",
                            budget_id=budget.id,
                            tenant_id=tenant.id,
                            utilization=budget.get_utilization_percentage(),
                        )

            except Exception as e:
                logger.error(f"Error checking budget {budget.id}: {e}")
                continue

    logger.info(f"Budget alert check completed. Created {total_alerts} alerts")

    return {"alerts_created": total_alerts}


@celery.task(name="app.tasks.alerts.send_budget_alert_notification")
def send_budget_alert_notification(alert_id: str):
    """
    Send email notification for budget alert.
    
    Args:
        alert_id: ID of the budget alert
    """
    try:
        alert = BudgetAlert.query.get(alert_id)
        if not alert or alert.is_sent:
            return

        budget = alert.budget

        # TODO: Implement email sending
        # For now, just mark as sent
        alert.is_sent = True
        alert.sent_at = datetime.utcnow().date()
        alert.notification_method = "email"
        db.session.commit()

        logger.info(f"Budget alert notification sent", alert_id=alert_id)

        return {"alert_id": alert_id, "status": "sent"}

    except Exception as e:
        logger.error(f"Error sending budget alert {alert_id}: {e}")
        raise
