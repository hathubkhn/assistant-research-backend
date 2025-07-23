from django.urls import path
from .views import PapersList, DatasetsList, TasksList, Dashboard
from .views.dashboard import TaskPaperAnalytics

public_patterns = [
    path('papers/', PapersList.as_view(), name='public-papers-list'),
    path('datasets/', DatasetsList.as_view(), name='public-datasets-list'),
    path('tasks/', TasksList.as_view(), name='public-tasks-list'),
    path('dashboard/', Dashboard.as_view(), name='public-dashboard'),
    path('task-paper-analytics/', TaskPaperAnalytics.as_view(), name='task-paper-analytics'),
]

urlpatterns = public_patterns