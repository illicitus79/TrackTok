"""Database seeding script with comprehensive demo data."""
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from random import choice, randint, uniform

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.core.extensions import db
from app.models import (
    Account,
    Budget,
    BudgetPeriod,
    Category,
    Expense,
    ExpenseStatus,
    PaymentMethod,
    Project,
    Tenant,
    User,
    UserPreferences,
)
from loguru import logger


def seed_database():
    """Seed database with comprehensive demo data for charts and reports."""
    app = create_app()

    with app.app_context():
        logger.info("Seeding database with demo data...")

        # Check if data already exists
        existing_tenant = Tenant.query.filter_by(subdomain="acme").first()
        if existing_tenant:
            logger.warning("Demo tenant 'acme' already exists. Skipping seed.")
            print("\n⚠️  Demo tenant 'acme' already exists. Use 'flask tenants:seed' for new demo data.")
            return

        # Create demo tenant
        tenant = Tenant(
            name="Acme Corporation",
            subdomain="acme",
            plan="pro",
            settings={
                "currency": "USD",
                "timezone": "America/New_York",
                "date_format": "MM/DD/YYYY",
            },
            is_active=True,
        )
        db.session.add(tenant)
        db.session.flush()

        # Create users with different roles
        owner = User(
            tenant_id=tenant.id,
            email="owner@acme.com",
            first_name="John",
            last_name="Owner",
            role="Owner",
            is_active=True,
        )
        owner.set_password("Password123")
        db.session.add(owner)

        admin = User(
            tenant_id=tenant.id,
            email="admin@acme.com",
            first_name="Jane",
            last_name="Admin",
            role="Admin",
            is_active=True,
        )
        admin.set_password("Password123")
        db.session.add(admin)

        analyst = User(
            tenant_id=tenant.id,
            email="analyst@acme.com",
            first_name="Bob",
            last_name="Analyst",
            role="Analyst",
            is_active=True,
        )
        analyst.set_password("Password123")
        db.session.add(analyst)

        member = User(
            tenant_id=tenant.id,
            email="member@acme.com",
            first_name="Alice",
            last_name="Member",
            role="Member",
            is_active=True,
        )
        member.set_password("Password123")
        db.session.add(member)

        db.session.flush()

        # Create user preferences
        for user in [owner, admin, analyst, member]:
            prefs = UserPreferences(
                user_id=user.id,
                email_notifications_enabled=True,
                email_frequency="daily",
                theme="dark",
                timezone="America/New_York",
            )
            db.session.add(prefs)

        # Create accounts (money sources)
        accounts_data = [
            {
                "name": "Operating Account",
                "account_type": "checking",
                "currency": "USD",
                "opening_balance": Decimal("50000.00"),
                "current_balance": Decimal("50000.00"),
                "low_balance_threshold": Decimal("5000.00"),
            },
            {
                "name": "Credit Card - Business",
                "account_type": "credit_card",
                "currency": "USD",
                "opening_balance": Decimal("0.00"),
                "current_balance": Decimal("0.00"),
                "low_balance_threshold": Decimal("0.00"),
            },
            {
                "name": "Petty Cash",
                "account_type": "cash",
                "currency": "USD",
                "opening_balance": Decimal("2000.00"),
                "current_balance": Decimal("2000.00"),
                "low_balance_threshold": Decimal("500.00"),
            },
        ]

        accounts = []
        for acc_data in accounts_data:
            account = Account(tenant_id=tenant.id, **acc_data)
            db.session.add(account)
            accounts.append(account)

        db.session.flush()

        # Create categories with colors for charts
        categories_data = [
            {"name": "Software & SaaS", "color": "#3b82f6", "description": "Software licenses and subscriptions"},
            {"name": "Hardware", "color": "#10b981", "description": "Computer equipment and devices"},
            {"name": "Travel", "color": "#f59e0b", "description": "Business travel expenses"},
            {"name": "Marketing", "color": "#ec4899", "description": "Marketing and advertising"},
            {"name": "Office Supplies", "color": "#8b5cf6", "description": "Office supplies and equipment"},
            {"name": "Consulting", "color": "#06b6d4", "description": "Professional services"},
            {"name": "Training", "color": "#f97316", "description": "Employee training and development"},
            {"name": "Utilities", "color": "#84cc16", "description": "Utilities and services"},
        ]

        categories = []
        for cat_data in categories_data:
            category = Category(tenant_id=tenant.id, **cat_data)
            db.session.add(category)
            categories.append(category)

        db.session.flush()

        # Create projects with budgets
        projects_data = [
            {
                "name": "Website Redesign",
                "description": "Complete overhaul of company website",
                "start_date": date.today() - timedelta(days=90),
                "end_date": date.today() + timedelta(days=30),
                "starting_budget": Decimal("25000.00"),
                "projected_estimate": Decimal("24000.00"),
                "status": "active",
            },
            {
                "name": "Mobile App Development",
                "description": "iOS and Android app development",
                "start_date": date.today() - timedelta(days=120),
                "end_date": date.today() + timedelta(days=60),
                "starting_budget": Decimal("80000.00"),
                "projected_estimate": Decimal("85000.00"),
                "status": "active",
            },
            {
                "name": "Q4 Marketing Campaign",
                "description": "Holiday season marketing push",
                "start_date": date.today() - timedelta(days=60),
                "end_date": date.today() + timedelta(days=90),
                "starting_budget": Decimal("35000.00"),
                "projected_estimate": Decimal("33000.00"),
                "status": "active",
            },
        ]

        projects = []
        for proj_data in projects_data:
            project = Project(tenant_id=tenant.id, **proj_data)
            db.session.add(project)
            projects.append(project)

        db.session.flush()

        # Create expenses spread across 6 months for meaningful charts
        vendors = [
            "AWS", "GitHub", "Figma", "Adobe", "Microsoft", "Apple", "Dell",
            "Zoom", "Slack", "Notion", "Mailchimp", "HubSpot", "Salesforce",
            "Google Workspace", "Dropbox", "United Airlines", "Hilton Hotels"
        ]

        payment_methods = [
            PaymentMethod.CREDIT_CARD.value,
            PaymentMethod.BANK_TRANSFER.value,
            PaymentMethod.CASH.value,
        ]

        users = [owner, admin, analyst, member]
        expense_count = 0

        # Generate expenses for the past 6 months
        for month_offset in range(6):
            # Calculate month start date
            month_start = date.today() - timedelta(days=180) + timedelta(days=month_offset * 30)
            
            # Generate 15-25 expenses per month
            month_expenses = randint(15, 25)
            
            for _ in range(month_expenses):
                # Randomly decide if this is project-related
                is_project = choice([True, True, False])  # 66% project-related
                project = choice(projects) if is_project else None
                
                # Select category and account
                category = choice(categories)
                account = choice(accounts)
                
                # Generate amount based on category
                if category.name in ["Software & SaaS", "Consulting"]:
                    amount = Decimal(str(round(uniform(100, 2000), 2)))
                elif category.name == "Hardware":
                    amount = Decimal(str(round(uniform(500, 5000), 2)))
                elif category.name == "Travel":
                    amount = Decimal(str(round(uniform(200, 3000), 2)))
                else:
                    amount = Decimal(str(round(uniform(50, 1000), 2)))
                
                # Random day within the month
                expense_day = month_start + timedelta(days=randint(0, 28))
                
                expense = Expense(
                    tenant_id=tenant.id,
                    project_id=project.id if project else None,
                    account_id=account.id,
                    category_id=category.id,
                    amount=amount,
                    currency="USD",
                    expense_date=expense_day,
                    vendor=choice(vendors),
                    note=f"Demo expense for {category.name}",
                    is_project_related=is_project,
                    payment_method=choice(payment_methods),
                    status=ExpenseStatus.APPROVED.value,
                    created_by=choice(users).id,
                )
                db.session.add(expense)
                
                # Update account balance
                account.current_balance -= amount
                expense_count += 1

        db.session.flush()

        # Create budgets for active projects
        for project in projects:
            budget = Budget(
                tenant_id=tenant.id,
                name=f"{project.name} Budget",
                amount=project.starting_budget,
                currency="USD",
                period=BudgetPeriod.MONTHLY.value,
                start_date=project.start_date,
                end_date=project.end_date,
                alert_threshold=80,
                alert_enabled=True,
            )
            db.session.add(budget)

        # Create category budgets
        for category in categories[:4]:
            budget = Budget(
                tenant_id=tenant.id,
                name=f"{category.name} Monthly Budget",
                amount=Decimal("5000.00"),
                currency="USD",
                period=BudgetPeriod.MONTHLY.value,
                start_date=date.today().replace(day=1),
                end_date=(date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
                category_id=category.id,
                alert_threshold=75,
                alert_enabled=True,
            )
            db.session.add(budget)

        db.session.commit()

        logger.info("✓ Database seeded successfully")
        print("\n" + "="*70)
        print("✅ Database seeded with comprehensive demo data!")
        print("="*70)
        print(f"\n📊 DEMO TENANT: Acme Corporation")
        print(f"   Subdomain: acme.localhost:5000")
        print(f"   Plan: Pro")
        print(f"\n👥 USERS (all passwords: Password123):")
        print(f"   • owner@acme.com    - Owner (full access)")
        print(f"   • admin@acme.com    - Admin (manage users & settings)")
        print(f"   • analyst@acme.com  - Analyst (read-only reports)")
        print(f"   • member@acme.com   - Member (basic access)")
        print(f"\n💰 ACCOUNTS:")
        for account in accounts:
            print(f"   • {account.name}: ${account.current_balance:,.2f}")
        print(f"\n📁 PROJECTS:")
        for project in projects:
            print(f"   • {project.name} (${project.starting_budget:,.2f} budget)")
        print(f"\n🏷️  CATEGORIES: {len(categories)}")
        for cat in categories:
            print(f"   • {cat.name} ({cat.color})")
        print(f"\n📈 DATA:")
        print(f"   • Expenses: {expense_count} (spread across 6 months)")
        print(f"   • Budgets: {len(projects) + 4} (project + category budgets)")
        print(f"\n🚀 NEXT STEPS:")
        print(f"   1. Start the app: flask run")
        print(f"   2. Visit: http://localhost:5000")
        print(f"   3. Login with any user above")
        print(f"   4. View charts at: http://localhost:5000/dashboard")
        print("="*70 + "\n")


if __name__ == "__main__":
    seed_database()
