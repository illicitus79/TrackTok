"""Balance management service for ACID transactions."""
from decimal import Decimal
from typing import Optional

from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.core.extensions import db
from app.models.account import Account
from app.models.audit import AuditAction, AuditLog
from app.models.expense import Expense


class BalanceService:
    """
    Service for managing account balances with ACID transactions.
    
    Ensures that every expense operation properly updates account balances
    and maintains data integrity.
    """

    @staticmethod
    def create_expense_with_balance_update(
        tenant_id: str,
        account_id: str,
        amount: Decimal,
        expense_data: dict,
        user_id: str
    ) -> Expense:
        """
        Create expense and debit account balance in a single transaction.
        
        Args:
            tenant_id: Tenant ID
            account_id: Account ID to debit
            amount: Expense amount
            expense_data: Dict with expense fields
            user_id: User creating the expense
            
        Returns:
            Created Expense object
            
        Raises:
            ValueError: If account not found or insufficient balance
            IntegrityError: If transaction fails
        """
        try:
            # Begin transaction (handled by SQLAlchemy session)
            
            # Get account with row lock (SELECT FOR UPDATE)
            account = db.session.query(Account).filter_by(
                id=account_id,
                tenant_id=tenant_id,
                is_active=True
            ).with_for_update().first()
            
            if not account:
                raise ValueError(f"Account {account_id} not found or inactive")
            
            # Check if account would go negative (optional business rule)
            # Uncomment if you want to prevent negative balances
            # if account.current_balance - amount < 0:
            #     raise ValueError(
            #         f"Insufficient balance. Current: {account.current_balance}, "
            #         f"Required: {amount}"
            #     )
            
            # Create expense
            expense = Expense(
                tenant_id=tenant_id,
                account_id=account_id,
                created_by=user_id,
                **expense_data
            )
            
            # Debit account balance
            old_balance = account.current_balance
            account.debit(amount)
            new_balance = account.current_balance
            
            db.session.add(expense)
            db.session.flush()  # Get expense ID
            
            # Log balance change
            AuditLog.log_action(
                action=AuditAction.CREATE,
                entity_type="expense",
                entity_id=expense.id,
                details={
                    "amount": float(amount),
                    "account_id": account_id,
                    "old_balance": float(old_balance),
                    "new_balance": float(new_balance)
                }
            )
            
            # Commit transaction
            db.session.commit()
            
            logger.info(
                f"Expense created with balance update",
                expense_id=expense.id,
                account_id=account_id,
                amount=float(amount),
                old_balance=float(old_balance),
                new_balance=float(new_balance)
            )
            
            return expense
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating expense with balance update: {e}")
            raise

    @staticmethod
    def update_expense_with_balance_adjustment(
        expense_id: str,
        tenant_id: str,
        old_amount: Decimal,
        new_amount: Decimal,
        old_account_id: Optional[str] = None,
        new_account_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Expense:
        """
        Update expense and adjust account balances accordingly.
        
        Handles both amount changes and account transfers.
        
        Args:
            expense_id: Expense ID
            tenant_id: Tenant ID
            old_amount: Previous expense amount
            new_amount: New expense amount
            old_account_id: Previous account (if changing accounts)
            new_account_id: New account (if changing accounts)
            user_id: User making the change
            
        Returns:
            Updated Expense object
            
        Raises:
            ValueError: If expense or accounts not found
        """
        try:
            expense = Expense.query.filter_by(
                id=expense_id,
                tenant_id=tenant_id
            ).first()
            
            if not expense:
                raise ValueError(f"Expense {expense_id} not found")
            
            # Determine if account changed
            account_changed = (old_account_id and new_account_id and 
                             old_account_id != new_account_id)
            
            if account_changed:
                # Transfer between accounts
                old_account = db.session.query(Account).filter_by(
                    id=old_account_id,
                    tenant_id=tenant_id
                ).with_for_update().first()
                
                new_account = db.session.query(Account).filter_by(
                    id=new_account_id,
                    tenant_id=tenant_id
                ).with_for_update().first()
                
                if not old_account or not new_account:
                    raise ValueError("One or both accounts not found")
                
                # Reverse old expense (credit old account)
                old_account.credit(old_amount)
                
                # Apply new expense (debit new account)
                new_account.debit(new_amount)
                
                expense.account_id = new_account_id
                expense.amount = new_amount
                
                logger.info(
                    f"Expense transferred between accounts",
                    expense_id=expense_id,
                    old_account=old_account_id,
                    new_account=new_account_id,
                    old_amount=float(old_amount),
                    new_amount=float(new_amount)
                )
                
            else:
                # Same account, just adjust amount
                account = db.session.query(Account).filter_by(
                    id=expense.account_id,
                    tenant_id=tenant_id
                ).with_for_update().first()
                
                if not account:
                    raise ValueError(f"Account {expense.account_id} not found")
                
                # Calculate delta
                delta = new_amount - old_amount
                
                if delta > 0:
                    # Increased expense - debit more
                    account.debit(delta)
                elif delta < 0:
                    # Decreased expense - credit back
                    account.credit(abs(delta))
                
                expense.amount = new_amount
                
                logger.info(
                    f"Expense amount adjusted",
                    expense_id=expense_id,
                    account_id=expense.account_id,
                    old_amount=float(old_amount),
                    new_amount=float(new_amount),
                    delta=float(delta)
                )
            
            # Log audit
            AuditLog.log_action(
                action=AuditAction.UPDATE,
                entity_type="expense",
                entity_id=expense.id,
                details={
                    "old_amount": float(old_amount),
                    "new_amount": float(new_amount),
                    "account_changed": account_changed
                }
            )
            
            db.session.commit()
            
            return expense
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating expense with balance adjustment: {e}")
            raise

    @staticmethod
    def delete_expense_with_balance_reversal(
        expense_id: str,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Soft delete expense and reverse account balance impact.
        
        Args:
            expense_id: Expense ID
            tenant_id: Tenant ID
            user_id: User performing deletion
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If expense not found
        """
        try:
            expense = Expense.query.filter_by(
                id=expense_id,
                tenant_id=tenant_id,
                deleted_at=None
            ).first()
            
            if not expense:
                raise ValueError(f"Expense {expense_id} not found or already deleted")
            
            # Get account with lock
            account = db.session.query(Account).filter_by(
                id=expense.account_id,
                tenant_id=tenant_id
            ).with_for_update().first()
            
            if not account:
                raise ValueError(f"Account {expense.account_id} not found")
            
            # Reverse the expense (credit account)
            old_balance = account.current_balance
            account.credit(expense.amount)
            new_balance = account.current_balance
            
            # Soft delete expense
            expense.soft_delete()
            
            # Log audit
            AuditLog.log_action(
                action=AuditAction.DELETE,
                entity_type="expense",
                entity_id=expense.id,
                details={
                    "amount": float(expense.amount),
                    "account_id": expense.account_id,
                    "old_balance": float(old_balance),
                    "new_balance": float(new_balance),
                    "balance_reversed": True
                }
            )
            
            db.session.commit()
            
            logger.info(
                f"Expense soft deleted with balance reversal",
                expense_id=expense_id,
                account_id=expense.account_id,
                amount=float(expense.amount),
                old_balance=float(old_balance),
                new_balance=float(new_balance)
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting expense with balance reversal: {e}")
            raise
