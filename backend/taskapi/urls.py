from django.urls import path
from .views import AnalyzeTasksView, SuggestTasksView, ResetTasksView, ListTasksView

urlpatterns = [
    path('analyze/', AnalyzeTasksView.as_view()),
    path('suggest/', SuggestTasksView.as_view()),
    path('reset/', ResetTasksView.as_view()),
    path('list/', ListTasksView.as_view()),
]
