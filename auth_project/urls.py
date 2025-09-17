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
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static



# # API patterns from public_api
# api_patterns = [
#     path(route='', view=include('public_api.urls')),
#     path('research-assistant/query/', public_api_views.research_assistant, name='api-research-assistant-query'),    
#     path('papers/<uuid:paper_id>/', public_api_views.paper_detail, name='api-paper-detail'),
#     path('papers/by-slug/<str:slug>/', public_api_views.paper_by_slug, name='api-paper-by-slug'),
#     path('papers/by-venue/<str:venue_type>/', public_api_views.papers_by_venue_type, name='api-papers-by-venue-type'),
#     path('papers/interesting/', public_api_views.interesting_papers, name='api-interesting-papers'),
#     path('papers/downloaded/', public_api_views.downloaded_papers, name='api-downloaded-papers'),
#     path('papers/by-keywords/', public_api_views.papers_by_keywords, name='api-papers-by-keywords'),
#     path('papers/by-research-interests/', public_api_views.papers_by_keywords, name='api-papers-by-research-interests'),
#     path('papers/mark-interesting/<uuid:paper_id>/', public_api_views.mark_paper_interesting, name='api-mark-paper-interesting'),
#     path('papers/<uuid:paper_id>/unmark-interesting/', public_api_views.unmark_paper_interesting, name='api-unmark-paper-interesting'),
#     path('papers/mark-downloaded/<uuid:paper_id>/', public_api_views.mark_paper_downloaded, name='api-mark-paper-downloaded'),
#     path('papers/<uuid:paper_id>/unmark-downloaded/', public_api_views.unmark_paper_downloaded, name='api-unmark-paper-downloaded'),
#     path('papers/upload/', public_api_views.upload_paper, name='api-paper-upload'),
    
#     path('journals/', public_api_views.journals_list, name='api-journals-list'),
#     path('journals/<uuid:journal_id>/', public_api_views.journal_detail, name='api-journal-detail'),
#     path('journals/create/', public_api_views.create_journal, name='api-create-journal'),
#     path('journals/<uuid:journal_id>/update/', public_api_views.update_journal, name='api-update-journal'),
#     path('journals/filter/', public_api_views.filter_journals_list, name='api-filter-journals-list'),
    
#     path('conferences/', public_api_views.conferences_list, name='api-conferences-list'),
#     path('conferences/<uuid:conference_id>/', public_api_views.conference_detail, name='api-conference-detail'),
#     path('conferences/create/', public_api_views.create_conference, name='api-create-conference'),
#     path('conferences/<uuid:conference_id>/update/', public_api_views.update_conference, name='api-update-conference'),
#     path('conferences/filter/', public_api_views.filter_conferences_list, name='api-filter-conferences-list'),
#     path('conferences/debug/counts/', public_api_views.conference_counts_debug, name='api-conference-counts-debug'),
    
#     path('venues/counts/', public_api_views.venues_counts, name='api-venues-counts'),
    
#     path('datasets/<uuid:dataset_id>/', public_api_views.dataset_detail, name='api-dataset-detail'),
#     path('datasets/by-slug/<str:slug>/', public_api_views.dataset_by_slug, name='api-dataset-by-slug'),
#     path('datasets/interesting/', public_api_views.interesting_datasets, name='api-interesting-datasets'),
#     path('datasets/mark-interesting/<uuid:dataset_id>/', public_api_views.mark_dataset_interesting, name='api-mark-dataset-interesting'),
#     path('datasets/<uuid:dataset_id>/unmark-interesting/', public_api_views.unmark_dataset_interesting, name='api-unmark-dataset-interesting'),
#     path('datasets/<uuid:dataset_id>/add-similar/', public_api_views.add_similar_dataset, name='api-add-similar-dataset'),
    
#     path('search/', public_api_views.search, name='api-search'),
    
#     path('profile', public_api_views.get_profile, name='api-get-profile'),
#     path('profile/', public_api_views.get_profile, name='api-get-profile-with-slash'),
#     path('profile/avatar/', public_api_views.update_avatar, name='api-update-avatar'),
#     path('profile/update/', public_api_views.update_profile, name='api-update-profile'),
    
#     path('publications/', public_api_views.publications_list, name='api-publications-list'),
#     path('publications/<uuid:publication_id>/', public_api_views.publication_detail, name='api-publication-detail'),
    
#     path('register/', public_api_views.register, name='api-register'),
#     path('token-login/', public_api_views.token_login, name='api-token-login'),
#     path('auth/google/callback', public_api_views.google_callback, name='api-google-callback'),
#     path('auth/microsoft/callback', public_api_views.microsoft_callback, name='api-microsoft-callback'),
#     path('login/', public_api_views.login_view, name='api-login-view'),
#     path('my-library/', public_api_views.my_library, name='api-my-library'),
# ]


urlpatterns = [
    path('', RedirectView.as_view(url='/api/login/'), name='home'),
    path('api/', include('public_api.urls')),
    path('accounts/', include('allauth.urls')),
    path('accounts/google/login/', include('allauth.socialaccount.providers.google.urls')),
    path('accounts/microsoft/login/', include('allauth.socialaccount.providers.microsoft.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
