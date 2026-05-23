"""
Settings de produção do BI AZUL — herda da base com DEBUG=False e segurança.
Roda atrás de Nginx que termina TLS; backend só recebe HTTP local.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["biazul.com", "www.biazul.com"])

# Atrás de Nginx (TLS termina lá)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Cookies seguros (HTTPS only)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS leve (sem subdomínios pra não bloquear subdomínios futuros)
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 dias
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Banco em prod é obrigatoriamente Postgres
assert env("DATABASE_URL", default=""), "DATABASE_URL é obrigatório em produção"
assert env("FERNET_KEY", default=""), "FERNET_KEY é obrigatório em produção"
assert env("SECRET_KEY", default=""), "SECRET_KEY é obrigatório em produção"

# Celery: prefere eager em VPS de 1 vCPU (sem worker dedicado)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
