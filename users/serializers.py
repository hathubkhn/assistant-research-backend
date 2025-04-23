from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Paper, ResearchPaper, Dataset, DatasetReference, Publication, PaperCitation

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    
    Provides basic user information with read-only access to ID, username, and email.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email']

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    Handles creating new users with profile information.
    Passwords are write-only and not returned in responses.
    """
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True, required=False)
    full_name = serializers.CharField(required=False)
    faculty_institute = serializers.CharField(required=False)
    school = serializers.CharField(required=False)
    research_interests = serializers.CharField(required=False)
    additional_keywords = serializers.CharField(required=False)
    position = serializers.CharField(required=False)
    google_scholar_link = serializers.URLField(required=False)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'password2', 
                  'full_name', 'faculty_institute', 'school', 'research_interests', 'additional_keywords',
                  'position', 'google_scholar_link']
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
        
    def validate(self, data):
        # Check if password2 is provided, and if so, validate it matches password
        if 'password2' in data and data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Passwords don't match"})
        return data
    
    def create(self, validated_data):
        # Extract profile data
        profile_data = {}
        for field in ['full_name', 'faculty_institute', 'school', 'research_interests', 'additional_keywords', 'position', 'google_scholar_link']:
            if field in validated_data:
                profile_data[field] = validated_data.pop(field)
        
        print(f"Profile data extracted: {profile_data}")
        
        # Remove password2 if it exists
        validated_data.pop('password2', None)
        
        # Create the user
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        print(f"User created: {user.username}, {user.email}, ID: {user.id}")
        
        # Update the profile
        if profile_data:
            profile = user.profile
            for key, value in profile_data.items():
                print(f"Setting profile field {key} = {value}")
                setattr(profile, key, value)
            
            # Check if profile is complete
            required_fields = ['full_name', 'faculty_institute', 'school', 'research_interests', 'position']
            fields_values = {field: getattr(profile, field) for field in required_fields}
            print(f"Required fields values: {fields_values}")
            
            is_completed = all(getattr(profile, field) for field in required_fields)
            profile.is_profile_completed = is_completed
            
            print(f"Profile is_completed: {is_completed}")
            profile.save()
            print(f"Profile saved, ID: {profile.id}")
        
        # Force save to auth_db as well (in case router isn't handling it properly)
        from django.db import connections
        cursor = connections['auth_db'].cursor()
        try:
            # Check if user exists in auth_db
            cursor.execute("SELECT id FROM auth_user WHERE username = %s", [user.username])
            if not cursor.fetchone():
                # Insert user in auth_db if not exists
                cursor.execute(
                    """
                    INSERT INTO auth_user 
                    (password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    [
                        user.password, user.last_login, user.is_superuser, user.username, 
                        user.first_name, user.last_name, user.email, user.is_staff, 
                        user.is_active, user.date_joined
                    ]
                )
                user_id_in_auth_db = cursor.fetchone()[0]
                
                # Insert profile in auth_db
                if user_id_in_auth_db:
                    cursor.execute(
                        """
                        INSERT INTO users_userprofile
                        (user_id, full_name, faculty_institute, school, research_interests, additional_keywords, position, 
                        google_scholar_link, is_profile_completed, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            user_id_in_auth_db, profile.full_name, profile.faculty_institute, 
                            profile.school, profile.research_interests, profile.additional_keywords, profile.position, 
                            profile.google_scholar_link, profile.is_profile_completed,
                            profile.created_at, profile.updated_at
                        ]
                    )
                    print(f"User and profile also saved to auth_db")
            
            connections['auth_db'].commit()
        except Exception as e:
            print(f"Error saving to auth_db: {e}")
            connections['auth_db'].rollback()
        finally:
            cursor.close()
        
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile.
    
    Provides access to the user profile information.
    Includes the associated user data as read-only.
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'full_name', 'faculty_institute', 'school', 'research_interests', 
                  'additional_keywords', 'position', 'google_scholar_link', 'bio', 'avatar_url', 'is_profile_completed']
        read_only_fields = ['id', 'user', 'is_profile_completed']
    
    def update(self, instance, validated_data):
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.faculty_institute = validated_data.get('faculty_institute', instance.faculty_institute)
        instance.school = validated_data.get('school', instance.school)
        instance.research_interests = validated_data.get('research_interests', instance.research_interests)
        instance.additional_keywords = validated_data.get('additional_keywords', instance.additional_keywords)
        instance.position = validated_data.get('position', instance.position)
        instance.google_scholar_link = validated_data.get('google_scholar_link', instance.google_scholar_link)
        instance.bio = validated_data.get('bio', instance.bio)
        instance.avatar_url = validated_data.get('avatar_url', instance.avatar_url)
        
        # Check if all required fields are filled
        required_fields = ['full_name', 'faculty_institute', 'school', 'research_interests', 'position']
        is_completed = all(getattr(instance, field) for field in required_fields)
        instance.is_profile_completed = is_completed
        
        instance.save()
        return instance

class PaperSerializer(serializers.ModelSerializer):
    """
    Serializer for Paper model.
    
    Handles paper uploads and metadata.
    File field is write-only and not returned in responses.
    Most fields are read-only after creation.
    """
    file = serializers.FileField(write_only=True)
    citations_by_year = serializers.SerializerMethodField()
    
    class Meta:
        model = Paper
        fields = ['id', 'title', 'authors', 'conference', 'year', 'field', 
                  'keywords', 'abstract', 'doi', 'bibtex', 'sourceCode', 'is_interesting', 'is_downloaded',
                  'is_uploaded', 'file', 'file_name', 'file_size', 'added_date', 'citations_by_year']
        read_only_fields = ['id', 'title', 'authors', 'conference', 'year', 'field',
                          'keywords', 'abstract', 'doi', 'bibtex', 'sourceCode', 'is_uploaded', 'file_name',
                          'file_size', 'added_date', 'citations_by_year']
    
    def get_citations_by_year(self, obj):
        """
        Return a list of citation data by year for this paper
        """
        return list(obj.citations.all().values('year', 'count'))
    
    def create(self, validated_data):
        # File is handled in the view
        return Paper.objects.create(**validated_data)

class DatasetSerializer(serializers.ModelSerializer):
    """
    Serializer for Dataset model.
    
    Provides complete dataset information.
    """
    class Meta:
        model = Dataset
        fields = ['id', 'name', 'abbreviation', 'description', 'downloadUrl', 
                 'paperCount', 'language', 'category', 'tasks', 'thumbnailUrl', 
                 'benchmarks', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class ResearchPaperSerializer(serializers.ModelSerializer):
    """
    Serializer for ResearchPaper model.
    
    Provides complete research paper information with nested dataset references.
    """
    datasets = serializers.SerializerMethodField()
    
    class Meta:
        model = ResearchPaper
        fields = ['id', 'title', 'authors', 'conference', 'year', 'field', 
                 'keywords', 'abstract', 'downloadUrl', 'doi', 'method', 
                 'results', 'conclusions', 'bibtex', 'sourceCode', 
                 'datasets', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_datasets(self, obj):
        # Get all datasets associated with this paper
        dataset_refs = DatasetReference.objects.filter(paper=obj)
        datasets = [ref.dataset for ref in dataset_refs]
        return DatasetSerializer(datasets, many=True).data

class DatasetReferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for DatasetReference model.
    
    Provides the relationship between papers and datasets.
    """
    class Meta:
        model = DatasetReference
        fields = ['id', 'paper', 'dataset']

class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = ['id', 'title', 'authors', 'journal', 'year', 'url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at'] 