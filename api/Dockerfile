# CloudRun最適化 Dockerfile for Kaboom Stock Trading API
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
COPY uv.lock ./

RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS production

WORKDIR /app

RUN useradd -m -u 1000 kaboom && chown -R kaboom:kaboom /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv

COPY --chown=kaboom:kaboom app/ /app/app/
COPY --chown=kaboom:kaboom batch/ /app/batch/
COPY --chown=kaboom:kaboom alembic.ini /app/alembic.ini
COPY --chown=kaboom:kaboom alembic/ /app/alembic/
COPY --chown=kaboom:kaboom main.py /app/main.py

USER kaboom

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

ENV PORT=8080

ENV WORKERS=1 \
    WORKER_CLASS=uvicorn.workers.UvicornWorker \
    WORKER_CONNECTIONS=1000 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=100 \
    TIMEOUT=60 \
    KEEPALIVE=5

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

CMD [
  "gunicorn",
  "app.main:app",
  "--bind",
  "0.0.0.0:8080",
  "--workers",
  "1",
  "--worker-class",
  "uvicorn.workers.UvicornWorker",
  "--worker-connections",
  "1000",
  "--max-requests",
  "1000",
  "--max-requests-jitter",
  "100",
  "--timeout",
  "60",
  "--keepalive",
  "5",
  "--access-logfile",
  "-",
  "--error-logfile",
  "-",
  "--log-level",
  "info"
]
