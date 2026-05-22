from django.urls import path

from .views import GoalDetailView, GoalsListView

urlpatterns = [
    path("", GoalsListView.as_view(), name="goals-list"),
    path("<int:pk>", GoalDetailView.as_view(), name="goals-detail"),
]
