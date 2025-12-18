"""Alert service for budget and balance monitoring."""
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import and_, func

from app.core.extensions import db
from app.models.account import Account
from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.budget import Budget
from app.models.project import Project
from app.models.user import User, UserRole


class AlertService:
    """Service for generating and managing alerts."""

    @staticmethod
    def _action(label: str, url: str, variant: str = "primary") -> Dict[str, str]:
        """Helper to build action button metadata."""
        return {"label": label, "url": url, "variant": variant}

    @staticmethod
    def _upsert_alert(
        tenant_id: str,
        alert_type: AlertType,
        entity_type: str,
        entity_id: str,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[dict] = None,
    ) -> Alert:
        """Create or update an alert in place and reset read/notification flags when refreshed."""
        alert = (
            Alert.query.filter_by(
                tenant_id=tenant_id,
                alert_type=alert_type,
                entity_type=entity_type,
                entity_id=entity_id,
                is_deleted=False,
            )
            .order_by(Alert.created_at.desc())
            .first()
        )

        if alert:
            alert.title = title
            alert.message = message
            alert.severity = severity
            alert.alert_metadata = metadata or {}
            alert.is_read = False
            alert.is_dismissed = False
            alert.notification_sent = False
            alert.notification_sent_at = None
        else:
            alert = Alert(
                tenant_id=tenant_id,
                alert_type=alert_type,
                entity_type=entity_type,
                entity_id=entity_id,
                title=title,
                message=message,
                severity=severity,
                alert_metadata=metadata or {},
            )
            db.session.add(alert)

        return alert

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
                Account.is_deleted == False,
                Account.low_balance_threshold.isnot(None),
                Account.low_balance_threshold > 0,
                Account.current_balance <= Account.low_balance_threshold,
            )
        ).all()
        
        created_alerts = []
        
        for account in low_balance_accounts:
            severity = AlertSeverity.ERROR if account.current_balance < 0 else AlertSeverity.WARNING
            metadata = {
                "current_balance": float(account.current_balance),
                "threshold": float(account.low_balance_threshold),
                "currency": account.currency,
                "account_name": account.name,
                "account_id": account.id,
                "suggestions": [
                    "Add funds or transfer money to restore a safe buffer.",
                    "Audit recent large expenses from this account.",
                    "Adjust the low balance threshold if this is expected behavior.",
                ],
                "actions": [
                    AlertService._action("Add funds", f"/accounts/{account.id}/adjust", "primary"),
                    AlertService._action("View account activity", f"/accounts/{account.id}/transactions", "secondary"),
                ],
            }

            alert = AlertService._upsert_alert(
                tenant_id=tenant_id,
                alert_type=AlertType.LOW_BALANCE,
                entity_type="account",
                entity_id=account.id,
                title=f"Low Balance: {account.name}",
                message=(
                    f"Balance is {account.current_balance:.2f} {account.currency}, below the threshold of "
                    f"{account.low_balance_threshold:.2f} {account.currency}."
                ),
                severity=severity,
                metadata=metadata,
            )
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
                        overage = projected_total - project.starting_budget
                        message = (
                            f"'{project.name}' is on track to exceed its budget by "
                            f"{overage:.2f}. Current utilization: {utilization:.1f}%."
                        )
                        severity = AlertSeverity.WARNING if confidence < 95 else AlertSeverity.ERROR
                        metadata = {
                            'current_spent': float(total_spent),
                            'starting_budget': float(project.starting_budget),
                            'projected_total': float(projected_total),
                            'projected_overage': float(overage),
                            'confidence': float(confidence),
                            'utilization': float(utilization),
                            "project_name": project.name,
                            "currency": project.currency,
                            "suggestions": [
                                "Delay or reprioritize non-critical spend to stay within budget.",
                                "Increase the project budget or reforecast with finance.",
                                "Review vendor contracts for quick savings opportunities.",
                            ],
                            "actions": [
                                AlertService._action("Review project", f"/projects/{project.id}/edit", "primary"),
                                AlertService._action("Open expenses", f"/expenses?project_id={project.id}", "secondary"),
                            ],
                        }

                        alert = AlertService._upsert_alert(
                            tenant_id=tenant_id,
                            alert_type=AlertType.FORECAST_OVERSPEND,
                            entity_type='project',
                            entity_id=project.id,
                            title=f"Forecasted Overspend: {project.name}",
                            message=message,
                            severity=severity,
                            metadata=metadata,
                        )
                        created_alerts.append(alert)
        
        if created_alerts:
            db.session.commit()
            logger.info(f"Created/updated {len(created_alerts)} forecast overspend alerts for tenant {tenant_id}")
        
        return created_alerts

    @staticmethod
    def check_budget_thresholds(tenant_id: str) -> List[Alert]:
        """Create alerts when budgets near or exceed thresholds."""
        budgets = Budget.query.filter_by(
            tenant_id=tenant_id,
            is_active=True,
            is_deleted=False,
            alert_enabled=True,
        ).all()

        created_alerts: List[Alert] = []

        today = date.today()
        for budget in budgets:
            utilization = budget.get_utilization_percentage()
            spent = float(budget.get_spent_amount())
            remaining = float(budget.amount) - spent
            threshold_pct = budget.alert_threshold or 80
            alert_type = None
            severity = AlertSeverity.WARNING

            if utilization >= 100:
                alert_type = AlertType.BUDGET_EXCEEDED
                severity = AlertSeverity.ERROR
            elif utilization >= threshold_pct:
                alert_type = AlertType.BUDGET_WARNING
                severity = AlertSeverity.WARNING

            if not alert_type:
                continue

            days_left = (budget.end_date - today).days if budget.end_date else None
            title = (
                f"Budget exceeded: {budget.name}"
                if alert_type == AlertType.BUDGET_EXCEEDED
                else f"Budget at {utilization:.0f}%: {budget.name}"
            )
            message = (
                f"Spend is {utilization:.1f}% of {float(budget.amount):,.2f} {budget.currency}. "
                f"Remaining: {remaining:,.2f} {budget.currency}."
            )
            metadata = {
                "utilization": float(utilization),
                "spent": spent,
                "amount": float(budget.amount),
                "currency": budget.currency,
                "remaining": remaining,
                "threshold": threshold_pct,
                "budget_name": budget.name,
                "period_end": budget.end_date.isoformat() if budget.end_date else None,
                "days_remaining": days_left,
                "suggestions": [
                    "Pause or defer discretionary expenses tied to this budget.",
                    "Increase the budget or shorten the period to tighten controls.",
                    "Review top vendors/categories contributing to the spike.",
                ],
                "actions": [
                    AlertService._action("View expenses", "/expenses", "primary"),
                    AlertService._action("Adjust budget plan", "/settings", "secondary"),
                ],
            }

            alert = AlertService._upsert_alert(
                tenant_id=tenant_id,
                alert_type=alert_type,
                entity_type="budget",
                entity_id=budget.id,
                title=title,
                message=message,
                severity=severity,
                metadata=metadata,
            )
            created_alerts.append(alert)

        if created_alerts:
            db.session.commit()
            logger.info(f"Created/updated {len(created_alerts)} budget alerts for tenant {tenant_id}")
        return created_alerts

    @staticmethod
    def check_project_deadlines(tenant_id: str) -> List[Alert]:
        """Alert when projects are nearing or past their deadline."""
        projects = Project.query.filter_by(
            tenant_id=tenant_id,
            is_deleted=False,
            status="active",
        ).filter(Project.end_date.isnot(None)).all()

        created_alerts: List[Alert] = []
        today = date.today()

        for project in projects:
            days_remaining = (project.end_date - today).days
            if days_remaining > 14:
                continue

            if days_remaining < 0:
                alert_type = AlertType.DEADLINE_OVERDUE
                severity = AlertSeverity.ERROR
                descriptor = "is overdue"
            elif days_remaining <= 7:
                alert_type = AlertType.PROJECT_DEADLINE
                severity = AlertSeverity.WARNING
                descriptor = f"ends in {days_remaining} days"
            else:
                alert_type = AlertType.PROJECT_DEADLINE
                severity = AlertSeverity.INFO
                descriptor = f"ends in {days_remaining} days"

            message = f"Project '{project.name}' {descriptor}. Ensure final expenses and reports are in."
            metadata = {
                "end_date": project.end_date.isoformat(),
                "days_remaining": days_remaining,
                "project_name": project.name,
                "suggestions": [
                    "Close out outstanding expenses tied to this project.",
                    "Align stakeholders on timeline or extend the deadline.",
                    "Review remaining budget and forecast final spend.",
                ],
                "actions": [
                    AlertService._action("Edit project", f"/projects/{project.id}/edit", "primary"),
                    AlertService._action("Log expense", f"/expenses/new?project_id={project.id}", "secondary"),
                ],
            }

            alert = AlertService._upsert_alert(
                tenant_id=tenant_id,
                alert_type=alert_type,
                entity_type="project",
                entity_id=project.id,
                title=f"Project deadline: {project.name}",
                message=message,
                severity=severity,
                metadata=metadata,
            )
            created_alerts.append(alert)

        if created_alerts:
            db.session.commit()
            logger.info(f"Created/updated {len(created_alerts)} project deadline alerts for tenant {tenant_id}")
        return created_alerts

    @staticmethod
    def send_alert_notification(alert_id: str, recipients: Optional[List[str]] = None) -> bool:
        """
        Send alert notification via email.
        
        Args:
            alert_id: Alert ID
            recipients: List of email addresses (defaults to tenant owners/admins)
            
        Returns:
            Success status
        """
        from flask import current_app, render_template, url_for
        from flask_mail import Message
        from urllib.parse import urljoin
        
        from app.core.extensions import mail
        from app.models.user_preferences import UserPreferences
        
        alert = Alert.query.get(alert_id)
        if not alert:
            logger.error(f"Alert {alert_id} not found")
            return False
        
        try:
            if recipients is None:
                recipients = [
                    u.email
                    for u in User.query.filter(
                        User.tenant_id == alert.tenant_id,
                        User.is_active == True,
                        User.is_deleted == False,
                        User.role.in_([UserRole.OWNER.value, UserRole.ADMIN.value]),
                    ).all()
                ]

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
            actions = (alert.alert_metadata or {}).get("actions") or []
            primary_action = actions[0]["url"] if actions else dashboard_url
            if primary_action and not str(primary_action).startswith("http"):
                primary_action = urljoin(dashboard_url, str(primary_action).lstrip("/"))
            
            # Render email templates
            html_body = render_template(
                'emails/alert_notification.html',
                alert=alert,
                dashboard_url=dashboard_url,
                preferences_url=preferences_url,
                primary_action=primary_action,
            )
            
            text_body = render_template(
                'emails/alert_notification.txt',
                alert=alert,
                dashboard_url=dashboard_url,
                preferences_url=preferences_url,
                primary_action=primary_action,
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
    def dispatch_notifications(alerts: List[Alert], tenant_id: str) -> int:
        """Send notifications for alerts that have not been sent yet."""
        sent = 0
        for alert in alerts:
            if alert.notification_sent:
                continue
            if AlertService.send_alert_notification(alert.id):
                sent += 1
        if sent:
            logger.info(f"Sent {sent} alert notifications for tenant {tenant_id}")
        return sent

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
            is_read=False,
            is_dismissed=False,
        ).order_by(Alert.created_at.desc()).limit(limit).all()
