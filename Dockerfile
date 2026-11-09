# ==============================================================================
# Production Dockerfile for Predictive Maintenance Intelligence
# Compatible with Hugging Face Spaces, Render, and Container Platforms
# ==============================================================================

FROM python:3.11-slim

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    FLASK_ENV=production

# Install minimal OS dependencies for numerical libraries and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code, models, database, and templates
COPY . .

# Ensure proper permissions for appuser
RUN chown -R appuser:appuser /app

USER appuser

# Expose standard port
EXPOSE 7860

# Healthcheck probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7860/api/health || exit 1

# Start production WSGI server
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "120"]

