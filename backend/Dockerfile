# =============================================================================
# BlueMetrics — Backend Dockerfile (multi-stage, slim, production-ready)
# =============================================================================

# ---- builder ----------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# build deps (psycopg precisa de libpq + headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# instala apenas runtime deps (sem [dev]) num venv isolado
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install \
        Django>=5,<5.2 djangorestframework djangorestframework-simplejwt \
        django-cors-headers django-environ "psycopg[binary]" redis celery \
        django-celery-beat httpx cryptography structlog python-dateutil \
        gunicorn

# ---- runtime ----------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=bluemetrics.settings.prod \
    LOG_JSON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -d /app -s /bin/bash app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . /app

# coletar static files (admin, DRF browsable)
RUN /opt/venv/bin/python manage.py collectstatic --noinput || true

USER app
EXPOSE 8000

# liveness probe: docker faz health check usando /healthz
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# gunicorn em multi-worker. Workers = (2 * cores) + 1 ajustado em runtime
CMD ["gunicorn", "bluemetrics.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
