"""URLs raiz do projeto."""
from django.contrib import admin
from django.urls import include, path, re_path

from apps.reports.urls import api_urlpatterns as reports_api_urls
from apps.reports.urls import public_urlpatterns as reports_public_urls

# `re_path` com `/?` aceita URL com e sem trailing slash.
# Necessário porque o Next.js (proxy reverso) normaliza a URL e pode
# descartar a barra final antes de fazer rewrite para o backend.
urlpatterns = [
    path("admin/", admin.site.urls),
    # observability (healthz, readyz, /api/status)
    path("", include("apps.observability.urls")),
    # API
    re_path(r"^api/auth/?", include("apps.accounts.urls")),
    re_path(r"^api/integrations/?", include("apps.integrations.urls")),
    re_path(r"^api/sync/?", include("apps.sync.urls")),
    re_path(r"^api/dashboards/?", include("apps.analytics.urls")),
    re_path(r"^api/insights/?", include("apps.insights.urls")),
    re_path(r"^api/billing/?", include("apps.billing.urls")),
    re_path(r"^api/admin-saas/?", include("apps.admin_saas.urls")),
    re_path(r"^api/security/?", include("apps.security.urls")),
    re_path(r"^api/explorer/?", include("apps.explorer.urls")),
    re_path(r"^api/goals/?", include("apps.goals.urls")),
    re_path(r"^api/reports/?", include(reports_api_urls)),
    # Endpoint público (read-only via token opaco) — fora de /api/
    path("r/", include(reports_public_urls)),
]
