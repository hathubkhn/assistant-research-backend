from django.urls import path

# Import views from organized view modules
from .views.dashboard import Dashboard, TaskPaperAnalytics
from .views.paper import (
    PapersList,
    PaperDetailView,
    PaperBySlugView,
    StarPaperView,
    UnstarPaperView,
    ListDownloadedPapers,
    MarkPaperDownloaded,
    UnmarkPaperDownloaded,
)
from .views.dataset import (
    DatasetsList,
    DatasetDetail,
    InterestingDatasets,
    MarkDatasetInteresting,
    UnmarkDatasetInteresting,
)
from .views.journal import JournalsList, JournalDetailView
from .views.conference import ConferencesList, ConferenceDetail
from .views.keywords import ListKeywordsView, TasksList
from .views.general import (
    SearchView,
    GetProfile,
    UpdateProfile,
    PublicationsList,
    PublicationDetail,
    Stats,
    DashboardStats,
    PapersStats,
    KeywordsStats,
    DatasetsStats,
    Register,
    TokenLogin,
    GoogleCallback,
    MicrosoftCallback,
    LoginView,
    UpdateAvatar,
    VenuesCounts,
    HomeStats,
    MyLibrary,
    UploadPaper,
    ResearchAssistant,
)

urlpatterns = [
    path("dashboard/", Dashboard.as_view(), name="public-dashboard"),
    path("task-paper-analytics/", TaskPaperAnalytics.as_view(), name="task-paper-analytics"),
    
    path('search/', SearchView.as_view(), name='api-search'),
    
    path("papers/", PapersList.as_view(), name="public-papers-list"),
    path('papers/<uuid:paper_id>/', PaperDetailView.as_view(), name='api-paper-detail'),
    path('papers/by-slug/<str:slug>/', PaperBySlugView.as_view(), name='api-paper-by-slug'),
    path('papers/downloaded/', ListDownloadedPapers.as_view(), name='api-downloaded-papers'),
    path('papers/mark-interesting/<uuid:paper_id>/', StarPaperView.as_view(), name='api-mark-paper-interesting'),
    path('papers/<uuid:paper_id>/unmark-interesting/', UnstarPaperView.as_view(), name='api-unmark-paper-interesting'),
    path('papers/mark-downloaded/<uuid:paper_id>/', MarkPaperDownloaded.as_view(), name='api-mark-paper-downloaded'),
    path('papers/<uuid:paper_id>/unmark-downloaded/', UnmarkPaperDownloaded.as_view(), name='api-unmark-paper-downloaded'),
    path('papers/upload/', UploadPaper.as_view(), name='api-upload-paper'),
    
    path("datasets/", DatasetsList.as_view(), name="public-datasets-list"),
    path('datasets/<uuid:dataset_id>/', DatasetDetail.as_view(), name='api-dataset-detail'),
    path('datasets/interesting/', InterestingDatasets.as_view(), name='api-interesting-datasets'),
    path('datasets/mark-interesting/<uuid:dataset_id>/', MarkDatasetInteresting.as_view(), name='api-mark-dataset-interesting'),
    path('datasets/<uuid:dataset_id>/unmark-interesting/', UnmarkDatasetInteresting.as_view(), name='api-unmark-dataset-interesting'),
    
    path("journals/", JournalsList.as_view(), name="api-journals-list"),
    path("journals/<uuid:journal_id>/", JournalDetailView.as_view(), name="api-journal-detail"),
    
    path("conferences/", ConferencesList.as_view(), name="api-conferences-list"),
    path("conferences/<uuid:conference_id>/", ConferenceDetail.as_view(), name="api-conference-detail"),
    
    path("keywords/", ListKeywordsView.as_view(), name="api-keywords-list"),
    path("tasks/", TasksList.as_view(), name="public-tasks-list"),
    
    path('profile/', GetProfile.as_view(), name='api-get-profile'),
    path('profile/update/', UpdateProfile.as_view(), name='api-update-profile'),
    path('profile/avatar/', UpdateAvatar.as_view(), name='api-update-avatar'),
    
    path('publications/', PublicationsList.as_view(), name='api-publications-list'),
    path('publications/<uuid:publication_id>/', PublicationDetail.as_view(), name='api-publication-detail'),
    
    path('register/', Register.as_view(), name='api-register'),
    path('token-login/', TokenLogin.as_view(), name='api-token-login'),
    path('auth/google/callback/', GoogleCallback.as_view(), name='api-google-callback'),
    path('auth/microsoft/callback/', MicrosoftCallback.as_view(), name='api-microsoft-callback'),
    path('login/', LoginView.as_view(), name='api-login-view'),
    
    # Statistics
    path('stats/', Stats.as_view(), name='api-stats'),
    path('stats/dashboard/', DashboardStats.as_view(), name='api-dashboard-stats'),
    path('stats/papers/', PapersStats.as_view(), name='api-papers-stats'),
    path('stats/keywords/', KeywordsStats.as_view(), name='api-keywords-stats'),
    path('stats/datasets/', DatasetsStats.as_view(), name='api-datasets-stats'),
    path('stats/home/', HomeStats.as_view(), name='api-home-stats'),
    
    path('venues/counts/', VenuesCounts.as_view(), name='api-venues-counts'),
    path('my-library/', MyLibrary.as_view(), name='api-my-library'),
    path('research-assistant/query/', ResearchAssistant.as_view(), name='api-research-assistant-query'),
]
