from django.urls import path

from .views import (
    CommercialDashboardView,
    ExecutiveDashboardView,
    FinancialDashboardView,
    OverviewView,
)

urlpatterns = [
    # Visão geral premium (alimenta /app) — agrega KPIs v1+v2, score, cards
    path("overview", OverviewView.as_view(), name="dashboard-overview"),
    path("executive", ExecutiveDashboardView.as_view(), name="dashboard-executive"),
    path("financial", FinancialDashboardView.as_view(), name="dashboard-financial"),
    path("commercial", CommercialDashboardView.as_view(), name="dashboard-commercial"),
]
