"""Settings de testes — SQLite em memória + Celery eager."""
from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-key-not-secret"  # noqa: S105

# SQLite em memória (rápido + isolado)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Celery eager
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Fernet key fixa para testes (não usar fora)
FERNET_KEY = "vYZTLBgnL6PtaqEXxoO9wDr0bd34iA1bpvyMcXq0BHM="  # noqa: S105

# Logging silencioso em testes
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}

# Senha hash mais rápido
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
