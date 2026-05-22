from django.urls import path

from .views import AuditLogView, DeleteMyAccountView, ExportMyDataView

urlpatterns = [
    path("me/export", ExportMyDataView.as_view(), name="lgpd-export"),
    path("me/delete", DeleteMyAccountView.as_view(), name="lgpd-delete"),
    path("audit-logs", AuditLogView.as_view(), name="audit-logs"),
]
