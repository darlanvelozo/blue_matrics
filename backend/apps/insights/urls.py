from django.urls import path

from .views import DismissView, GenerateInsightsView, ListInsightsView, MarkReadView

urlpatterns = [
    path("", ListInsightsView.as_view(), name="insights-list"),
    path("generate", GenerateInsightsView.as_view(), name="insights-generate"),
    path("<int:pk>/read", MarkReadView.as_view(), name="insights-read"),
    path("<int:pk>/dismiss", DismissView.as_view(), name="insights-dismiss"),
]
