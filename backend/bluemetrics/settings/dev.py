"""Settings de desenvolvimento."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: S104

# Dev sem Redis: eager mode
CELERY_TASK_ALWAYS_EAGER = True
