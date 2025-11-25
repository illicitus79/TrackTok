"""Alert service for budget and balance monitoring."""
from datetime import datetime
from typing import List, Optional

from loguru import logger
from sqlalchemy import and_, func

from app.core.extensions import db
from app.models.account import Account
from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.project import Project
from app.models.tenant import Tenant


class AlertService:
    """Service for generating and managing alerts."""

    @staticmethod
    def check_low_balance_accounts(tenant_id: str) -> List[Alert]:
        """
        Check all accounts for low balance conditions.
        
        Creates alerts when current_balance <= low_balance_threshold.
        
        Args:
            tenant_id: Tenant ID to check accounts for
            
        Returns:
            List of created Alert objects
        """
        logger.info(f"Checking low balance accounts for tenant {tenant_id}")
        
        # Get all active accounts with low balance
        low_balance_accounts = Account.query.filter(
            and_(
                Account.tenant_id == tenant_id,
                Account.is_active == True,
                Account.current_balance <= Account.low_balance_threshold,
                Account.low_balance_threshold > 0
            )
        ).all()
        
        created_alerts = []
        
        for account in low_balance_accounts:
            # Check if alert already exists and is unread
            existing_alert = Alert.query.filter_by(
                tenant_id=tenant_id,
                alert_type=AlertType.LOW_BALANCE,
                entity_type='account',
                entity_id=account.id,
                is_read=False
            ).first()
            
            if existing_alert:
                # Update existing alert
                existing_alert.message = (
                    f"Account '{account.name}' balance ({account.current_balance:.2f} {account.currency}) "
                    f"is below threshold ({account.low_balance_threshold:.2f} {account.currency})"
                )
                existing_alert.severity = AlertSeverity.ERROR if account.current_balance < 0 else AlertSeverity.WARNING
                existing_alert.metadata = {
                    'current_balance': float(account.current_balance),
                    'threshold': float(account.low_balance_threshold),
                    'currency': account.currency,
                    'account_name': account.name
                }
                db.session.commit()
                created_alerts.append(existing_alert)
            else:
                # Create new alert
                alert = Alert(
                    tenant_id=tenant_id,
                    alert_type=AlertType.LOW_BALANCE,
                    entity_type='account',
                    entity_id=account.id,
                    message=(
                        f"Account '{account.name}' balance ({account.current_balance:.2f} {account.currency}) "
                        f"is below threshold ({account.low_balance_threshold:.2f} {account.currency})"
                    ),
                    severity=AlertSeverity.ERROR if account.current_balance < 0 else AlertSeverity.WARNING,
                    metadata={
                        'current_balance': float(account.current_balance),
                        'threshold': float(account.low_balance_threshold),
                        'currency': account.currency,
                        'account_name': account.name
                    }
                )
                db.session.add(alert)
                created_alerts.append(alert)
        
        if created_alerts:
            db.session.commit()
            logger.info(f"Created/updated {len(created_alerts)} low balance alerts for tenant {tenant_id}")
        
        return created_alerts

    @staticmethod
    def check_forecast_overspend(tenant_id: str, project_id: Optional[str] = None) -> List[Alert]:
        """
        Check for budget overspend forecast conditions.
        
        Uses linear projection to predict if project will exceed budget.
        
        Args:
            tenant_id: Tenant ID
            project_id: Optional specific project to check
            
        Returns:
            List of created Alert objects
        """
        logger.info(f"Checking forecast overspend for tenant {tenant_id}, project {project_id}")
        
        # Get projects to check
        query = Project.query.filter_by(tenant_id=tenant_id, is_deleted=False, status='active')
        if project_id:
            query = query.filter_by(id=project_id)
        
        projects = query.all()
        created_alerts = []
        
        for project in projects:
            # Calculate if forecast exceeds budget
            total_spent = project.total_spent
            remaining_budget = project.remaining_budget
            utilization = project.budget_utilization
            
            # Simple linear projection: if current utilization > 90% and days_remaining > 0
            if utilization >= 90.0 and project.days_remaining and project.days_remaining > 0:
                # Calculate burn rate
                if project.days_elapsed and project.days_elapsed > 0:
                    daily_burn_rate = total_spent / project.days_elapsed
                    projected_total = daily_burn_rate * (project.days_elapsed + project.days_remaining)
                    
                    # Check if projected total exceeds budget or estimate
                    will_exceed = projected_total > project.starting_budget
                    confidence = min(100, utilization)  # Simple confidence based on utilization
                    
                    if will_exceed and confidence >= 90:
                        # Check if alert already exists
                        existing_alert = Alert.query.filter_by(
                            tenant_id=tenant_id,
                            alert_type=AlertType.FORECAST_OVERSPEND,
                            entity_type='project',
                            entity_id=project.id,
                            is_read=False
                        ).first()
                        
                        overage = projected_total - project.starting_budget
                        message = (
                            f"Project '{project.name}' is projected to exceed budget by "
                            f"{overage:.2f}. Current utilization: {utilization:.1f}%"
                        )
                        
                        if existing_alert:
                            existing_alert.message = message
                            existing_alert.metadata = {
                                'current_spent': float(total_spent),
                                'starting_budget': float(project.starting_budget),
                                'projected_total': float(projected_total),
                                'projected_overage': float(overage),
                                'confidence': float(confidence),
                                'utilization': float(utilization)
                            }
                            db.session.commit()
                            created_alerts.append(existing_alert)
                        else:
                            alert = Alert(
                                tenant_id=tenant_id,
                                alert_type=AlertType.FORECAST_OVERSPEND,
                                entity_type='project',
                                entity_id=project.id,
                                message=message,
                                severity=AlertSeverity.WARNING if confidence < 95 else AlertSeverity.ERROR,
                                metadata={
                                    'current_spent': float(total_spent),
                                    'starting_budget': float(project.starting_budget),
                                    'projected_total': float(projected_total),
                                    'projected_overage': float(overage),
                                    'confidence': float(confidence),
                                    'utilization': float(utilization)
                                }
                            )
                            db.session.add(alert)
                            created_alerts.append(alert)
        
        if created_alerts:
            db.session.commit()
            logger.info(f"Created/updated {len(created_alerts)} forecast overspend alerts for tenant {tenant_id}")
        
        return created_alerts

    @staticmethod
    def send_alert_notification(alert_id: str, recipients: List[str]) -> bool:
        """
        Send alert notification via email.
        
        Args:
            alert_id: Alert ID
            recipients: List of email addresses
            
        Returns:
            Success status
        """
        from flask import current_app, render_template, url_for
        from flask_mail import Message
        
        from app.core.extensions import mail
        from app.models.user_preferences import UserPreferences
        
        alert = Alert.query.get(alert_id)
        if not alert:
            logger.error(f"Alert {alert_id} not found")
            return False
        
        try:
            # Filter recipients based on preferences
            filtered_recipients = []
            for recipient_email in recipients:
                from app.models.user import User
                user = User.query.filter_by(email=recipient_email, tenant_id=alert.tenant_id).first()
                if user:
                    prefs = UserPreferences.get_or_create_for_user(user.id)
                    if prefs.should_send_email_for_alert(alert.alert_type):
                        filtered_recipients.append(recipient_email)
            
            if not filtered_recipients:
                logger.info(f"No recipients for alert {alert_id} after filtering preferences")
                alert.mark_notification_sent()
                db.session.commit()
                return True
            
            # Build dashboard URL
            dashboard_url = url_for('web.dashboard', _external=True, _scheme='https')
            preferences_url = url_for('api_v1.user_preferences', _external=True, _scheme='https')
            
            # Render email templates
            html_body = render_template(
                'emails/alert_notification.html',
                alert=alert,
                dashboard_url=dashboard_url,
                preferences_url=preferences_url
            )
            
            text_body = render_template(
                'emails/alert_notification.txt',
                alert=alert,
                dashboard_url=dashboard_url,
                preferences_url=preferences_url
            )
            
            # Send email
            msg = Message(
                subject=f"TrackTok Alert: {alert.title}",
                recipients=filtered_recipients,
                html=html_body,
                body=text_body
            )
            
            mail.send(msg)
            
            # Mark as sent
            alert.mark_notification_sent()
            db.session.commit()
            
            logger.info(f"Alert {alert_id} notification sent to {len(filtered_recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert notification {alert_id}: {e}")
            return False

    @staticmethod
    def get_unread_alerts(tenant_id: str, limit: int = 10) -> List[Alert]:
        """
        Get unread alerts for tenant.
        
        Args:
            tenant_id: Tenant ID
            limit: Maximum number of alerts to return
            
        Returns:
            List of Alert objects
        """
        return Alert.query.filter_by(
            tenant_id=tenant_id,
            is_read=False
        ).order_by(Alert.created_at.desc()).limit(limit).all()
