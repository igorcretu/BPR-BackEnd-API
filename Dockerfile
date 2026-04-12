# Production-ready Dockerfile for BPR Backend API
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies including Playwright requirements
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    procps \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (chromium only for efficiency)
# Install browser first, then dependencies separately with error handling
RUN playwright install chromium

# Install Playwright system dependencies
# Use --allow-change-held-packages and || true to handle missing packages gracefully
RUN playwright install-deps chromium || \
    (apt-get update && apt-get install -y --no-install-recommends \
    fonts-unifont \
    fonts-ubuntu \
    && rm -rf /var/lib/apt/lists/*) || true

# Copy application code
COPY . .

# Create logs directory and verify models
RUN mkdir -p /app/logs && \
    chmod -R 777 /app/logs && \
    echo "Checking model files in app/models:" && \
    ls -lh /app/app/models/ || echo "Models directory is empty"

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with Gunicorn for production
# Configuration:
# - workers: 4 (adjust based on CPU cores: 2-4 x NUM_CORES)
# - threads: 2 per worker (for I/O bound tasks)
# - timeout: 120s (for ML predictions)
# - worker-class: sync (compatible with Flask-SQLAlchemy)
# - max-requests: 1000 (restart workers after 1000 requests to prevent memory leaks)
# - access-log: - (log to stdout for Docker)
# - error-log: - (log to stderr for Docker)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "2", \
     "--timeout", "120", \
     "--worker-class", "sync", \
     "--worker-tmp-dir", "/dev/shm", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--capture-output", \
     "app.main:app"]