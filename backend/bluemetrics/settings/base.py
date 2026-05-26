"""
Base settings for BlueMetrics.

Lê variáveis de ambiente via django-environ. Os settings específicos
(dev/test/prod) sobrescrevem o que precisarem.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BASE_DIR.parent  # repo root

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
)
# Lê .env do repo root se existir (modo dev local sem Docker)
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.tenants",
    "apps.accounts",
    "apps.integrations",
    "apps.sync",
    "apps.analytics",
    "apps.insights",
    "apps.billing",
    "apps.admin_saas",
    "apps.security",
    "apps.observability",
    "apps.explorer",
    "apps.goals",
    "apps.reports",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware (ordem importa!)
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # tenant injection — DEVE ficar após Authentication
    "apps.tenants.middleware.TenantContextMiddleware",
    # security headers — sempre depois (aplica em todas as respostas)
    "apps.security.middleware.SecurityHeadersMiddleware",
    # request_id + structured log (último — captura status final)
    "apps.observability.middleware.RequestLogMiddleware",
]

# ---------------------------------------------------------------------------
# App version (lido por /api/status)
# ---------------------------------------------------------------------------
APP_VERSION = "0.11.0"

ROOT_URLCONF = "bluemetrics.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "bluemetrics.wsgi.application"

# ---------------------------------------------------------------------------
# Database — Postgres em prod/dev-docker; SQLite como fallback dev local.
# ---------------------------------------------------------------------------
if env("DATABASE_URL", default=""):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# i18n / timezone
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# DRF + JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PARSER_CLASSES": ("rest_framework.parsers.JSONParser",),
    "EXCEPTION_HANDLER": "apps.accounts.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGIN_REGEXES = env.list(
    "CORS_ALLOWED_ORIGIN_REGEXES",
    default=[],
)

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# CSRF: confiar em origens externas (ex.: Cloudflare Tunnel)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[],
)

# Atrás de proxy (Cloudflare Tunnel → Next.js → gunicorn): respeitar X-Forwarded-Proto
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="memory://")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="cache+memory://")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Crypto (Conta Azul tokens etc.)
# ---------------------------------------------------------------------------
FERNET_KEY = env("FERNET_KEY", default="")

# ---------------------------------------------------------------------------
# LLM (Insights enrichment)
# ---------------------------------------------------------------------------
# Provider: "openai" | "anthropic" | "disabled"
INSIGHT_LLM_PROVIDER = env("INSIGHT_LLM_PROVIDER", default="disabled")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_BASE_URL = env("OPENAI_BASE_URL", default="https://api.openai.com/v1")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", default="claude-sonnet-4-6")

# ---------------------------------------------------------------------------
# Stripe (Billing)
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

# ---------------------------------------------------------------------------
# Conta Azul
# ---------------------------------------------------------------------------
CONTA_AZUL = {
    "CLIENT_ID": env("CONTA_AZUL_CLIENT_ID", default=""),
    "CLIENT_SECRET": env("CONTA_AZUL_CLIENT_SECRET", default=""),
    "REDIRECT_URI": env(
        "CONTA_AZUL_REDIRECT_URI",
        default="http://localhost:8000/api/integrations/contaazul/callback",
    ),
    "AUTH_URL": env("CONTA_AZUL_AUTH_URL", default="https://auth.contaazul.com/oauth2/authorize"),
    "TOKEN_URL": env("CONTA_AZUL_TOKEN_URL", default="https://auth.contaazul.com/oauth2/token"),
    "API_BASE": env("CONTA_AZUL_API_BASE", default="https://api-v2.contaazul.com/v1"),
    "SCOPE": "openid profile aws.cognito.signin.user.admin",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

LOG_JSON = env.bool("LOG_JSON", default=False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "json": {
            "()": "apps.observability.logging.JSONFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if LOG_JSON else "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "bluemetrics.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Sentry (opcional) — só ativa se SENTRY_DSN setada
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="production")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1)
SENTRY_PROFILES_SAMPLE_RATE = env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.0)

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=SENTRY_ENVIRONMENT,
            release=env("APP_VERSION", default=""),
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                LoggingIntegration(event_level=None),  # breadcrumbs only
            ],
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
            send_default_pii=False,
        )
    except ImportError:
        # SDK não instalado — segue sem observability
        pass

REDIS_URL = env("REDIS_URL", default="")

# ---------------------------------------------------------------------------
# Email — provider plugável via SMTP (Resend, SES, Mailgun, Gmail, etc.)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=15)
DEFAULT_FROM_EMAIL = env("EMAIL_FROM", default="BI AZUL <no-reply@biazul.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL  # erros do Django
