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
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware (ordem importa!)
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # tenant injection — DEVE ficar após Authentication
    "apps.tenants.middleware.TenantContextMiddleware",
]

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

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}
