from django.urls import path

from .ai_views import AnalyzeView, AskView
from .chat_views import ChatSessionDetailView, ChatSessionListView
from .views import DismissView, GenerateInsightsView, ListInsightsView, MarkReadView

urlpatterns = [
    path("", ListInsightsView.as_view(), name="insights-list"),
    path("generate", GenerateInsightsView.as_view(), name="insights-generate"),
    path("ask", AskView.as_view(), name="ai-ask"),
    path("analyze", AnalyzeView.as_view(), name="ai-analyze"),
    path("chats", ChatSessionListView.as_view(), name="ai-chats-list"),
    path("chats/<int:pk>", ChatSessionDetailView.as_view(), name="ai-chats-detail"),
    path("<int:pk>/read", MarkReadView.as_view(), name="insights-read"),
    path("<int:pk>/dismiss", DismissView.as_view(), name="insights-dismiss"),
]
