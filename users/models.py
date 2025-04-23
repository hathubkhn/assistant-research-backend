from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=100, blank=True, null=True)
    faculty_institute = models.CharField(max_length=100, blank=True, null=True)
    school = models.CharField(max_length=100, blank=True, null=True)
    research_interests = models.TextField(blank=True, null=True)  # Main research interests
    additional_keywords = models.TextField(blank=True, null=True)  # Additional keywords
    position = models.CharField(max_length=100, blank=True, null=True)
    google_scholar_link = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    is_profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

class Paper(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='papers')
    title = models.CharField(max_length=500)
    authors = models.JSONField(default=list)  # Store as a list
    conference = models.CharField(max_length=255, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    field = models.CharField(max_length=255, blank=True, null=True)
    keywords = models.JSONField(default=list)  # Store as a list
    abstract = models.TextField(blank=True, null=True)
    doi = models.CharField(max_length=255, blank=True, null=True)
    bibtex = models.TextField(blank=True, null=True)  # BibTeX citation format
    sourceCode = models.URLField(max_length=500, blank=True, null=True)  # Repository URL
    is_interesting = models.BooleanField(default=False)
    is_downloaded = models.BooleanField(default=False)
    is_uploaded = models.BooleanField(default=True)  # Default to True for uploaded papers
    file = models.FileField(upload_to='papers/')
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.IntegerField(blank=True, null=True)  # Size in bytes
    added_date = models.DateTimeField(auto_now_add=True)
    
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

# New models for research papers from Prisma seed
class ResearchPaper(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=500)
    authors = models.JSONField(default=list)
    conference = models.CharField(max_length=255)
    year = models.IntegerField()
    field = models.CharField(max_length=255)
    keywords = models.JSONField(default=list)
    abstract = models.TextField()
    downloadUrl = models.URLField(max_length=500)
    doi = models.CharField(max_length=255, blank=True, null=True)
    method = models.TextField(blank=True, null=True)
    results = models.TextField(blank=True, null=True)
    conclusions = models.TextField(blank=True, null=True)
    bibtex = models.TextField(blank=True, null=True)
    sourceCode = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class Dataset(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=500)
    abbreviation = models.CharField(max_length=100)
    description = models.TextField()
    downloadUrl = models.URLField(max_length=500)
    paperCount = models.IntegerField()
    language = models.CharField(max_length=50)
    category = models.CharField(max_length=100)
    tasks = models.JSONField(default=list)
    thumbnailUrl = models.URLField(max_length=500, blank=True, null=True)
    benchmarks = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class DatasetReference(models.Model):
    paper = models.ForeignKey(ResearchPaper, on_delete=models.CASCADE, related_name='datasetRefs')
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='paperRefs')
    
    class Meta:
        unique_together = ('paper', 'dataset')
        
    def __str__(self):
        return f"{self.dataset.name} - {self.paper.title}"

class Publication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='publications')
    title = models.CharField(max_length=500)
    authors = models.TextField()
    journal = models.CharField(max_length=255)
    year = models.IntegerField()
    url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

    # Ensure Django uses the correct table name
    class Meta:
        db_table = 'users_publication'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
