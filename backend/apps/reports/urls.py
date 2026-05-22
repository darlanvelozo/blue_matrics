from django.urls import path

from .views import ExportView, PublicShareView, ShareDetailView, SharesListView

# Endpoints de API (autenticados) — registrados em /api/reports/
api_urlpatterns = [
    path("export/<str:dashboard>/<str:fmt>", ExportView.as_view(), name="reports-export"),
    path("shares", SharesListView.as_view(), name="reports-shares"),
    path("shares/<int:pk>", ShareDetailView.as_view(), name="reports-share-detail"),
]

# Endpoint público — registrado em /r/
public_urlpatterns = [
    path("<str:token>", PublicShareView.as_view(), name="reports-public-share"),
]
