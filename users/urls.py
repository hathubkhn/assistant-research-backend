from django.urls import path, include
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token-login/', views.TokenLoginView.as_view(), name='token-login'),
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('', include('social_django.urls', namespace='social')),
    
    # SSO Callback Handling
    path('sso-callback/<str:provider>/', views.SSOCallbackView.as_view(), name='sso-callback'),
    path('auth/microsoft/callback', views.MicrosoftAuthCallbackView.as_view(), name='microsoft-callback'),
    path('auth/google/callback', views.GoogleAuthCallbackView.as_view(), name='google-callback'),
    path('sso-info/', views.SSOExplanationView.as_view(), name='sso-info'),
    
    # User profile URLs
    path('user/', views.UserView.as_view(), name='user'),
    path('user/profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    
    # Publications URL
    path('publications/', views.PublicationsView.as_view(), name='publications-list'),
    path('publications/<int:pk>/', views.PublicationDetailView.as_view(), name='publication-detail'),
    
    # Paper-related URLs
    path('papers/', views.UserPapersView.as_view(), name='papers-list'),
    path('papers/<int:pk>/', views.PaperDetailView.as_view(), name='paper-detail'),
    path('papers/upload/', views.PaperUploadView.as_view(), name='paper-upload'),
    
    # Research papers and datasets URLs
    path('research/papers/', views.ResearchPaperListView.as_view(), name='research-papers-list'),
    path('research/papers/<str:pk>/', views.ResearchPaperDetailView.as_view(), name='research-paper-detail'),
    path('research/datasets/', views.DatasetListView.as_view(), name='datasets-list'),
    path('research/datasets/<str:pk>/', views.DatasetDetailView.as_view(), name='dataset-detail'),
    path('research/datasets/<str:dataset_id>/papers/', views.DatasetPapersView.as_view(), name='dataset-papers'),
] 