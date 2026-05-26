"""Settings de desenvolvimento."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0"],
)  # noqa: S104

# Dev sem Redis: eager mode
CELERY_TASK_ALWAYS_EAGER = True
