from django.urls import path
from .views import AnalyzeTasksView, SuggestTasksView

urlpatterns = [
    path('analyze/', AnalyzeTasksView.as_view()),
    path('suggest/', SuggestTasksView.as_view()),
]
