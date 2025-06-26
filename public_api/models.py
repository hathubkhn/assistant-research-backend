from django.db import models
from django.contrib.auth.models import User
import uuid
from django.conf import settings
from django.utils import timezone

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

    class Meta:
        db_table = "user_profile"

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

    class Meta:
        db_table = "journal"

class Conference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=50, blank=True)
    rank = models.CharField(max_length=10, blank=True)  # A*, A, B, C or similar
    location = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conference"

class Paper(models.Model):
    FILE_FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'DOCX'),
        ('doc', 'DOC'),
        ('txt', 'TXT'),
        ('html', 'HTML'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    doi = models.CharField(max_length=200, null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)

    journal = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    conference = models.ForeignKey(Conference, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')

    file_format = models.CharField(max_length=20, choices=FILE_FORMAT_CHOICES, default='pdf')
    pdf_file = models.FileField(upload_to=settings.PAPER_PDF_DIR, null=True, blank=True)
    
    url = models.URLField(max_length=200)
    pdf_url = models.URLField(max_length=200)
    github_url = models.URLField(max_length=200, null=True, blank=True)
    crawled_at = models.DateTimeField(default=timezone.now)
    
    keywords = models.JSONField(default=list)

    method = models.TextField(blank=True)
    results = models.TextField(blank=True)
    conclusions = models.TextField(blank=True)
    bibtex = models.TextField(blank=True)

    download_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    citations_count = models.IntegerField(default=0)
    references = models.ManyToManyField('self', symmetrical=False, related_name='referenced_papers')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'papers'
        indexes = [
            models.Index(fields=['-publication_date']),
            models.Index(fields=['title'])
        ]

    @property
    def venue_type(self):
        if self.journal is not None:
            return "journal"
        elif self.conference is not None:
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
        elif self.conference is not None:
            return self.conference.name
        else:
            return self.conference

class Author(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    affiliation = models.CharField(max_length=200)
    bio = models.TextField()
    google_scholar_url = models.URLField(max_length=200)
    papers = models.ManyToManyField(Paper, related_name='authors')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'authors'

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
    # New fields from JSON
    link = models.URLField(blank=True)
    subtitle = models.TextField(blank=True)
    paper_link = models.URLField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    language = models.CharField(max_length=100, blank=True)
    abbreviation = models.CharField(max_length=100, blank=True)
    paper_count = models.IntegerField(null=True, blank=True)
    benchmarks = models.JSONField(default=list, blank=True, null=True)
    dataloaders = models.JSONField(default=list, blank=True, null=True)
    dataset_papers = models.JSONField(default=list, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    papers = models.ManyToManyField(Paper, related_name='datasets', blank=True)
    similar_datasets = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='related_to')

    def __str__(self):
        return self.name

class Task(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    datasets = models.ManyToManyField(Dataset, related_name='tasks')
    papers = models.ManyToManyField(Paper, related_name='tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'

class DatasetSimilarDataset(models.Model):
    from_dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='similar_dataset_relations')
    to_dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='related_by_dataset_relations')
    
    class Meta:
        db_table = 'dataset_similar_datasets'
        unique_together = ('from_dataset', 'to_dataset')
        
    def __str__(self):
        return f"{self.from_dataset.name} -> {self.to_dataset.name}"

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
