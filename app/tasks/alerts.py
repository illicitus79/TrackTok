"""Alert monitoring tasks."""
from datetime import datetime

from loguru import logger

from app.core.extensions import db
from app.models.project import Project
from app.models.tenant import Tenant
from app.services.alerts import AlertService
from app.services.forecasting import ForecastingService
from app.tasks.celery_app import celery


@celery.task(name="app.tasks.alerts.check_low_balance_accounts")
def check_low_balance_accounts():
    """
    Check all active accounts for low balance conditions.
    
    Runs hourly to monitor account balances.
    """
    logger.info("Starting low balance account check")
    
    tenants = Tenant.query.filter_by(is_active=True).all()
    total_alerts = 0
    
    for tenant in tenants:
        try:
            alerts = AlertService.check_low_balance_accounts(tenant.id)
            total_alerts += len(alerts)
            
            # Send notifications for new alerts
            for alert in alerts:
                if not alert.notification_sent_at:
                    # TODO: Get tenant admins/owners emails
                    # AlertService.send_alert_notification(alert.id, recipients)
                    pass
                    
        except Exception as e:
            logger.error(f"Error checking low balance for tenant {tenant.id}: {e}")
            continue
    
    logger.info(f"Low balance check completed. Created/updated {total_alerts} alerts")
    
    return {"alerts_created": total_alerts}


@celery.task(name="app.tasks.alerts.update_forecast_and_generate_alerts")
def update_forecast_and_generate_alerts():
    """
    Update forecasts for all active projects and generate overspend alerts.
    
    Runs daily to analyze project spending trends.
    """
    logger.info("Starting forecast and alert generation")
    
    tenants = Tenant.query.filter_by(is_active=True).all()
    total_forecasts = 0
    total_alerts = 0
    
    for tenant in tenants:
        try:
            # Get all active projects
            projects = Project.query.filter_by(
                tenant_id=tenant.id,
                status='active',
                is_deleted=False
            ).all()
            
            for project in projects:
                # Calculate forecast
                forecast = ForecastingService.predict_overspend(
                    tenant.id,
                    project.id
                )
                total_forecasts += 1
                
                logger.debug(
                    f"Forecast for project {project.id}",
                    will_exceed=forecast['will_exceed'],
                    confidence=forecast['confidence']
                )
                
                # Check for overspend alerts (confidence >= 90%)
                if forecast['will_exceed'] and forecast['confidence'] >= 90:
                    alerts = AlertService.check_forecast_overspend(tenant.id, project.id)
                    total_alerts += len(alerts)
                    
                    # Send notifications
                    for alert in alerts:
                        if not alert.notification_sent_at:
                            # TODO: Get project stakeholders emails
                            # AlertService.send_alert_notification(alert.id, recipients)
                            pass
                            
        except Exception as e:
            logger.error(f"Error forecasting for tenant {tenant.id}: {e}")
            continue
    
    logger.info(
        f"Forecast check completed. Generated {total_forecasts} forecasts, {total_alerts} alerts"
    )
    
    return {
        "forecasts_generated": total_forecasts,
        "alerts_created": total_alerts
    }


@celery.task(name="app.tasks.alerts.send_daily_summary")
def send_daily_summary():
    """
    Send daily summary of alerts and budget status to tenant admins.
    
    Runs daily at configured time.
    """
    logger.info("Starting daily summary generation")
    
    tenants = Tenant.query.filter_by(is_active=True).all()
    summaries_sent = 0
    
    for tenant in tenants:
        try:
            # Get unread alerts
            alerts = AlertService.get_unread_alerts(tenant.id, limit=50)
            
            if alerts:
                # TODO: Generate summary email with alert details
                # TODO: Get tenant admin emails and send
                logger.info(f"Would send daily summary to tenant {tenant.id} with {len(alerts)} alerts")
                summaries_sent += 1
                
        except Exception as e:
            logger.error(f"Error generating summary for tenant {tenant.id}: {e}")
            continue
    
    logger.info(f"Daily summary completed. Sent {summaries_sent} summaries")
    
    return {"summaries_sent": summaries_sent}
