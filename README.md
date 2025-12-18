# TrackTok - Multi-Tenant Expense Tracker

[![CI](https://github.com/yourusername/tracktok/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/tracktok/actions)
[![Coverage](https://codecov.io/gh/yourusername/tracktok/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/tracktok)

A production-ready, API-first multi-tenant expense tracking platform built with Flask, PostgreSQL, Redis, and Celery.

## 🚀 Features

- **Multi-Tenancy**: Single-database architecture with subdomain/header-based tenant resolution
- **RESTful API**: Full-featured `/api/v1/*` endpoints with OpenAPI 3.0 documentation
- **Interactive API Docs**: Swagger UI and ReDoc for testing and exploring the API
- **Postman Integration**: Auto-generated Postman collection for easy API testing
- **Authentication**: JWT-based auth with refresh tokens
- **Authorization**: Role-based access control (Owner, Admin, Analyst, Member)
- **Budget Management**: Set budgets with automated alert system
- **Real-time Analytics**: Interactive charts powered by Chart.js
- **Background Jobs**: Celery-based async task processing
- **Themeable UI**: Light/dark mode using CSS variables
- **Audit Trail**: Immutable financial record tracking
- **Rate Limiting**: Redis-powered API rate limiting
- **Production-Ready**: Docker, CI/CD, comprehensive test coverage

## Plan tiers (current defaults)

- **Basic (default)**: 1 user, 3 projects, 3 accounts, up to 100 expenses per project (soft cap), total expense safety cap 100,000.
- **Professional**: Higher limits (multi-user coming later). Pricing coming soon.
- Tier changes are managed from the Tenants admin screen (restricted to the tier admin account).

## 📋 Tech Stack

**Backend:**

- Python 3.11+
- Flask 3.x
- SQLAlchemy 2.x + Alembic
- PostgreSQL 16
- Redis 7
- Celery 5.x
- Flask-JWT-Extended
- Flask-Smorest (OpenAPI)
- Marshmallow 3.x

**Frontend:**

- Jinja2 templates
- Custom CSS (theme variables)
- Chart.js 4.x

**DevOps:**

- Docker & Docker Compose
- GitHub Actions
- pytest + factory_boy

## 🏗️ Architecture

```
tracktok/
├── app/
│   ├── api/v1/          # REST API endpoints
│   ├── core/            # Core configs, extensions, tenancy
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Marshmallow schemas
│   ├── tasks/           # Celery background tasks
│   ├── utils/           # RBAC decorators, helpers
│   ├── web/             # Web UI views
│   └── templates/       # Jinja2 templates
├── alembic/             # Database migrations
├── docker/              # Dockerfiles
├── scripts/             # Utility scripts
├── static/              # CSS, JS, images
└── tests/               # Test suite
```

## 🛠️ Quick Start

### Using Docker (Recommended)

```powershell
# Clone repository
git clone https://github.com/yourusername/tracktok.git
cd tracktok

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Initialize database
docker-compose exec web python scripts/init_db.py

# Seed demo data
docker-compose exec web python scripts/seed.py

# Access the application
# Web UI: http://localhost:5000
# API Docs: http://localhost:5000/api/docs/swagger
# Flower (Celery): http://localhost:5555
```

### Local Development

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
$env:FLASK_APP="app"
$env:FLASK_ENV="development"
$env:DATABASE_URL="postgresql://tracktok:tracktok@localhost:5432/tracktok"

# Initialize database
python scripts/init_db.py

# Run migrations
flask db upgrade

# Seed demo data
python scripts/seed.py

# Run development server
flask run

# Run Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Run Celery beat (separate terminal)
celery -A app.tasks.celery_app beat --loglevel=info
```

## Navigation & help

- The top nav now uses a book icon that links to the “How to use” guide covering onboarding steps, analytics, and tips.
- Use the Settings page to set tenant currency, timezone, and date format so dashboards, budgets, and alerts stay consistent across the workspace.

## 📝 API Documentation

### Interactive Documentation

Access comprehensive API documentation:

- **Swagger UI**: `http://localhost:5000/api/docs/swagger` - Interactive testing interface
- **ReDoc**: `http://localhost:5000/api/docs/redoc` - Clean, readable documentation

### Export OpenAPI Specification

```powershell
# Export OpenAPI JSON
python scripts/export_openapi.py --openapi -o openapi.json
make openapi

# Export Postman collection
python scripts/export_openapi.py --postman -o postman_collection.json
make postman

# Export both
python scripts/export_openapi.py --both
make docs
```

### Postman Setup

1. Export the collection: `make postman`
2. Import `postman_collection.json` into Postman
3. Set collection variables:
   - `base_url`: `http://localhost:5000`
   - `jwt_token`: Obtain from login endpoint
   - `tenant_id`: Your tenant ID

See [API_DOCS.md](./API_DOCS.md) for detailed API documentation.

### API Features

- **OpenAPI 3.0** specification
- **Bearer token** authentication
- **Multi-tenant** support (subdomain or header-based)
- **Rate limiting** with headers
- **Pagination** metadata
- **Error schemas** with validation details
- **Security schemes** documentation

## 🔐 Authentication

### Register New Tenant

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "name": "Acme Corp",
  "subdomain": "acme",
  "owner_email": "owner@acme.com",
  "owner_password": "SecurePass123",
  "owner_first_name": "John",
  "owner_last_name": "Doe"
}
```

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json
X-Tenant-Id: <tenant-id>

{
  "email": "owner@acme.com",
  "password": "SecurePass123"
}
```

Response includes `access_token` and `refresh_token`.

### Access Protected Endpoints

```http
GET /api/v1/expenses
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant-id>
```

## 🧪 Testing

```powershell
# Run all tests with coverage
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m tenancy
pytest -m rbac

# Generate HTML coverage report
pytest --cov=app --cov-report=html
```

## 📊 Database Migrations

```powershell
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade
```

## 🔧 Configuration

Key environment variables (see `.env.example`):

```env
# Flask
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Multi-Tenancy
TENANT_RESOLUTION=subdomain  # or header
BASE_DOMAIN=localhost:5000
```

## 📦 Deployment

### Production Checklist

- [ ] Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Configure production database (PostgreSQL)
- [ ] Set up Redis instance
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS origins
- [ ] Set up Sentry for error tracking
- [ ] Enable Prometheus metrics (optional)
- [ ] Configure email service for notifications
- [ ] Set up automated backups
- [ ] Review rate limiting settings

### Docker Production

```powershell
# Build production image
docker build -f docker/Dockerfile -t tracktok:latest .

# Run with production config
docker-compose -f docker-compose.prod.yml up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Flask ecosystem
- Chart.js
- PostgreSQL & Redis teams

---

Built with ❤️ using Flask & Python

For questions or support, please open an issue on GitHub.
