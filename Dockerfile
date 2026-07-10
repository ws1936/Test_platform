# === Build stage ===
FROM python:3.12-slim AS builder

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency files first for layer caching
COPY requirements.txt .

# Install dependencies into a venv
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache -r requirements.txt


# === Runtime stage ===
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src /app/src
COPY pytest.ini /app/pytest.ini

# Ensure venv binaries are on PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Run alembic migrations then start uvicorn
CMD ["sh", "-c", "cd /app/src && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
