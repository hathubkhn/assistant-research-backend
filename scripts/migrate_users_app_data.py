#!/usr/bin/env python
"""
Script to migrate data from the users app to the public_api app.
"""
import os
import sys
import uuid
import django
from django.db import connection, transaction
from django.contrib.auth.models import User

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
django.setup()

from public_api.models import Profile, Paper, Publication, Dataset

def migrate_profiles():
    """Migrate UserProfile data to Profile"""
    print("Migrating user profiles...")
    
    with connection.cursor() as cursor:
        # Get count of userprofiles
        cursor.execute("SELECT COUNT(*) FROM users_userprofile")
        count = cursor.fetchone()[0]
        print(f"Found {count} user profiles to migrate")
        
        # Get all users with userprofiles
        cursor.execute("""
            SELECT 
                u.id, p.full_name, p.faculty_institute, p.research_interests, 
                p.position, p.google_scholar_link, p.is_profile_completed,
                p.school, p.bio, p.avatar_url, p.additional_keywords
            FROM auth_user u
            JOIN users_userprofile p ON u.id = p.user_id
        """)
        
        migrated = 0
        for row in cursor.fetchall():
            user_id, full_name, faculty_institute, research_interests, position, \
                google_scholar_link, is_profile_completed, school, bio, avatar_url, additional_keywords = row
            
            try:
                user = User.objects.get(id=user_id)
                profile, created = Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        'full_name': full_name or '',
                        'faculty_institute': faculty_institute or '',
                        'research_interests': research_interests or '',
                        'position': position or '',
                        'google_scholar_link': google_scholar_link or None,
                        'is_profile_completed': is_profile_completed,
                        'school': school or None,
                        'bio': bio or None,
                        'avatar_url': avatar_url or None,
                        'additional_keywords': additional_keywords or None
                    }
                )
                
                if not created:
                    # Update fields
                    profile.full_name = full_name or profile.full_name
                    profile.faculty_institute = faculty_institute or profile.faculty_institute
                    profile.research_interests = research_interests or profile.research_interests
                    profile.position = position or profile.position
                    profile.google_scholar_link = google_scholar_link or profile.google_scholar_link
                    profile.is_profile_completed = is_profile_completed
                    profile.school = school or profile.school
                    profile.bio = bio or profile.bio
                    profile.avatar_url = avatar_url or profile.avatar_url
                    profile.additional_keywords = additional_keywords or profile.additional_keywords
                    profile.save()
                
                migrated += 1
                print(f"Migrated profile for user {user.username}")
            except User.DoesNotExist:
                print(f"User with ID {user_id} does not exist, skipping profile")
        
        print(f"Migrated {migrated} profiles")

def migrate_research_papers():
    """Migrate ResearchPaper data to Paper"""
    print("Migrating research papers...")
    
    with connection.cursor() as cursor:
        # Get count of research papers
        cursor.execute("SELECT COUNT(*) FROM users_researchpaper")
        count = cursor.fetchone()[0]
        print(f"Found {count} research papers to migrate")
        
        # Get all research papers
        cursor.execute("""
            SELECT 
                id, title, authors, abstract, conference, year, field, 
                keywords, downloadUrl, doi, method, results, conclusions, 
                bibtex, sourceCode, created_at, updated_at
            FROM users_researchpaper
        """)
        
        migrated = 0
        for row in cursor.fetchall():
            id, title, authors, abstract, conference, year, field, \
                keywords, downloadUrl, doi, method, results, conclusions, \
                bibtex, sourceCode, created_at, updated_at = row
            
            # Check if paper with same title exists
            if not Paper.objects.filter(title=title).exists():
                try:
                    paper = Paper.objects.create(
                        id=uuid.uuid4(),  # Generate new UUID
                        title=title or '',
                        authors=authors or [],
                        abstract=abstract or '',
                        conference=conference or '',
                        year=year or 0,
                        field=field or '',
                        keywords=keywords or [],
                        downloadUrl=downloadUrl or '',
                        doi=doi or '',
                        method=method or '',
                        results=results or '',
                        conclusions=conclusions or '',
                        bibtex=bibtex or '',
                        sourceCode=sourceCode or '',
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    migrated += 1
                    print(f"Migrated paper: {title}")
                except Exception as e:
                    print(f"Error migrating paper {title}: {str(e)}")
        
        print(f"Migrated {migrated} papers")

def migrate_datasets():
    """Migrate Dataset data to public_api Dataset"""
    print("Migrating datasets...")
    
    with connection.cursor() as cursor:
        # Get count of datasets
        cursor.execute("SELECT COUNT(*) FROM users_dataset")
        count = cursor.fetchone()[0]
        print(f"Found {count} datasets to migrate")
        
        # Get all datasets
        cursor.execute("""
            SELECT 
                id, name, abbreviation, description, downloadUrl, 
                link, paper_link, subtitle, paperCount, language, 
                category, tasks, thumbnailUrl, benchmarks, dataloaders, 
                similar_datasets, papers, created_at, updated_at
            FROM users_dataset
        """)
        
        migrated = 0
        for row in cursor.fetchall():
            try:
                id, name, abbreviation, description, downloadUrl, \
                    link, paper_link, subtitle, paperCount, language, \
                    category, tasks, thumbnailUrl, benchmarks, dataloaders, \
                    similar_datasets, papers, created_at, updated_at = row
                
                # Check if dataset with same name exists
                if not Dataset.objects.filter(name=name).exists():
                    dataset = Dataset.objects.create(
                        id=uuid.uuid4(),  # Generate new UUID
                        name=name,
                        description=description,
                        data_type=category,
                        size=f"{paperCount} papers" if paperCount else "",
                        format="",
                        source_url=downloadUrl or "",
                        license="",
                        citation="",
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    migrated += 1
                    print(f"Migrated dataset: {name}")
            except Exception as e:
                print(f"Error migrating dataset: {str(e)}")
        
        print(f"Migrated {migrated} datasets")

def migrate_publications():
    """Migrate Publication data to public_api Publication"""
    print("Migrating publications...")
    
    with connection.cursor() as cursor:
        # Get count of publications
        cursor.execute("SELECT COUNT(*) FROM users_publication")
        count = cursor.fetchone()[0]
        print(f"Found {count} publications to migrate")
        
        # Get all publications
        cursor.execute("""
            SELECT 
                user_id, title, authors, journal, year, url,
                created_at, updated_at
            FROM users_publication
        """)
        
        migrated = 0
        for row in cursor.fetchall():
            try:
                user_id, title, authors, journal, year, url, created_at, updated_at = row
                
                # Get the user
                try:
                    user = User.objects.get(id=user_id)
                    
                    # Check if publication exists
                    if not Publication.objects.filter(user=user, title=title).exists():
                        publication = Publication.objects.create(
                            id=uuid.uuid4(),  # Generate new UUID
                            user=user,
                            title=title,
                            authors=authors,
                            venue=journal,
                            year=year,
                            url=url,
                            created_at=created_at,
                            updated_at=updated_at
                        )
                        migrated += 1
                        print(f"Migrated publication: {title} for user {user.username}")
                except User.DoesNotExist:
                    print(f"User with ID {user_id} does not exist, skipping publication")
            except Exception as e:
                print(f"Error migrating publication: {str(e)}")
        
        print(f"Migrated {migrated} publications")

@transaction.atomic
def run_migration():
    """Run the migration"""
    migrate_profiles()
    migrate_research_papers()
    migrate_datasets()
    migrate_publications()

if __name__ == "__main__":
    print("Starting migration from users app to public_api app...")
    run_migration()
    print("Migration completed.") 