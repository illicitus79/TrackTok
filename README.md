# TrackTok

TrackTok is a multi-tenant expense tracking application built with Flask, PostgreSQL, Redis, Celery, SQLAlchemy, and Alembic.

## Features

- Multi-tenant expense, project, category, account, budget, and alert management
- Web UI with Jinja templates and static CSS/JavaScript assets
- REST API under `/api/v1/*`
- OpenAPI documentation through Swagger UI and ReDoc
- PostgreSQL schema management through Alembic migrations
- Redis-backed rate limiting and Celery background jobs

## Project Layout

```text
tracktok/
  app/                  Flask application package
    api/v1/             REST API endpoints
    core/               Configuration, extensions, security, logging
    middleware/         Request and tenancy middleware
    models/             SQLAlchemy models
    schemas/            Marshmallow schemas
    services/           Business logic services
    tasks/              Celery app and tasks
    templates/          Jinja templates
    utils/              Shared helpers
    web/                Web UI routes and forms
  docs/                 Project documentation
  docker/               Dockerfiles and container entrypoints
  migrations/           Active Alembic migration environment
  scripts/              Utility scripts
  static/               CSS, JavaScript, and image assets
  tests/                Test suite
  uploads/              Local uploaded files
```

## Launch Locally Without Docker

These steps assume Windows PowerShell from the repository root.

### 1. Install Services

Install and start PostgreSQL and Redis locally.

Create the PostgreSQL role and database if they do not already exist:

```powershell
psql -U postgres
```

```sql
CREATE USER tracktok WITH PASSWORD 'tracktok';
CREATE DATABASE tracktok OWNER tracktok;
\q
```

If your local PostgreSQL user, password, host, port, or database name differs, use those values in `DATABASE_URL`.

### 2. Create Python Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Local Environment

Do not use the Docker service hostnames (`db` or `redis`) for a non-Docker launch. Use localhost values:

```powershell
$env:FLASK_APP = "app"
$env:FLASK_ENV = "development"
$env:DATABASE_URL = "postgresql://tracktok:tracktok@localhost:5432/tracktok"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
$env:RATELIMIT_STORAGE_URL = "redis://localhost:6379/1"
$env:RATELIMIT_SWALLOW_ERRORS = "True"
```

You may also copy `.env.example` to `.env`, but adjust the database and Redis URLs to `localhost` for local execution.
If you see `Error 11001 connecting to redis:6379`, your local process is still using Docker's `redis` hostname. Replace every Redis URL in `.env` with `redis://localhost:6379/...`, or set the PowerShell variables above before running Flask.

### 4. Apply Database Migrations

```powershell
python scripts/init_db.py
```

This runs Alembic migrations from `migrations/` and updates the PostgreSQL schema to the latest revision. The equivalent Flask command is:

```powershell
flask db upgrade
```

### 5. Optional Demo Data

```powershell
python scripts/seed.py
```

### 6. Run The App

```powershell
flask run --host=127.0.0.1 --port=5000 --debug
```

Open:

- Web UI: `http://localhost:5000`
- API health check: `http://localhost:5000/api/v1/health`
- Swagger UI: `http://localhost:5000/api/docs/swagger`
- ReDoc: `http://localhost:5000/api/docs/redoc`

### 7. Run Background Workers

Use separate terminals with the same environment variables:

```powershell
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info
celery -A app.tasks.celery_app flower --port=5555
```

Flower is available at `http://localhost:5555`.

## PostgreSQL Notes

- The active migration directory is `migrations/`.
- The root `alembic.ini` points to `migrations/`, so both `alembic upgrade head` and `flask db upgrade` use the same migration history.
- `scripts/init_db.py` applies migrations instead of calling `db.create_all()`, so schema changes are tracked consistently.
- The default local database URL is `postgresql://tracktok:tracktok@localhost:5432/tracktok`.
- Docker Compose maps PostgreSQL to host port `5433`, but inside Docker the app uses `db:5432`. Do not use `db:5432` for a non-Docker app process.

## Useful Commands

```powershell
flask db current
flask db heads
flask db migrate -m "describe schema change"
flask db upgrade
pytest
```

## Docker

Docker remains available if needed:

```powershell
docker compose up -d
docker compose exec web python scripts/init_db.py
docker compose exec web python scripts/seed.py
```

### Updating Docker After Local Changes

If the containers are already running and you only changed Python, template, CSS, or JavaScript files, restart the app services:

```powershell
docker compose restart web worker beat
```

Use a full rebuild when you change dependencies, Dockerfiles, `.env`, Compose files, or anything that affects the container image:

```powershell
docker compose down
docker compose up -d --build
docker compose exec web python scripts/init_db.py
```

Run `scripts/init_db.py` after pulling or creating database migration changes. It applies Alembic migrations and keeps PostgreSQL at the latest schema revision.

Check the web container logs if the app does not start or a request fails:

```powershell
docker compose logs -f web
```

See [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) for Docker-specific notes.

## Documentation

- [API docs](docs/API_DOCS.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Development](docs/DEVELOPMENT.md)
- [OpenAPI export](docs/OPENAPI_EXPORT.md)
- [OpenAPI implementation](docs/OPENAPI_IMPLEMENTATION.md)
- [Network troubleshooting](docs/NETWORK_TROUBLESHOOTING.md)
- [Project summary](docs/PROJECT_SUMMARY.md)

## Configuration

Important environment variables:

```env
FLASK_APP=app
FLASK_ENV=development
DATABASE_URL=postgresql://tracktok:tracktok@localhost:5432/tracktok
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
RATELIMIT_STORAGE_URL=redis://localhost:6379/1
RATELIMIT_SWALLOW_ERRORS=True
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me-too
```

Set `TRACKTOK_SKIP_DOTENV=true` when running diagnostics that must not load `.env`.
