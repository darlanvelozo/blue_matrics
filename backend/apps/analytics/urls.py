from django.urls import path

from .views import CommercialDashboardView, ExecutiveDashboardView, FinancialDashboardView

urlpatterns = [
    path("executive", ExecutiveDashboardView.as_view(), name="dashboard-executive"),
    path("financial", FinancialDashboardView.as_view(), name="dashboard-financial"),
    path("commercial", CommercialDashboardView.as_view(), name="dashboard-commercial"),
]
