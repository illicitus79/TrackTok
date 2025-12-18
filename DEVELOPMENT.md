# TrackTok Development Notes

## Getting Started

### First Time Setup

1. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Set Up Database**
   ```powershell
   # Start PostgreSQL (via Docker or local)
   docker-compose up -d db
   
   # Initialize database
   python scripts/init_db.py
   
   # Seed demo data
   python scripts/seed.py
   ```

3. **Run Application**
   ```powershell
   # Terminal 1: Web server
   flask run
   
   # Terminal 2: Celery worker
   celery -A app.tasks.celery_app worker --loglevel=info
   
   # Terminal 3: Celery beat (scheduler)
   celery -A app.tasks.celery_app beat --loglevel=info
   ```

### Demo Credentials

After seeding, use these credentials:

- **URL**: http://acme.localhost:5000 (or use X-Tenant-Id header)
- **Owner**: owner@acme.com / Password123
- **Admin**: admin@acme.com / Password123
- **Member**: member@acme.com / Password123

### Testing Multi-Tenancy

#### Via Subdomain (Development)
Add to your hosts file (`C:\Windows\System32\drivers\etc\hosts`):
```
127.0.0.1 acme.localhost
127.0.0.1 demo.localhost
```

Then access: `http://acme.localhost:5000`

#### Via Header
```http
GET /api/v1/expenses
Authorization: Bearer <token>
X-Tenant-Id: <tenant-id>
```

## Navigation & help

- The top nav includes a book icon that links to the in-app “How to use” guide for onboarding and dashboard tips.
- Settings (currency, timezone, date format) should be configured early so budgets, alerts, and analytics render consistently across the tenant.

## Plan tiers (current defaults)

- **Basic (default)**: 1 user, 3 projects, 3 accounts, up to 100 expenses per project (soft cap), total expense safety cap 100,000.
- **Professional**: Higher limits (multi-user coming later). Pricing coming soon.
- Tier changes are managed from the Tenants admin screen (restricted to the tier admin account).

## Architecture Decisions

### Multi-Tenancy Strategy
- **Single database, single schema** with `tenant_id` discriminator
- Auto-filtering via custom Query class
- Enforced at middleware level
- Benefits: Cost-effective, easier backups, simpler ops
- Trade-offs: Requires careful query auditing

### Security
- JWT access tokens (1 hour expiry)
- JWT refresh tokens (30 days expiry)
- Bcrypt password hashing
- Rate limiting via Redis
- RBAC with 4 roles (Owner > Admin > Analyst > Member)

### Background Jobs
- Celery for async task processing
- Daily budget alert checks (9 AM)
- Monthly report generation (1st of month)
- Redis as message broker

## API Examples

### Register New Tenant
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "name": "Demo Corp",
  "subdomain": "demo",
  "owner_email": "admin@demo.com",
  "owner_password": "SecurePass123!",
  "owner_first_name": "Jane",
  "owner_last_name": "Doe"
}
```

### Create Expense
```http
POST /api/v1/expenses/
Authorization: Bearer <token>
X-Tenant-Id: <tenant-id>
Content-Type: application/json

{
  "amount": "125.50",
  "title": "Office Supplies",
  "description": "Printer paper and pens",
  "category_id": "<category-id>",
  "expense_date": "2025-01-15",
  "payment_method": "credit_card",
  "tags": ["office", "supplies"]
}
```

### Create Budget
```http
POST /api/v1/budgets/
Authorization: Bearer <token>
X-Tenant-Id: <tenant-id>
Content-Type: application/json

{
  "name": "Monthly Office Budget",
  "amount": "5000.00",
  "period": "monthly",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "alert_threshold": 80,
  "alert_enabled": true
}
```

## Development Tips

### Database Migrations
```powershell
# Create migration after model changes
flask db migrate -m "Add new field"

# Review generated migration in alembic/versions/

# Apply migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

### Testing
```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific markers
pytest -m tenancy
pytest -m rbac
pytest -m integration
```

### Debugging
```powershell
# Enable SQL query logging
$env:SQLALCHEMY_ECHO="True"

# Enable debug mode
$env:DEBUG="True"

# View Celery task queue
celery -A app.tasks.celery_app inspect active

# Monitor with Flower
celery -A app.tasks.celery_app flower
# Then visit http://localhost:5555
```

## Production Deployment

### Environment Variables
Ensure these are set in production:
```env
SECRET_KEY=<strong-random-key>
JWT_SECRET_KEY=<strong-random-key>
DATABASE_URL=<production-db-url>
REDIS_URL=<production-redis-url>
FLASK_ENV=production
DEBUG=False
```

### Security Checklist
- [ ] Generate strong secrets
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable audit logging
- [ ] Configure Sentry/error tracking
- [ ] Set up database backups
- [ ] Review user permissions

## Troubleshooting

### Common Issues

**Issue**: "Tenant not found" errors
- Solution: Ensure X-Tenant-Id header is set or using correct subdomain

**Issue**: JWT token expired
- Solution: Use refresh endpoint `/api/v1/auth/refresh`

**Issue**: Database connection errors
- Solution: Check PostgreSQL is running, verify DATABASE_URL

**Issue**: Celery tasks not running
- Solution: Ensure Redis is running, check worker logs

## Next Steps / Roadmap

- [ ] Add email notifications (SendGrid/SES integration)
- [ ] Implement file upload for receipts (S3/local storage)
- [ ] Add recurring expense automation
- [ ] Build advanced analytics dashboard
- [ ] Add export functionality (CSV, PDF)
- [ ] Implement multi-currency support
- [ ] Add invoice generation
- [ ] Create mobile app API
- [ ] Add team collaboration features
- [ ] Implement approval workflows

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Chart.js](https://www.chartjs.org/)

---
Last updated: 2025-01-15
