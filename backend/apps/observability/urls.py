from django.urls import path

from .views import StatusView, healthz, readyz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("api/status", StatusView.as_view(), name="api-status"),
]
