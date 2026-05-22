from django.urls import path

from .views import (
    CustomersListView,
    FilterOptionsView,
    FinancialListView,
    ProductsListView,
    SaleDetailView,
    SalesListView,
)

urlpatterns = [
    path("customers", CustomersListView.as_view(), name="explorer-customers"),
    path("products", ProductsListView.as_view(), name="explorer-products"),
    path("sales", SalesListView.as_view(), name="explorer-sales"),
    path("sales/<int:pk>", SaleDetailView.as_view(), name="explorer-sale-detail"),
    path("financial", FinancialListView.as_view(), name="explorer-financial"),
    path("filter-options", FilterOptionsView.as_view(), name="explorer-filter-options"),
]
