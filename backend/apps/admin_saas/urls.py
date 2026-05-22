from django.urls import path

from .views import SummaryView, TenantDetailView, TenantsListView

urlpatterns = [
    path("summary", SummaryView.as_view(), name="admin-saas-summary"),
    path("tenants", TenantsListView.as_view(), name="admin-saas-tenants"),
    path("tenants/<int:pk>", TenantDetailView.as_view(), name="admin-saas-tenant-detail"),
]
