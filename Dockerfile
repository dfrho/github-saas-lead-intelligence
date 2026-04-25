FROM python:3.11-slim-bookworm

# Install system deps needed by psycopg binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifest first so Docker caches this layer
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e "."

# Copy source
COPY src/ ./src/

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI + embedded APScheduler
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
