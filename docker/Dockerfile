# Multi-stage build for production-ready image
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org" && \
    pip config set global.cert /etc/ssl/certs/ca-certificates.crt || true && \
    pip install --no-cache-dir -r requirements.txt || \
    (pip config set global.cert "" && pip install --no-cache-dir -r requirements.txt)

# Final stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV AUTO_MIGRATE_ON_START=1

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 tracktok && chown -R tracktok:tracktok /app
USER tracktok

# Copy application code
COPY --chown=tracktok:tracktok . .

# Entrypoint to run migrations (controlled via AUTO_MIGRATE_ON_START)
RUN chmod +x docker/entrypoint.sh

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

# Default command
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
