"""Database seeding script with demo data."""
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from random import choice, randint, uniform

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.core.extensions import db
from app.models import Budget, Category, Expense, Tenant, User, UserRole
from loguru import logger


def seed_database():
    """Seed database with demo data."""
    app = create_app()

    with app.app_context():
        logger.info("Seeding database with demo data...")

        # Create demo tenant
        tenant = Tenant(
            name="Acme Corporation", subdomain="acme", plan="pro", max_users=50, max_expenses=10000
        )
        db.session.add(tenant)
        db.session.flush()

        # Create users
        owner = User(
            tenant_id=tenant.id,
            email="owner@acme.com",
            first_name="John",
            last_name="Owner",
            role=UserRole.OWNER.value,
            is_verified=True,
        )
        owner.set_password("Password123")
        db.session.add(owner)

        admin = User(
            tenant_id=tenant.id,
            email="admin@acme.com",
            first_name="Jane",
            last_name="Admin",
            role=UserRole.ADMIN.value,
            is_verified=True,
        )
        admin.set_password("Password123")
        db.session.add(admin)

        member = User(
            tenant_id=tenant.id,
            email="member@acme.com",
            first_name="Bob",
            last_name="Member",
            role=UserRole.MEMBER.value,
            is_verified=True,
        )
        member.set_password("Password123")
        db.session.add(member)

        db.session.flush()

        # Create categories
        categories_data = [
            {"name": "Food & Dining", "color": "#FF6384", "icon": "🍔"},
            {"name": "Transportation", "color": "#36A2EB", "icon": "🚗"},
            {"name": "Utilities", "color": "#FFCE56", "icon": "💡"},
            {"name": "Entertainment", "color": "#4BC0C0", "icon": "🎬"},
            {"name": "Shopping", "color": "#9966FF", "icon": "🛍️"},
            {"name": "Health", "color": "#FF9F40", "icon": "🏥"},
        ]

        categories = []
        for cat_data in categories_data:
            category = Category(tenant_id=tenant.id, **cat_data)
            db.session.add(category)
            categories.append(category)

        db.session.flush()

        # Create expenses
        users = [owner, admin, member]
        payment_methods = ["cash", "credit_card", "debit_card", "bank_transfer"]

        for i in range(50):
            expense = Expense(
                tenant_id=tenant.id,
                created_by=choice(users).id,
                category_id=choice(categories).id,
                amount=Decimal(str(round(uniform(10, 500), 2))),
                currency="USD",
                title=f"Expense #{i+1}",
                description=f"Demo expense for testing",
                expense_date=date.today() - timedelta(days=randint(0, 90)),
                payment_method=choice(payment_methods),
                status="approved",
            )
            db.session.add(expense)

        # Create budgets
        for category in categories[:3]:
            budget = Budget(
                tenant_id=tenant.id,
                name=f"{category.name} Budget",
                amount=Decimal("2000.00"),
                currency="USD",
                period="monthly",
                start_date=date.today().replace(day=1),
                end_date=(date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
                - timedelta(days=1),
                category_id=category.id,
                alert_threshold=80,
                alert_enabled=True,
            )
            db.session.add(budget)

        db.session.commit()

        logger.info("✓ Database seeded successfully")
        print("\n✅ Database seeded with demo data!")
        print(f"   Tenant: acme (subdomain: acme.localhost)")
        print(f"   Users:")
        print(f"     - owner@acme.com / Password123")
        print(f"     - admin@acme.com / Password123")
        print(f"     - member@acme.com / Password123")
        print(f"   Categories: {len(categories)}")
        print(f"   Expenses: 50")
        print(f"   Budgets: 3")


if __name__ == "__main__":
    seed_database()
