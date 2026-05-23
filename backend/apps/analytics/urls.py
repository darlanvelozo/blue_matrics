from django.urls import path

from .views import (
    CommercialDashboardView,
    ExecutiveDashboardView,
    FinancialDashboardView,
    OverviewView,
    PredictiveDashboardView,
)

urlpatterns = [
    path("overview", OverviewView.as_view(), name="dashboard-overview"),
    path("executive", ExecutiveDashboardView.as_view(), name="dashboard-executive"),
    path("financial", FinancialDashboardView.as_view(), name="dashboard-financial"),
    path("commercial", CommercialDashboardView.as_view(), name="dashboard-commercial"),
    path("predictive", PredictiveDashboardView.as_view(), name="dashboard-predictive"),
]
