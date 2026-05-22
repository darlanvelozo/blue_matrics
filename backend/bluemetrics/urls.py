"""URLs raiz do projeto."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/integrations/", include("apps.integrations.urls")),
    path("api/sync/", include("apps.sync.urls")),
    path("api/dashboards/", include("apps.analytics.urls")),
    path("api/insights/", include("apps.insights.urls")),
    path("api/billing/", include("apps.billing.urls")),
]
