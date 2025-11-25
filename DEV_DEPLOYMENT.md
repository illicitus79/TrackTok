# TrackTok Development Deployment Guide

This guide covers setting up and running TrackTok on your **Windows development PC**.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Running with Docker (Recommended)](#running-with-docker-recommended)
- [Running Locally (Without Docker)](#running-locally-without-docker)
- [Database Management](#database-management)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
  - During installation, check "Add Python to PATH"
- **PostgreSQL 16+** - [Download](https://www.postgresql.org/download/windows/)
- **Redis** - [Download Redis for Windows](https://github.com/microsoftarchive/redis/releases)
- **Git** - [Download](https://git-scm.com/download/win)
- **Docker Desktop** (Optional, recommended) - [Download](https://www.docker.com/products/docker-desktop/)

### Recommended Tools

- **Visual Studio Code** - [Download](https://code.visualstudio.com/)
- **Postman** - [Download](https://www.postman.com/downloads/) (for API testing)
- **pgAdmin 4** - [Download](https://www.pgadmin.org/download/) (for database management)

## Initial Setup

### 1. Clone Repository

```powershell
# Navigate to your development directory
cd C:\i79\Dev

# Clone the repository (if not already cloned)
git clone https://github.com/illicitus79/TrackTok.git
cd TrackTok
```

### 2. Configure Environment

```powershell
# Copy environment template
Copy-Item .env.example .env

# Edit .env file
notepad .env
```

**Development .env Configuration:**

```env
# Flask
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True

# Database
DATABASE_URL=postgresql://tracktok:tracktok@localhost:5432/tracktok_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=dev-jwt-secret-change-in-production
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# Application
BASE_URL=http://localhost:5000
BASE_DOMAIN=localhost
TENANT_RESOLUTION=subdomain

# CORS (for local frontend development)
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# Email (local testing - uses console output)
MAIL_SERVER=localhost
MAIL_PORT=1025
MAIL_USE_TLS=False
MAIL_DEBUG=True

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/tracktok.log

# Development
TEMPLATES_AUTO_RELOAD=True
```

## Running with Docker (Recommended)

Docker provides the easiest setup with all dependencies isolated.

### 1. Start Docker Desktop

Make sure Docker Desktop is running.

### 2. Build and Start Services

```powershell
# Build and start all services (web, database, redis, worker, beat)
docker-compose up -d --build

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 3. Initialize Database

```powershell
# Run migrations
docker-compose exec web flask db upgrade

# Load demo data (optional)
docker-compose exec web python scripts/seed.py
```

### 4. Access Application

- **Web App**: http://localhost:5000
- **Swagger API Docs**: http://localhost:5000/api/docs
- **Flower (Celery Monitor)**: http://localhost:5555
- **Adminer (Database UI)**: http://localhost:8080
  - System: PostgreSQL
  - Server: db
  - Username: tracktok
  - Password: tracktok
  - Database: tracktok

### 5. Login with Demo Account

After running seed script:

- **Email**: owner@acme.com
- **Password**: Password123

### Common Docker Commands

```powershell
# Start services
docker-compose up -d

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# View logs for specific service
docker-compose logs -f web
docker-compose logs -f worker

# Rebuild after code changes (if needed)
docker-compose up -d --build

# Execute commands in container
docker-compose exec web flask shell
docker-compose exec web python scripts/seed.py

# Access database
docker-compose exec db psql -U tracktok tracktok

# Restart a specific service
docker-compose restart web
```

## Running Locally (Without Docker)

If you prefer to run services locally without Docker:

### 1. Install PostgreSQL

During installation:

- Set password for `postgres` user
- Port: 5432 (default)
- Remember the password!

Create database:

```powershell
# Open PowerShell and connect to PostgreSQL
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres

# In PostgreSQL prompt:
CREATE DATABASE tracktok_dev;
CREATE USER tracktok WITH PASSWORD 'tracktok';
GRANT ALL PRIVILEGES ON DATABASE tracktok_dev TO tracktok;
\q
```

### 2. Install Redis

Download and extract Redis for Windows, then:

```powershell
# Navigate to Redis directory
cd C:\path\to\redis

# Start Redis server (keep this terminal open)
.\redis-server.exe
```

**Or install as Windows Service:**

```powershell
.\redis-server.exe --service-install
.\redis-server.exe --service-start
```

### 3. Create Python Virtual Environment

```powershell
# Navigate to project directory
cd C:\i79\Dev\TrackTok

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install Python Dependencies

```powershell
# Make sure virtual environment is activated
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Initialize Database

```powershell
# Run migrations
flask db upgrade

# Seed demo data (optional)
python scripts/seed.py
```

### 6. Run Application

You'll need **multiple terminal windows**:

**Terminal 1 - Flask Web Server:**

```powershell
cd C:\i79\Dev\TrackTok
.\venv\Scripts\Activate.ps1
flask run --host=0.0.0.0 --port=5000
```

**Terminal 2 - Celery Worker:**

```powershell
cd C:\i79\Dev\TrackTok
.\venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

**Terminal 3 - Celery Beat (Scheduler):**

```powershell
cd C:\i79\Dev\TrackTok
.\venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app beat --loglevel=info
```

**Terminal 4 - Flower (Optional - Celery Monitor):**

```powershell
cd C:\i79\Dev\TrackTok
.\venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app flower --port=5555
```

### 7. Access Application

- **Web App**: http://localhost:5000
- **API Docs**: http://localhost:5000/api/docs
- **Flower**: http://localhost:5555

## Database Management

### Using Alembic Migrations

```powershell
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback one migration
flask db downgrade

# Show migration history
flask db history

# Show current migration
flask db current
```

### Direct Database Access

**Using psql (Command Line):**

```powershell
# Connect to database
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U tracktok -d tracktok_dev

# Common queries:
\dt                                    # List tables
\d+ expenses                          # Describe expenses table
SELECT * FROM tenants;                # View tenants
SELECT * FROM users LIMIT 10;         # View users
\q                                     # Quit
```

**Using pgAdmin:**

1. Open pgAdmin
2. Create new server connection:
   - Host: localhost
   - Port: 5432
   - Database: tracktok_dev
   - Username: tracktok
   - Password: tracktok
3. Browse tables and run queries

### Reset Database

```powershell
# Drop and recreate database
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "DROP DATABASE tracktok_dev;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE tracktok_dev;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE tracktok_dev TO tracktok;"

# Run migrations again
flask db upgrade

# Seed data
python scripts/seed.py
```

## Development Workflow

### Making Code Changes

With Docker (hot reload enabled):

```powershell
# Edit files in your favorite editor
# Changes are automatically detected

# If changes don't appear, restart:
docker-compose restart web
```

Without Docker:

```powershell
# Flask will auto-reload on code changes
# If it doesn't, restart Flask:
# Press Ctrl+C and run again:
flask run
```

### Adding New Dependencies

```powershell
# Install package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt

# If using Docker, rebuild:
docker-compose up -d --build
```

### Creating API Endpoints

1. **Define Schema** in `app/schemas/`:

```python
from marshmallow import Schema, fields

class NewResourceSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    created_at = fields.DateTime(dump_only=True)
```

2. **Create Model** in `app/models/`:

```python
from app.models.base import BaseModel

class NewResource(BaseModel):
    __tablename__ = 'new_resources'
    name = db.Column(db.String(100), nullable=False)
```

3. **Create Migration**:

```powershell
flask db migrate -m "Add new_resources table"
flask db upgrade
```

4. **Create API Endpoint** in `app/api/v1/`:

```python
from flask_smorest import Blueprint

blp = Blueprint('new_resources', __name__, url_prefix='/api/v1/new-resources')

@blp.route('/')
@blp.response(200, NewResourceSchema(many=True))
def list_resources():
    resources = NewResource.query.all()
    return resources
```

5. **Register Blueprint** in `app/__init__.py`:

```python
from app.api.v1.new_resources import blp as new_resources_blp
api.register_blueprint(new_resources_blp)
```

## Testing

### Run All Tests

```powershell
# With Docker
docker-compose exec web pytest

# Without Docker (activate venv first)
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Run Specific Tests

```powershell
# Run specific test file
pytest tests/unit/test_tenancy.py

# Run specific test
pytest tests/unit/test_tenancy.py::test_tenant_creation

# Run tests matching pattern
pytest -k "test_budget"
```

### Run Linters

```powershell
# Format code with black
black app/ tests/

# Check imports with isort
isort app/ tests/

# Run flake8
flake8 app/ tests/ --max-line-length=100
```

### Generate OpenAPI Documentation

```powershell
# Export OpenAPI spec
python scripts/export_openapi.py

# This creates:
# - openapi.json (OpenAPI 3.0 spec)
# - postman_collection.json (Postman collection)
```

## Troubleshooting

### Port Already in Use

```powershell
# Find process using port 5000
netstat -ano | findstr :5000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Database Connection Errors

**Error: "could not connect to server"**

```powershell
# Check if PostgreSQL is running
Get-Service postgresql-x64-16

# Start if stopped
Start-Service postgresql-x64-16
```

**Error: "password authentication failed"**

- Check `DATABASE_URL` in `.env`
- Verify password in PostgreSQL

### Redis Connection Errors

**Error: "Error 10061 connecting to localhost:6379"**

```powershell
# Check if Redis is running
Get-Process redis-server

# If not running, start it:
cd C:\path\to\redis
.\redis-server.exe

# Or start Windows service:
Start-Service Redis
```

### Celery Worker Issues on Windows

**Error: "Process PoolExecutor is broken"**

- Use `--pool=solo` flag:

```powershell
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

### Python Virtual Environment Issues

**Error: "cannot be loaded because running scripts is disabled"**

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Docker Issues

**Error: "docker-compose: command not found"**

- Use `docker compose` (without hyphen) for Docker Desktop

**Error: "Cannot connect to Docker daemon"**

- Make sure Docker Desktop is running

**Error: "Port is already allocated"**

- Stop other services using the port, or change port in `docker-compose.yml`

### Migration Issues

**Error: "Target database is not up to date"**

```powershell
# Run pending migrations
flask db upgrade
```

**Error: "Can't locate revision identified by 'xxxx'"**

```powershell
# Reset migrations (WARNING: loses data)
flask db downgrade base
flask db upgrade
```

### Module Import Errors

**Error: "ModuleNotFoundError: No module named 'app'"**

```powershell
# Make sure you're in project root and venv is activated
cd C:\i79\Dev\TrackTok
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### Static Files Not Loading

```powershell
# Clear browser cache
# Or use Ctrl+F5 to hard refresh

# Check if files exist in static/ directory
```

## Development Tips

### VS Code Setup

Install recommended extensions:

- Python
- Pylance
- Docker
- GitLens
- Thunder Client (API testing)

**VS Code Settings** (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}\\venv\\Scripts\\python.exe",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

### Debugging in VS Code

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Flask",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "app",
        "FLASK_ENV": "development"
      },
      "args": ["run", "--no-debugger", "--no-reload"],
      "jinja": true
    }
  ]
}
```

### Quick Commands (Create Shortcuts)

Create `dev.ps1` script:

```powershell
# Quick development commands

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('start','stop','restart','logs','shell','test','migrate','seed')]
    [string]$Command
)

switch ($Command) {
    'start' { docker-compose up -d }
    'stop' { docker-compose stop }
    'restart' { docker-compose restart web worker }
    'logs' { docker-compose logs -f web }
    'shell' { docker-compose exec web flask shell }
    'test' { docker-compose exec web pytest }
    'migrate' { docker-compose exec web flask db upgrade }
    'seed' { docker-compose exec web python scripts/seed.py }
}
```

Usage:

```powershell
.\dev.ps1 start
.\dev.ps1 logs
.\dev.ps1 test
```

## Additional Resources

- **API Documentation**: http://localhost:5000/api/docs (when running)
- **Project README**: [README.md](README.md)
- **API Reference**: [API_DOCS.md](API_DOCS.md)
- **Docker Guide**: [DOCKER_GUIDE.md](DOCKER_GUIDE.md)
- **Production Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)

## Quick Reference

### Environment URLs

| Service     | URL                            | Credentials                  |
| ----------- | ------------------------------ | ---------------------------- |
| Web App     | http://localhost:5000          | owner@acme.com / Password123 |
| Swagger API | http://localhost:5000/api/docs | -                            |
| Flower      | http://localhost:5555          | -                            |
| Adminer     | http://localhost:8080          | tracktok / tracktok          |

### Common Commands

```powershell
# Docker
docker-compose up -d              # Start services
docker-compose logs -f web        # View logs
docker-compose exec web bash      # Shell into container

# Flask
flask run                         # Start server
flask db upgrade                  # Run migrations
flask shell                       # Interactive shell

# Celery
celery -A app.tasks.celery_app worker --pool=solo    # Start worker
celery -A app.tasks.celery_app beat                  # Start scheduler

# Testing
pytest                           # Run tests
black app/                       # Format code
flake8 app/                      # Lint code
```

---

**Happy Coding! 🚀**

Last Updated: November 2025
