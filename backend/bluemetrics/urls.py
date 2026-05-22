"""URLs raiz do projeto."""
from django.contrib import admin
from django.urls import include, path

from apps.reports.urls import api_urlpatterns as reports_api_urls
from apps.reports.urls import public_urlpatterns as reports_public_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    # observability (healthz, readyz, /api/status)
    path("", include("apps.observability.urls")),
    # API
    path("api/auth/", include("apps.accounts.urls")),
    path("api/integrations/", include("apps.integrations.urls")),
    path("api/sync/", include("apps.sync.urls")),
    path("api/dashboards/", include("apps.analytics.urls")),
    path("api/insights/", include("apps.insights.urls")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/admin-saas/", include("apps.admin_saas.urls")),
    path("api/security/", include("apps.security.urls")),
    path("api/explorer/", include("apps.explorer.urls")),
    path("api/goals/", include("apps.goals.urls")),
    path("api/reports/", include(reports_api_urls)),
    # Endpoint público (read-only via token opaco) — fora de /api/
    path("r/", include(reports_public_urls)),
]
