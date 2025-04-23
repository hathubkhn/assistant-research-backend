from django.contrib import admin
from .models import UserProfile, Paper, ResearchPaper, Dataset, DatasetReference, Publication, PaperCitation

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'faculty_institute', 'school', 'is_profile_completed')
    search_fields = ('user__username', 'full_name', 'faculty_institute')

@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'conference', 'year', 'field', 'added_date')
    search_fields = ('title', 'abstract', 'user__username')
    list_filter = ('year', 'field', 'is_interesting', 'is_downloaded')

@admin.register(ResearchPaper)
class ResearchPaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'conference', 'year', 'field')
    search_fields = ('title', 'abstract', 'authors')
    list_filter = ('year', 'field', 'conference')

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'category', 'language', 'paperCount', 'benchmarks')
    search_fields = ('name', 'description', 'category')
    list_filter = ('category', 'language')

@admin.register(DatasetReference)
class DatasetReferenceAdmin(admin.ModelAdmin):
    list_display = ('paper', 'dataset')
    search_fields = ('paper__title', 'dataset__name')

@admin.register(PaperCitation)
class PaperCitationAdmin(admin.ModelAdmin):
    list_display = ('paper', 'year', 'count')
    list_filter = ('year',)
    search_fields = ('paper__title',)
