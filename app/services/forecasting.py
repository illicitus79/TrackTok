"""Forecasting service for budget predictions."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, extract, func

from app.core.extensions import db
from app.models.account import Account
from app.models.expense import Expense
from app.models.project import Project


class ForecastingService:
    """Service for financial forecasting and predictions."""

    @staticmethod
    def calculate_burn_rate(
        tenant_id: str,
        project_id: str,
        days: int = 30
    ) -> Dict[str, float]:
        """
        Calculate burn rate for a project.
        
        Args:
            tenant_id: Tenant ID
            project_id: Project ID
            days: Number of days to calculate over (default last 30 days)
            
        Returns:
            Dict with daily_burn_rate, monthly_burn_rate
        """
        logger.info(f"Calculating burn rate for project {project_id} over {days} days")
        
        project = Project.query.filter_by(id=project_id, tenant_id=tenant_id).first()
        if not project:
            return {"daily_burn_rate": 0.0, "monthly_burn_rate": 0.0, "period_days": days}
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get total expenses in period
        total_expenses = db.session.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.tenant_id == tenant_id,
                Expense.project_id == project_id,
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date,
                Expense.deleted_at.is_(None)
            )
        ).scalar() or 0.0
        
        # Calculate rates
        daily_burn_rate = total_expenses / days if days > 0 else 0.0
        monthly_burn_rate = daily_burn_rate * 30
        
        return {
            "daily_burn_rate": float(daily_burn_rate),
            "monthly_burn_rate": float(monthly_burn_rate),
            "period_days": days,
            "total_spent_in_period": float(total_expenses),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    @staticmethod
    def predict_overspend(
        tenant_id: str,
        project_id: str
    ) -> Dict[str, any]:
        """
        Predict if project will exceed budget using linear projection.
        
        Args:
            tenant_id: Tenant ID
            project_id: Project ID
            
        Returns:
            Prediction dict with probability, projected_total, etc.
        """
        logger.info(f"Predicting overspend for project {project_id}")
        
        project = Project.query.filter_by(id=project_id, tenant_id=tenant_id).first()
        if not project:
            return {
                "will_exceed": False,
                "confidence": 0.0,
                "projected_total": 0.0,
                "projected_overage": 0.0,
                "days_until_depleted": None
            }
        
        # Get project metrics
        total_spent = project.total_spent
        starting_budget = project.starting_budget
        days_elapsed = project.days_elapsed or 0
        days_remaining = project.days_remaining or 0
        total_days = days_elapsed + days_remaining
        
        # Calculate linear projection
        if days_elapsed > 0 and total_days > 0:
            daily_burn_rate = total_spent / days_elapsed
            projected_total = daily_burn_rate * total_days
            
            will_exceed = projected_total > starting_budget
            projected_overage = max(0, projected_total - starting_budget)
            
            # Confidence based on data availability (more elapsed days = higher confidence)
            confidence = min(100, (days_elapsed / total_days) * 100)
            
            # Days until budget depleted
            remaining_budget = starting_budget - total_spent
            days_until_depleted = None
            if daily_burn_rate > 0 and remaining_budget > 0:
                days_until_depleted = int(remaining_budget / daily_burn_rate)
            elif remaining_budget <= 0:
                days_until_depleted = 0
            
            return {
                "will_exceed": will_exceed,
                "confidence": float(confidence),
                "projected_total": float(projected_total),
                "projected_overage": float(projected_overage),
                "days_until_depleted": days_until_depleted,
                "daily_burn_rate": float(daily_burn_rate),
                "total_spent": float(total_spent),
                "starting_budget": float(starting_budget),
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining
            }
        
        return {
            "will_exceed": False,
            "confidence": 0.0,
            "projected_total": float(total_spent),
            "projected_overage": 0.0,
            "days_until_depleted": None
        }

    @staticmethod
    def generate_forecast_series(
        tenant_id: str,
        project_id: str,
        months_ahead: int = 6
    ) -> Dict[str, List]:
        """
        Generate forecast data series for charts (Chart.js format).
        
        Args:
            tenant_id: Tenant ID
            project_id: Project ID
            months_ahead: Number of months to forecast
            
        Returns:
            Dict with labels and actual/projected datasets
        """
        logger.info(f"Generating forecast series for project {project_id}, {months_ahead} months ahead")
        
        project = Project.query.filter_by(id=project_id, tenant_id=tenant_id).first()
        if not project:
            return {"labels": [], "actual": [], "projected": []}
        
        # Generate monthly data for past months (actual)
        labels = []
        actual_data = []
        projected_data = []
        
        start_date = project.start_date or datetime.utcnow()
        current_date = datetime.utcnow()
        
        # Calculate months between start and now
        months_elapsed = ((current_date.year - start_date.year) * 12 + 
                         current_date.month - start_date.month)
        
        # Generate actual data for past months
        for i in range(max(0, months_elapsed) + 1):
            month_date = start_date + timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            # Get expenses for this month
            month_total = db.session.query(func.sum(Expense.amount)).filter(
                and_(
                    Expense.tenant_id == tenant_id,
                    Expense.project_id == project_id,
                    Expense.expense_date >= month_start,
                    Expense.expense_date <= month_end,
                    Expense.deleted_at.is_(None)
                )
            ).scalar() or 0.0
            
            labels.append(month_date.strftime("%b %Y"))
            actual_data.append(float(month_total))
        
        # Generate projected data based on burn rate
        burn_rate_data = ForecastingService.calculate_burn_rate(tenant_id, project_id, 30)
        monthly_burn = burn_rate_data["monthly_burn_rate"]
        
        # Project future months
        last_actual_total = sum(actual_data)
        for i in range(1, months_ahead + 1):
            future_date = current_date + timedelta(days=30 * i)
            labels.append(future_date.strftime("%b %Y"))
            actual_data.append(None)  # No actual data for future
            projected_data.append(float(last_actual_total + (monthly_burn * i)))
        
        # Fill projected for past months (same as actual)
        for i in range(len(actual_data) - months_ahead):
            if actual_data[i] is not None:
                projected_data.insert(i, actual_data[i])
        
        return {
            "labels": labels,
            "actual": actual_data,
            "projected": projected_data
        }

    @staticmethod
    def calculate_remaining_runway(
        tenant_id: str,
        account_id: str,
        monthly_burn: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Calculate how many months/days until account is depleted.
        
        Args:
            tenant_id: Tenant ID
            account_id: Account ID
            monthly_burn: Optional override for burn rate
            
        Returns:
            Dict with runway in days/months
        """
        logger.info(f"Calculating runway for account {account_id}")
        
        account = Account.query.filter_by(id=account_id, tenant_id=tenant_id).first()
        if not account:
            return {
                "current_balance": 0.0,
                "monthly_burn": 0.0,
                "runway_months": 0.0,
                "runway_days": 0,
                "depletion_date": None
            }
        
        current_balance = account.current_balance
        
        # Calculate monthly burn if not provided
        if monthly_burn is None:
            # Get last 30 days of expenses
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            month_expenses = db.session.query(func.sum(Expense.amount)).filter(
                and_(
                    Expense.tenant_id == tenant_id,
                    Expense.account_id == account_id,
                    Expense.expense_date >= thirty_days_ago,
                    Expense.deleted_at.is_(None)
                )
            ).scalar() or 0.0
            monthly_burn = float(month_expenses)
        
        # Calculate runway
        if monthly_burn > 0:
            runway_months = current_balance / monthly_burn
            runway_days = int(runway_months * 30)
            depletion_date = (datetime.utcnow() + timedelta(days=runway_days)).date()
        else:
            runway_months = float('inf')
            runway_days = None
            depletion_date = None
        
        return {
            "current_balance": float(current_balance),
            "monthly_burn": float(monthly_burn),
            "runway_months": float(runway_months) if runway_months != float('inf') else None,
            "runway_days": runway_days,
            "depletion_date": depletion_date.isoformat() if depletion_date else None
        }
