FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install only runtime system dependencies (no build-essential in final image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# --- Builder stage: install Python deps in isolation ---
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
