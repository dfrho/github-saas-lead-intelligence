FROM python:3.11-slim-bookworm

# Install system deps needed by psycopg binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests first so Docker caches this layer.
# requirements-lock.txt pins every package so builds are reproducible and auditable.
COPY pyproject.toml requirements-lock.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -c requirements-lock.txt -e "."

# Copy source
COPY src/ ./src/

# Railway injects $PORT — default to 8000 for local use
EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
