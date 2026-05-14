from django.urls import path

from .views import LogsView, RunNowView

urlpatterns = [
    path("logs", LogsView.as_view(), name="sync-logs"),
    path("run", RunNowView.as_view(), name="sync-run"),
]
