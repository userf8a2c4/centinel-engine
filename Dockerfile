FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl cron \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main

COPY . /app

FROM base AS runtime

# Security: create non-root user to run the application.
# Seguridad: crear usuario no-root para ejecutar la aplicación.
RUN groupadd -r centinel && useradd -r -g centinel -d /app -s /sbin/nologin centinel

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Ensure the app user owns necessary writable directories.
RUN mkdir -p /app/logs /app/data /app/hashes && \
    chown -R centinel:centinel /app/logs /app/data /app/hashes

USER centinel

CMD ["python", "scripts/run_pipeline.py", "--once"]
