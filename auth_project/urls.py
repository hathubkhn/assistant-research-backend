"""
URL configuration for auth_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from public_api import views as public_api_views

# drf-yasg imports
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger schema view configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Research Assistant API",
        default_version='v1',
        description="API documentation for Research Assistant project\n\n"
                   "**Note**: SSO callback endpoints (e.g., /api/sso-callback/google/) are not testable "
                   "directly from Swagger UI as they are designed to receive redirects from OAuth providers.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[
        path('api/', include('users.urls')),
    ],
    url=getattr(settings, 'API_URL', 'http://localhost:8000'),
)

# API patterns from public_api
api_patterns = [
    path('test/', public_api_views.test_endpoint, name='api-test'),
    path('papers/', public_api_views.papers_list, name='api-papers-list'),
    path('papers/<uuid:paper_id>/', public_api_views.paper_detail, name='api-paper-detail'),
    path('papers/by-slug/<str:slug>/', public_api_views.paper_by_slug, name='api-paper-by-slug'),
    path('papers/by-venue/<str:venue_type>/', public_api_views.papers_by_venue_type, name='api-papers-by-venue-type'),
    path('papers/interesting/', public_api_views.interesting_papers, name='api-interesting-papers'),
    path('papers/downloaded/', public_api_views.downloaded_papers, name='api-downloaded-papers'),
    path('papers/by-keywords/', public_api_views.papers_by_keywords, name='api-papers-by-keywords'),
    path('papers/by-research-interests/', public_api_views.papers_by_keywords, name='api-papers-by-research-interests'),
    path('papers/mark-interesting/<uuid:paper_id>/', public_api_views.mark_paper_interesting, name='api-mark-paper-interesting'),
    path('papers/<uuid:paper_id>/unmark-interesting/', public_api_views.unmark_paper_interesting, name='api-unmark-paper-interesting'),
    path('papers/mark-downloaded/<uuid:paper_id>/', public_api_views.mark_paper_downloaded, name='api-mark-paper-downloaded'),
    path('papers/<uuid:paper_id>/unmark-downloaded/', public_api_views.unmark_paper_downloaded, name='api-unmark-paper-downloaded'),
    path('journals/', public_api_views.journals_list, name='api-journals-list'),
    path('journals/<uuid:journal_id>/', public_api_views.journal_detail, name='api-journal-detail'),
    path('journals/create/', public_api_views.create_journal, name='api-create-journal'),
    path('journals/<uuid:journal_id>/update/', public_api_views.update_journal, name='api-update-journal'),
    path('journals/filter/', public_api_views.filter_journals_list, name='api-filter-journals-list'),
    path('conferences/', public_api_views.conferences_list, name='api-conferences-list'),
    path('conferences/<uuid:conference_id>/', public_api_views.conference_detail, name='api-conference-detail'),
    path('conferences/create/', public_api_views.create_conference, name='api-create-conference'),
    path('conferences/<uuid:conference_id>/update/', public_api_views.update_conference, name='api-update-conference'),
    path('conferences/filter/', public_api_views.filter_conferences_list, name='api-filter-conferences-list'),
    path('conferences/debug/counts/', public_api_views.conference_counts_debug, name='api-conference-counts-debug'),
    path('venues/counts/', public_api_views.venues_counts, name='api-venues-counts'),
    path('datasets/', public_api_views.datasets_list, name='api-datasets-list'),
    path('datasets/<uuid:dataset_id>/', public_api_views.dataset_detail, name='api-dataset-detail'),
    path('datasets/by-slug/<str:slug>/', public_api_views.dataset_by_slug, name='api-dataset-by-slug'),
    path('datasets/interesting/', public_api_views.interesting_datasets, name='api-interesting-datasets'),
    path('datasets/mark-interesting/<uuid:dataset_id>/', public_api_views.mark_dataset_interesting, name='api-mark-dataset-interesting'),
    path('datasets/<uuid:dataset_id>/unmark-interesting/', public_api_views.unmark_dataset_interesting, name='api-unmark-dataset-interesting'),
    path('datasets/<uuid:dataset_id>/add-similar/', public_api_views.add_similar_dataset, name='api-add-similar-dataset'),
    path('search/', public_api_views.search, name='api-search'),
    path('profile', public_api_views.get_profile, name='api-get-profile'),
    path('profile/', public_api_views.get_profile, name='api-get-profile-with-slash'),
    path('profile/avatar/', public_api_views.update_avatar, name='api-update-avatar'),
    path('profile/update/', public_api_views.update_profile, name='api-update-profile'),
    path('publications/', public_api_views.publications_list, name='api-publications-list'),
    path('publications/create/', public_api_views.create_publication, name='api-create-publication'),
    path('publications/debug/', public_api_views.debug_publications, name='api-publications-debug'),
    path('publications/<uuid:publication_id>/', public_api_views.publication_detail, name='api-publication-detail'),
    path('stats/', public_api_views.stats, name='api-stats'),
    path('stats/home/', public_api_views.home_stats, name='api-home-stats'),
    path('stats/dashboard/', public_api_views.dashboard_stats, name='api-dashboard-stats'),
    path('stats/papers/', public_api_views.papers_stats, name='api-papers-stats'),
    path('stats/keywords/', public_api_views.keywords_stats, name='api-keywords-stats'),
    path('stats/research-interests/', public_api_views.research_interests_stats, name='api-research-interests-stats'),
    path('stats/all-keywords/', public_api_views.all_keywords, name='api-all-keywords'),
    path('stats/all-research-interests/', public_api_views.all_keywords, name='api-all-research-interests'),
    path('stats/datasets/', public_api_views.datasets_stats, name='api-datasets-stats'),
    path('seed/papers/', public_api_views.seed_papers, name='api-seed-papers'),
    path('keywords/', public_api_views.keywords, name='api-keywords'),
    path('research-interests/', public_api_views.keywords, name='api-research-interests'),
    path('keywords/sync/', public_api_views.sync_keywords, name='api-sync-keywords'),
    path('research-interests/sync/', public_api_views.sync_keywords, name='api-sync-research-interests'),
    path('register/', public_api_views.register, name='api-register'),
    path('token-login/', public_api_views.token_login, name='api-token-login'),
    path('auth/google/callback', public_api_views.google_callback, name='api-google-callback'),
    path('login/', public_api_views.login_view, name='api-login-view'),
    path('my-library/', public_api_views.my_library, name='api-my-library'),
]

urlpatterns = [
    # Redirect root URL to API login
    path('', RedirectView.as_view(url='/public/login/'), name='home'),
    
    path('admin/', admin.site.urls),
    path('api/', include(api_patterns)),  # Added API patterns from public_api - now first
    path('api/', include('users.urls')),  # Now second
    path('public/', include('public_api.urls')),  # Public API URLs
    
    # Django AllAuth URLs
    path('accounts/', include('allauth.urls')),
    
    # Add explicit SSO URLs
    path('accounts/google/login/', include('allauth.socialaccount.providers.google.urls')),
    path('accounts/microsoft/login/', include('allauth.socialaccount.providers.microsoft.urls')),
    
    # Swagger documentation URLs
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
