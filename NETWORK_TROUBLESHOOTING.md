# TrackTok - Network Troubleshooting Guide

## 🚨 SSL Certificate / Corporate Proxy Issues

You're experiencing SSL certificate verification failures due to a corporate network proxy/firewall. Here are your options:

---

## Option 1: Configure Corporate Proxy (Recommended)

### For pip (Python packages):

```powershell
# Create/edit pip.ini in %APPDATA%\pip\ (usually C:\Users\<username>\AppData\Roaming\pip\)
mkdir $env:APPDATA\pip -Force
@"
[global]
trusted-host = pypi.org
               files.pythonhosted.org
               pypi.python.org
cert = C:\path\to\your\corporate\certificate.crt
"@ | Out-File -FilePath "$env:APPDATA\pip\pip.ini" -Encoding utf8
```

### For Docker:

**Create `docker/daemon.json`** (for Docker Desktop):
```json
{
  "insecure-registries": [],
  "registry-mirrors": [],
  "proxies": {
    "http-proxy": "http://your-proxy:port",
    "https-proxy": "http://your-proxy:port"
  }
}
```

---

## Option 2: Use Pre-downloaded Dependencies

### Download packages offline:

```powershell
# On a machine WITH internet access:
pip download -r requirements.txt -d packages/

# Copy the `packages/` folder to your project

# On your restricted machine:
pip install --no-index --find-links=packages/ -r requirements.txt
```

---

## Option 3: Run with Existing Database (Skip Docker)

Since you have network restrictions, let's use **local installations** instead of Docker:

### Prerequisites:
1. **Install PostgreSQL locally**: https://www.postgresql.org/download/windows/
2. **Install Redis locally**: https://github.com/microsoftarchive/redis/releases (or use Memurai)

### Setup Steps:

```powershell
# 1. Start PostgreSQL (install as Windows service or run manually)
# - Create database: CREATE DATABASE tracktok;
# - Create user: CREATE USER tracktok WITH PASSWORD 'password';
# - Grant privileges: GRANT ALL PRIVILEGES ON DATABASE tracktok TO tracktok;

# 2. Start Redis
# - Install and run as Windows service OR:
redis-server

# 3. Install Python dependencies (if you can resolve SSL):
.\venv\Scripts\activate
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# 4. Copy .env.example to .env
cp .env.example .env

# 5. Edit .env with your local database settings:
# DATABASE_URL=postgresql://tracktok:password@localhost:5432/tracktok
# REDIS_URL=redis://localhost:6379/0

# 6. Initialize database
flask db upgrade

# 7. Seed demo data
python scripts/seed.py

# 8. Run application
flask run

# 9. In another terminal - run Celery worker
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# 10. In another terminal - run Celery beat scheduler
celery -A app.tasks.celery_app beat --loglevel=info
```

---

## Option 4: Contact IT Department

Request the following:

1. **Whitelist PyPI domains**:
   - pypi.org
   - files.pythonhosted.org
   - pypi.python.org

2. **Provide corporate SSL certificate** for pip/Docker

3. **Configure internal PyPI mirror** (if available)

---

## Option 5: Use Windows Subsystem for Linux (WSL2)

WSL2 sometimes bypasses corporate network issues:

```powershell
# Install WSL2
wsl --install

# Inside WSL2:
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql redis-server
# ... then follow Linux setup instructions
```

---

## Quick Test: Check Network Access

```powershell
# Test PyPI access
Invoke-WebRequest https://pypi.org/simple/flask/ -UseBasicParsing

# If this fails, you have a network restriction issue
```

---

## Current Error Analysis

Your error shows:
```
ERROR: HTTP error 403 while getting https://files.pythonhosted.org/...
ERROR: 403 Client Error: Forbidden
```

**This means**: Your corporate proxy/firewall is **actively blocking** PyPI downloads (403 Forbidden).

**You must**:
- Get IT to whitelist PyPI domains, OR
- Use a pre-downloaded package cache, OR
- Work from a different network (home/VPN), OR
- Use an internal PyPI mirror if your company has one

---

## Alternative: Minimal Setup Without All Dependencies

If you just want to explore the code structure:

```powershell
# Install only Flask and SQLAlchemy
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org flask sqlalchemy flask-sqlalchemy

# You won't be able to run the full app, but can review code
```

---

## Next Steps

1. **Contact your IT department** - most direct solution
2. **Try WSL2** - often bypasses Windows network restrictions  
3. **Use a personal hotspot** - temporary solution for testing
4. **Request VPN access** - if company policy allows

Let me know which approach you'd like to pursue!
