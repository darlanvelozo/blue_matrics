from django.urls import path

from .views import (
    CommercialDashboardView,
    CustomersAnalyticsView,
    ExecutiveDashboardView,
    FinancialDashboardView,
    OverviewView,
    PredictiveDashboardView,
    ProductsAnalyticsView,
)

urlpatterns = [
    path("overview", OverviewView.as_view(), name="dashboard-overview"),
    path("executive", ExecutiveDashboardView.as_view(), name="dashboard-executive"),
    path("financial", FinancialDashboardView.as_view(), name="dashboard-financial"),
    path("commercial", CommercialDashboardView.as_view(), name="dashboard-commercial"),
    path("predictive", PredictiveDashboardView.as_view(), name="dashboard-predictive"),
    # Analíticos (RFV, ABC, parados, reorder)
    path("analytics/customers", CustomersAnalyticsView.as_view(), name="analytics-customers"),
    path("analytics/products", ProductsAnalyticsView.as_view(), name="analytics-products"),
]
