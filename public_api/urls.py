from django.urls import path
from .views import PapersList

public_patterns = [
    path('papers/', PapersList.as_view(), name='public-papers-list'),
]

urlpatterns = public_patterns