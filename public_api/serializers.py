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