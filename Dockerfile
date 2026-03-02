FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl cron \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

FROM base AS runtime

# Install nginx for reverse proxy (dashboard + API behind single port).
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

# Security: create non-root user to run the application.
# Seguridad: crear usuario no-root para ejecutar la aplicación.
RUN groupadd -r centinel && useradd -r -g centinel -d /app -s /sbin/nologin centinel

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Ensure the app user owns necessary writable directories.
RUN mkdir -p /app/logs /app/data /app/hashes && \
    chown -R centinel:centinel /app/logs /app/data /app/hashes && \
    chmod +x /app/start.sh

USER centinel

CMD ["/app/start.sh"]
