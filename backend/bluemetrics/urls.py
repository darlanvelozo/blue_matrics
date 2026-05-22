"""URLs raiz do projeto."""
from django.contrib import admin
from django.urls import include, path

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
]
