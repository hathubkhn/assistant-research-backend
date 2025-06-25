from django.urls import path, include
from django.views.generic import RedirectView
from . import views

public_patterns = [
    path('research-assistant/', views.research_assistant, name='public-research-assistant'),
    path('papers/', views.papers_list, name='public-papers-list'),
    path('papers/<uuid:paper_id>/', views.paper_detail, name='public-paper-detail'),
    path('papers/by-slug/<str:slug>/', views.paper_by_slug, name='public-paper-by-slug'),
    path('papers/by-venue/<str:venue_type>/', views.papers_by_venue_type, name='public-papers-by-venue-type'),
    path('papers/interesting/', views.interesting_papers, name='public-interesting-papers'),
    path('papers/downloaded/', views.downloaded_papers, name='public-downloaded-papers'),
    path('papers/mark-interesting/<uuid:paper_id>/', views.mark_paper_interesting, name='public-mark-paper-interesting'),
    path('papers/<uuid:paper_id>/unmark-interesting/', views.unmark_paper_interesting, name='public-unmark-paper-interesting'),
    path('papers/mark-downloaded/<uuid:paper_id>/', views.mark_paper_downloaded, name='public-mark-paper-downloaded'),
    path('papers/<uuid:paper_id>/unmark-downloaded/', views.unmark_paper_downloaded, name='public-unmark-paper-downloaded'),
    path('datasets/', views.datasets_list, name='public-datasets-list'),
    path('datasets/<uuid:dataset_id>/', views.dataset_detail, name='public-dataset-detail'),
    path('datasets/by-slug/<str:slug>/', views.dataset_by_slug, name='public-dataset-by-slug'),
    path('datasets/interesting/', views.interesting_datasets, name='public-interesting-datasets'),
    path('datasets/mark-interesting/<uuid:dataset_id>/', views.mark_dataset_interesting, name='public-mark-dataset-interesting'),
    path('datasets/<uuid:dataset_id>/unmark-interesting/', views.unmark_dataset_interesting, name='public-unmark-dataset-interesting'),
    path('datasets/<uuid:dataset_id>/add-similar/', views.add_similar_dataset, name='public-add-similar-dataset'),
    path('journals/', views.journals_list, name='public-journals-list'),
    path('journals/<uuid:journal_id>/', views.journal_detail, name='public-journal-detail'),
    path('journals/create/', views.create_journal, name='public-create-journal'),
    path('journals/<uuid:journal_id>/update/', views.update_journal, name='public-update-journal'),
    path('journals/filter/', views.filter_journals_list, name='public-filter-journals-list'),
    path('conferences/', views.conferences_list, name='public-conferences-list'),
    path('conferences/<uuid:conference_id>/', views.conference_detail, name='public-conference-detail'),
    path('conferences/create/', views.create_conference, name='public-create-conference'),
    path('conferences/<uuid:conference_id>/update/', views.update_conference, name='public-update-conference'),
    path('conferences/filter/', views.filter_conferences_list, name='public-filter-conferences-list'),
    path('conferences/debug/counts/', views.conference_counts_debug, name='public-conference-counts-debug'),
    path('venues/counts/', views.venues_counts, name='public-venues-counts'),
    path('search/', views.search, name='public-search'),
    path('profile', views.get_profile, name='public-get-profile'),
    path('profile/', views.get_profile, name='public-get-profile-with-slash'),
    path('profile/avatar/', views.update_avatar, name='public-update-avatar'),
    path('profile/update/', views.update_profile, name='public-update-profile'),
    path('publications/', views.publications_list, name='public-publications-list'),
    path('publications/create/', views.create_publication, name='public-create-publication'),
    path('publications/debug/', views.debug_publications, name='public-publications-debug'),
    path('publications/<uuid:publication_id>/', views.publication_detail, name='public-publication-detail'),
    path('stats/', views.stats, name='public-stats'),
    path('stats/dashboard/', views.dashboard_stats, name='public-dashboard-stats'),
    path('stats/papers/', views.papers_stats, name='public-papers-stats'),
    path('stats/keywords/', views.keywords_stats, name='public-keywords-stats'),
    path('stats/datasets/', views.datasets_stats, name='public-datasets-stats'),
    path('register/', views.register, name='public-register'),
    path('token-login/', views.token_login, name='public-token-login'),
    path('auth/google/callback', views.google_callback, name='public-google-callback'),
    path('login/', views.login_view, name='public-login-view'),
]

# Create redirects from /public/ paths to /api/ paths for each pattern
redirect_patterns = [
    # For each public pattern, create a redirect to the equivalent API endpoint
    path(pattern.pattern._route, 
         RedirectView.as_view(url=f'/api/{pattern.pattern._route}', permanent=True), 
         name=f'redirect-{pattern.name}')
    for pattern in public_patterns
]

# Keep public_patterns for backward compatibility, but add warning in log
urlpatterns = public_patterns + redirect_patterns 