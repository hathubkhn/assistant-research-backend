from django.db import models
from django.contrib.auth.models import User
import uuid

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='public_profile')
    full_name = models.CharField(max_length=255, blank=True)
    faculty_institute = models.CharField(max_length=255, blank=True)
    school = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True)
    google_scholar_link = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    research_interests = models.TextField(blank=True, null=True)
    additional_keywords = models.TextField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    is_profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Journal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=50, blank=True)
    impact_factor = models.FloatField(null=True, blank=True)
    quartile = models.CharField(max_length=10, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Conference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=50, blank=True)
    rank = models.CharField(max_length=10, blank=True)  # A*, A, B, C or similar
    location = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Paper(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    authors = models.JSONField(default=list)
    abstract = models.TextField()
    conference = models.CharField(max_length=255, blank=True)
    journal = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    conference_venue = models.ForeignKey(Conference, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    year = models.IntegerField()
    field = models.CharField(max_length=100, blank=True)
    keywords = models.JSONField(default=list)
    downloadUrl = models.URLField(blank=True)
    doi = models.CharField(max_length=100, blank=True)
    method = models.TextField(blank=True)
    results = models.TextField(blank=True)
    conclusions = models.TextField(blank=True)
    bibtex = models.TextField(blank=True)
    sourceCode = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def venue_type(self):
        if self.journal is not None:
            return "journal"
        elif self.conference_venue is not None:
            return "conference"
        # Fallback for legacy data
        elif self.conference in Journal.objects.values_list('name', flat=True):
            return "journal"
        else:
            return "conference"
            
    @property
    def venue_name(self):
        if self.journal is not None:
            return self.journal.name
        elif self.conference_venue is not None:
            return self.conference_venue.name
        else:
            return self.conference

    def __str__(self):
        return self.title

class PaperCitation(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='citations')
    year = models.IntegerField()
    count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('paper', 'year')
        
    def __str__(self):
        return f"{self.paper.title} - {self.year}: {self.count} citations"

class Dataset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    data_type = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=50, blank=True)
    format = models.CharField(max_length=50, blank=True)
    source_url = models.URLField(blank=True)
    license = models.CharField(max_length=100, blank=True)
    citation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    papers = models.ManyToManyField(Paper, related_name='datasets', blank=True)
    similar_datasets = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='related_to')

    def __str__(self):
        return self.name

class Publication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='public_publications')
    title = models.CharField(max_length=500)
    authors = models.TextField()  # Stored as JSON string
    abstract = models.TextField(blank=True)
    venue = models.CharField(max_length=255, blank=True)
    year = models.IntegerField()
    url = models.URLField(blank=True)
    doi = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class InterestingPaper(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='public_interesting_papers')
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='interested_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'paper')

    def __str__(self):
        return f"{self.user.username} - {self.paper.title}"

class DownloadedPaper(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='public_downloaded_papers')
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='downloaded_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'paper')

    def __str__(self):
        return f"{self.user.username} - {self.paper.title}"

class InterestingDataset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='public_interesting_datasets')
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='interested_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'dataset')

    def __str__(self):
        return f"{self.user.username} - {self.dataset.name}"
