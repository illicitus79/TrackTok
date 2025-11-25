# Docker Compose Quick Start

This guide will help you get TrackTok running with Docker Compose.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 4GB+ RAM available for containers

## Quick Start

1. **Copy environment file**

   ```bash
   cp .env.example .env
   ```

2. **Start all services**

   ```bash
   docker-compose up -d
   ```

3. **Initialize database**

   ```bash
   docker-compose exec web flask db upgrade
   ```

4. **Seed demo data**

   ```bash
   docker-compose exec web python scripts/seed.py
   ```

5. **Access the application**
   - Web UI: http://localhost:5000
   - API Docs: http://localhost:5000/api/docs/swagger
   - Flower (Celery monitoring): http://localhost:5555
   - Adminer (DB admin): http://localhost:8080

## Services

### Web (Flask App)

- **Container**: `tracktok-web`
- **Port**: 5000
- **Health Check**: http://localhost:5000/api/v1/health

### Database (PostgreSQL)

- **Container**: `tracktok-db`
- **Port**: 5432
- **Credentials**: tracktok / tracktok
- **Database**: tracktok

### Redis

- **Container**: `tracktok-redis`
- **Port**: 6379

### Worker (Celery)

- **Container**: `tracktok-worker`
- Processes background tasks (alerts, reports, etc.)

### Beat (Celery Scheduler)

- **Container**: `tracktok-beat`
- Schedules periodic tasks

### Flower (Celery Monitoring)

- **Container**: `tracktok-flower`
- **Port**: 5555
- Monitor Celery tasks and workers

### Adminer (Database UI)

- **Container**: `tracktok-adminer`
- **Port**: 8080
- Web-based database management

## Common Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f worker
```

### Execute Commands

```bash
# Flask shell
docker-compose exec web flask shell

# Run migrations
docker-compose exec web flask db migrate -m "Description"
docker-compose exec web flask db upgrade

# Create tenant
docker-compose exec web flask tenants:create --name "Test Org" --slug test
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart web
docker-compose restart worker
```

### Stop Services

```bash
# Stop all (keeps data)
docker-compose stop

# Stop and remove containers (keeps volumes)
docker-compose down

# Stop and remove everything including volumes
docker-compose down -v
```

### Rebuild Images

```bash
# Rebuild all images
docker-compose build

# Rebuild specific service
docker-compose build web

# Rebuild and restart
docker-compose up -d --build
```

## Development Workflow

### Making Code Changes

1. Code changes are automatically reflected (volume mount)
2. For package changes:
   ```bash
   docker-compose restart web
   docker-compose restart worker
   ```

### Database Changes

1. Create migration:

   ```bash
   docker-compose exec web flask db migrate -m "Add new field"
   ```

2. Review migration in `alembic/versions/`

3. Apply migration:
   ```bash
   docker-compose exec web flask db upgrade
   ```

### Running Tests

```bash
# Run all tests
docker-compose exec web pytest

# With coverage
docker-compose exec web pytest --cov=app --cov-report=html

# Specific test file
docker-compose exec web pytest tests/unit/test_tenancy.py
```

## Troubleshooting

### Containers Won't Start

Check logs:

```bash
docker-compose logs
```

### Database Connection Issues

1. Check if PostgreSQL is ready:

   ```bash
   docker-compose exec db pg_isready -U tracktok
   ```

2. Restart database:
   ```bash
   docker-compose restart db
   ```

### Worker Not Processing Tasks

1. Check worker logs:

   ```bash
   docker-compose logs -f worker
   ```

2. Check Flower dashboard: http://localhost:5555

3. Restart worker:
   ```bash
   docker-compose restart worker
   ```

### Port Already in Use

If port 5000 is in use, modify `docker-compose.yml`:

```yaml
web:
  ports:
    - "5001:5000" # Change 5000 to 5001
```

### Fresh Start

Complete reset (WARNING: deletes all data):

```bash
docker-compose down -v
docker-compose up -d
docker-compose exec web flask db upgrade
docker-compose exec web python scripts/seed.py
```

## Production Deployment

For production, create a `docker-compose.prod.yml`:

```yaml
version: "3.8"

services:
  web:
    environment:
      - FLASK_ENV=production
      - DEBUG=False
    command: gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'
    restart: always

  worker:
    restart: always

  beat:
    restart: always
```

Deploy:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Resource Limits

Add resource limits in `docker-compose.yml`:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 512M
        reservations:
          cpus: "0.5"
          memory: 256M
```

## Backup and Restore

### Backup Database

```bash
docker-compose exec db pg_dump -U tracktok tracktok > backup.sql
```

### Restore Database

```bash
docker-compose exec -T db psql -U tracktok tracktok < backup.sql
```

## Monitoring

### Health Checks

All services have health checks configured. View status:

```bash
docker-compose ps
```

### Celery Monitoring

Access Flower dashboard at http://localhost:5555 to monitor:

- Active tasks
- Task history
- Worker status
- Task statistics

## Security Notes

1. **Change default credentials** in `.env`
2. **Use strong secrets** for production
3. **Don't expose** PostgreSQL/Redis ports in production
4. **Use SSL/TLS** with a reverse proxy (nginx/traefik)
5. **Enable firewall** rules
6. **Regular backups** of database

## Support

- Documentation: See `README.md`
- API Docs: http://localhost:5000/api/docs/swagger
- GitHub Issues: [Report issues](https://github.com/yourusername/tracktok/issues)
