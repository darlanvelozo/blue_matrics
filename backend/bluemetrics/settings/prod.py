"""Settings de produção."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Segurança HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Banco em prod é obrigatoriamente Postgres (definido em DATABASE_URL)
assert env("DATABASE_URL", default=""), "DATABASE_URL é obrigatório em produção"

# FERNET_KEY obrigatório
assert env("FERNET_KEY", default=""), "FERNET_KEY é obrigatório em produção"
