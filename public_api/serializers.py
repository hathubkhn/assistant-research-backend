from rest_framework import serializers
from .models import Profile, Paper, Dataset, Publication, Journal, Conference

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Profile
        fields = ['id', 'username', 'email', 'full_name', 'faculty_institute', 'school', 
                 'position', 'google_scholar_link', 'bio', 'research_interests', 
                 'additional_keywords', 'avatar_url', 'is_profile_completed', 
                 'created_at', 'updated_at']

class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = '__all__'

class ConferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conference
        fields = '__all__'

class PaperSerializer(serializers.ModelSerializer):
    journal_details = JournalSerializer(source='journal', read_only=True)
    conference_details = ConferenceSerializer(source='conference_venue', read_only=True)
    venue_type = serializers.ReadOnlyField()
    venue_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Paper
        fields = '__all__'

class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = '__all__'

class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = '__all__'


### For papers apis
class PaperListSerializer(serializers.ModelSerializer):
    year = serializers.SerializerMethodField()
    downloadUrl = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()
    venueType = serializers.SerializerMethodField()
    venue = serializers.SerializerMethodField()
    impactFactor = serializers.SerializerMethodField()
    quartile = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()
    
    class Meta:
        model = Paper
        fields = ['id', 'title', 'authors', 'venue', 'venueType', 
                  'year', 'keywords', 'abstract', 'downloadUrl',
                  'impactFactor', 'quartile']

    def get_authors(self, obj):
        authors_list = obj.authors.values_list('name', flat=True)
        authors_list = list(authors_list)
        if len(authors_list) > 0:
            return authors_list
        else:
            return ["Unknown"]
    
    def get_downloadUrl(self, obj):
        return obj.pdf_url

    def get_year(self, obj):
        return obj.publication_date.year if obj.publication_date else None
    
    def get_venueType(self, obj):
        return obj.venue_type
    
    def get_venue(self, obj):
        return obj.venue_name

    def get_impactFactor(self, obj):
        if obj.venue_type == 'journal' and obj.journal:
            return obj.journal.impact_factor
        else:
            return None
    
    def get_quartile(self, obj):
        if obj.venue_type == 'journal' and obj.journal:
            return obj.journal.quartile
        else:
            return None
        
    def get_keywords(self, obj):
        if obj.keywords:
            return obj.keywords
        else:
            return []
        
class PaperDetailSerializer(PaperListSerializer):
    sourceCode = serializers.SerializerMethodField()
    citationsByYear = serializers.SerializerMethodField()
    conferenceRank = serializers.SerializerMethodField()
    conferenceAbbreviation = serializers.SerializerMethodField()
    
    class Meta:
        model = Paper
        fields = ['id', 'title', 'authors', 'venue', 'venueType', 
                  'year', 'keywords', 'abstract', 'downloadUrl',
                  'impactFactor', 'quartile', 'citationsByYear',
                  'doi', 'method', 'results', 'conclusions', 'bibtex', 
                  'sourceCode', 'conferenceRank', 'conferenceAbbreviation',
                  'datasets']
    
    def get_citationsByYear(self, obj):
        return obj.citations_count
    
    def get_datasets(self, obj):
        datasets = obj.datasets.all()
        datasets_list = []
        for dataset in datasets:
            datasets_list.append({
                "id": dataset.id,
                "name": dataset.name,
                "abbreviation": dataset.abbreviation,
                "description": dataset.description,
                "data_type": dataset.data_type,
                "category": dataset.tasks.all().values_list('name', flat=True),
                "size": dataset.size,
                "format": dataset.format,
                "source_url": dataset.source_url,
                "license": dataset.license,
            })
    
    def get_conferenceRank(self, obj):
        if obj.venue_type == 'conference' and obj.conference:
            return obj.conference.rank
        else:
            return None
    
    def get_conferenceAbbreviation(self, obj):
        if obj.venue_type == 'conference' and obj.conference:
            return obj.conference.abbreviation
        else:
            return None

    def get_sourceCode(self, obj):
        if obj.github_url:
            return obj.github_url
        else:
            return None