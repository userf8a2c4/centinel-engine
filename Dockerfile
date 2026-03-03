FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install only runtime system dependencies (no build-essential in final image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# --- Frontend builder stage: build React app with Node.js ---
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json* ./
RUN npm ci --ignore-scripts
COPY dashboard/frontend/ ./
RUN npm run build

# --- Python builder stage: install Python deps in isolation ---
FROM base AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements-prod.txt

# --- Runtime stage ---
FROM base AS runtime

# Security: non-root user.
RUN groupadd -r centinel && useradd -r -g centinel -d /app -s /sbin/nologin centinel

# Copy installed Python packages from builder.
COPY --from=builder /install /usr/local

# Copy application source.
COPY . /app

# Copy React build output into static directory served by FastAPI.
COPY --from=frontend-builder /frontend/dist /app/static/dashboard

# Writable directories for runtime data.
RUN mkdir -p /app/logs /app/data /app/hashes && \
    chown -R centinel:centinel /app/logs /app/data /app/hashes

EXPOSE 8080

USER centinel

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:8080/live || exit 1

CMD ["gunicorn", "api.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "4", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "65", \
     "--access-logfile", "-"]
