# Manic AI Orchestrator — Dockerfile
FROM python:3.12-slim-bookworm

# Install git (required for coding agents) + WeasyPrint system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY frontend ./frontend

# Create non-root user for security
RUN groupadd -r manic && useradd -r -g manic -d /app manic \
    && chown -R manic:manic /app
USER manic

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
