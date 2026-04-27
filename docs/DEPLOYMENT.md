# TrackTok Deployment Guide

This guide covers deploying TrackTok to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Manual Deployment](#manual-deployment)
- [Database Setup](#database-setup)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Monitoring](#monitoring)
- [Backup & Recovery](#backup--recovery)
- [Security Checklist](#security-checklist)

## Prerequisites

### System Requirements

- **OS**: Ubuntu 22.04 LTS or similar
- **RAM**: Minimum 4GB, recommended 8GB+
- **CPU**: Minimum 2 cores, recommended 4+ cores
- **Disk**: Minimum 20GB free space
- **Docker**: 20.10+ (for containerized deployment)
- **PostgreSQL**: 16+ (if not using Docker)
- **Redis**: 7+ (if not using Docker)

### Domain & DNS

- Domain name pointing to your server
- SSL certificate (Let's Encrypt recommended)
- DNS records configured:
  - `A` record: `tracktok.yourdomain.com` → Server IP
  - `A` record: `*.tracktok.yourdomain.com` → Server IP (for subdomains)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/tracktok.git
cd tracktok
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Required Production Settings:**

```env
# Flask
FLASK_ENV=production
SECRET_KEY=<generate-strong-key>
DEBUG=False

# Database (use strong password)
DATABASE_URL=postgresql://tracktok:<strong-password>@db:5432/tracktok

# Redis (use strong password)
REDIS_URL=redis://:<strong-password>@redis:6379/0

# JWT (generate unique keys)
JWT_SECRET_KEY=<generate-strong-key>
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# Domain
BASE_DOMAIN=tracktok.yourdomain.com
ENABLE_CUSTOM_DOMAINS=True

# CORS (set your frontend domains)
CORS_ORIGINS=https://tracktok.yourdomain.com,https://app.yourdomain.com

# Email (configure SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@tracktok.com

# Security
RATELIMIT_DEFAULT=100 per hour

# Observability (optional)
SENTRY_DSN=your-sentry-dsn
PROMETHEUS_ENABLED=True
```

**Generate Secrets:**

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Docker Deployment

### Standard Deployment

1. **Build and Start Services**

   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

2. **Initialize Database**

   ```bash
   docker-compose exec web flask db upgrade
   ```

3. **Create First Tenant**

   ```bash
   docker-compose exec web flask tenants:create \
     --name "Your Company" \
     --slug yourcompany \
     --owner-email admin@yourcompany.com \
     --owner-password <secure-password>
   ```

4. **Verify Health**
   ```bash
   curl http://localhost:5000/api/v1/health
   ```

### With Nginx Reverse Proxy

Create `nginx.conf`:

```nginx
upstream tracktok_web {
    server localhost:5000;
}

server {
    listen 80;
    server_name tracktok.yourdomain.com *.tracktok.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tracktok.yourdomain.com *.tracktok.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/tracktok.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tracktok.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 16M;

    location / {
        proxy_pass http://tracktok_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }

    location /api/v1/health {
        proxy_pass http://tracktok_web;
        access_log off;
    }
}
```

Start Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Manual Deployment

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql-16 postgresql-contrib redis-server \
    nginx supervisor build-essential libpq-dev
```

### 2. Setup PostgreSQL

```bash
sudo -u postgres createuser tracktok
sudo -u postgres createdb tracktok
sudo -u postgres psql -c "ALTER USER tracktok WITH PASSWORD 'strong-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tracktok TO tracktok;"
```

### 3. Setup Application

```bash
# Create app user
sudo useradd -m -s /bin/bash tracktok
sudo su - tracktok

# Clone and setup
git clone https://github.com/yourusername/tracktok.git
cd tracktok
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with production values
```

### 4. Run Migrations

```bash
source venv/bin/activate
flask db upgrade
```

### 5. Setup Supervisor

Create `/etc/supervisor/conf.d/tracktok.conf`:

```ini
[program:tracktok-web]
command=/home/tracktok/tracktok/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 'app:create_app("production")'
directory=/home/tracktok/tracktok
user=tracktok
autostart=true
autorestart=true
stdout_logfile=/var/log/tracktok/web.log
stderr_logfile=/var/log/tracktok/web.err.log

[program:tracktok-worker]
command=/home/tracktok/tracktok/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info
directory=/home/tracktok/tracktok
user=tracktok
autostart=true
autorestart=true
stdout_logfile=/var/log/tracktok/worker.log
stderr_logfile=/var/log/tracktok/worker.err.log

[program:tracktok-beat]
command=/home/tracktok/tracktok/venv/bin/celery -A app.tasks.celery_app beat --loglevel=info
directory=/home/tracktok/tracktok
user=tracktok
autostart=true
autorestart=true
stdout_logfile=/var/log/tracktok/beat.log
stderr_logfile=/var/log/tracktok/beat.err.log
```

Start services:

```bash
sudo mkdir -p /var/log/tracktok
sudo chown tracktok:tracktok /var/log/tracktok
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status
```

## Database Setup

### Initialization

```bash
# Run migrations
flask db upgrade

# Create first tenant
flask tenants:create \
  --name "Company Name" \
  --slug company \
  --owner-email admin@company.com \
  --owner-password SecurePass123
```

### Connection Pooling

For high traffic, use PgBouncer:

```bash
sudo apt install pgbouncer
```

Configure `/etc/pgbouncer/pgbouncer.ini`:

```ini
[databases]
tracktok = host=localhost port=5432 dbname=tracktok

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
```

Update `DATABASE_URL`:

```env
DATABASE_URL=postgresql://tracktok:password@localhost:6432/tracktok
```

## SSL/TLS Configuration

### Using Let's Encrypt (Recommended)

Install Certbot:

```bash
sudo apt install certbot python3-certbot-nginx
```

Obtain certificate:

```bash
sudo certbot --nginx -d tracktok.yourdomain.com -d *.tracktok.yourdomain.com
```

Auto-renewal:

```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Manual SSL Certificate

If using custom certificate:

```bash
# Copy certificates
sudo cp fullchain.pem /etc/ssl/certs/tracktok-fullchain.pem
sudo cp privkey.pem /etc/ssl/private/tracktok-privkey.pem
sudo chmod 644 /etc/ssl/certs/tracktok-fullchain.pem
sudo chmod 600 /etc/ssl/private/tracktok-privkey.pem
```

Update nginx config with certificate paths.

## Monitoring

### Application Health

```bash
# Health check endpoint
curl https://tracktok.yourdomain.com/api/v1/health
```

### Celery Monitoring (Flower)

```bash
# Start flower (internal network only)
celery -A app.tasks.celery_app flower --port=5555 --address=127.0.0.1
```

### Log Monitoring

```bash
# Application logs
tail -f /var/log/tracktok/*.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# PostgreSQL logs
tail -f /var/log/postgresql/postgresql-16-main.log
```

### Prometheus (Optional)

Enable in `.env`:

```env
PROMETHEUS_ENABLED=True
```

Metrics available at `/metrics` endpoint.

## Backup & Recovery

### Database Backup

**Automated Daily Backup:**
Create `/usr/local/bin/backup-tracktok.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/tracktok"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T db pg_dump -U tracktok tracktok | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Keep last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/db_$DATE.sql.gz"
```

Add to crontab:

```bash
0 2 * * * /usr/local/bin/backup-tracktok.sh >> /var/log/tracktok-backup.log 2>&1
```

### Database Restore

```bash
# Stop services
docker-compose stop web worker beat

# Restore database
gunzip -c backup.sql.gz | docker-compose exec -T db psql -U tracktok tracktok

# Start services
docker-compose start web worker beat
```

### Application Files Backup

```bash
# Backup uploads and configuration
tar -czf tracktok-files-$(date +%Y%m%d).tar.gz \
  uploads/ \
  .env \
  alembic/versions/
```

## Security Checklist

### Pre-Deployment

- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Configure CORS with specific origins
- [ ] Enable rate limiting
- [ ] Set FLASK_ENV=production
- [ ] Disable DEBUG mode
- [ ] Configure proper logging
- [ ] Review all .env variables

### Network Security

- [ ] Configure firewall (UFW)
  ```bash
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 80/tcp    # HTTP
  sudo ufw allow 443/tcp   # HTTPS
  sudo ufw enable
  ```
- [ ] Close unnecessary ports
- [ ] Use VPN for database access
- [ ] Implement fail2ban
  ```bash
  sudo apt install fail2ban
  sudo systemctl enable fail2ban
  ```

### Application Security

- [ ] Use HTTPS everywhere
- [ ] Implement CSP headers
- [ ] Enable HSTS
- [ ] Configure secure cookie settings
- [ ] Implement input validation
- [ ] Use prepared statements (already done by SQLAlchemy)
- [ ] Regular dependency updates
- [ ] Enable audit logging

### Database Security

- [ ] Use strong passwords
- [ ] Restrict network access
- [ ] Enable SSL connections
- [ ] Regular backups
- [ ] Monitor slow queries
- [ ] Implement row-level security (RLS)

### Monitoring & Alerts

- [ ] Setup uptime monitoring (e.g., UptimeRobot)
- [ ] Configure error tracking (Sentry)
- [ ] Monitor disk space
- [ ] Setup log aggregation
- [ ] Create incident response plan

## Maintenance

### Updates

```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Run migrations
flask db upgrade

# Rebuild and restart (Docker)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Restart services (Manual)
sudo supervisorctl restart all
```

### Database Maintenance

```bash
# Vacuum database
docker-compose exec db psql -U tracktok tracktok -c "VACUUM ANALYZE;"

# Check table sizes
docker-compose exec db psql -U tracktok tracktok -c "\dt+"
```

### Log Rotation

Create `/etc/logrotate.d/tracktok`:

```
/var/log/tracktok/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 tracktok tracktok
    sharedscripts
    postrotate
        sudo supervisorctl restart tracktok-web tracktok-worker tracktok-beat
    endscript
}
```

## Scaling

### Horizontal Scaling

- Deploy multiple web instances behind load balancer
- Use shared Redis for sessions
- Centralized PostgreSQL with read replicas
- Distributed Celery workers

### Vertical Scaling

- Increase worker processes (gunicorn -w)
- Add more Celery worker processes
- Increase database connections
- Optimize queries with indexes

## Troubleshooting

See detailed troubleshooting in `TROUBLESHOOTING.md`

Common issues:

- **502 Bad Gateway**: Check if gunicorn is running
- **Database connection errors**: Verify DATABASE_URL and PostgreSQL status
- **Celery not processing tasks**: Check Redis connection and worker logs
- **High memory usage**: Adjust worker counts and implement caching

## Support

- **Documentation**: See README.md and API_DOCS.md
- **Issues**: https://github.com/yourusername/tracktok/issues
- **Security Issues**: Email security@tracktok.com

---

Last Updated: November 2025
