"""Celery application configuration."""
from celery import Celery
from celery.schedules import crontab

from app import create_app
from app.core.config import get_config

# Create Flask app for context
flask_app = create_app()
config = get_config()

# Initialize Celery
celery = Celery(
    "tracktok",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
)

# Configure Celery from Flask config
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

# Periodic task schedule
celery.conf.beat_schedule = {
    "check-low-balance-hourly": {
        "task": "app.tasks.alerts.check_low_balance_accounts",
        "schedule": crontab(minute=0),  # Every hour
    },
    "check-forecast-daily": {
        "task": "app.tasks.alerts.update_forecast_and_generate_alerts",
        "schedule": crontab(hour=8, minute=0),  # 8 AM daily
    },
    "send-daily-summary": {
        "task": "app.tasks.alerts.send_daily_summary",
        "schedule": crontab(hour=18, minute=0),  # 6 PM daily
    },
    "generate-monthly-reports": {
        "task": "app.tasks.reports.generate_monthly_reports",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),  # 1st of month
    },
}


class ContextTask(celery.Task):
    """Base task class with Flask app context."""

    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask
