import logging
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserProfile
from django.db import connections, transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronize user data between research_asssistant_db and auth_db'

    def add_arguments(self, parser):
        parser.add_argument(
            '--direction',
            type=str,
            default='both',
            choices=['to-auth', 'to-research', 'both'],
            help='Direction to sync: to-auth, to-research, or both'
        )

    def handle(self, *args, **kwargs):
        # Check if PostgreSQL is enabled
        use_postgres = os.environ.get('USE_POSTGRES', 'False').lower() in ('true', '1', 't')
        if not use_postgres:
            self.stderr.write(self.style.ERROR("Error: USE_POSTGRES environment variable must be set to True for database synchronization"))
            self.stderr.write("Run the command with: export USE_POSTGRES=True && python manage.py sync_users")
            return

        # Check if auth_db connection exists
        if 'auth_db' not in connections:
            self.stderr.write(self.style.ERROR("Error: 'auth_db' connection does not exist. Make sure settings.py has proper configuration."))
            return

        direction = kwargs['direction']
        
        if direction in ['to-auth', 'both']:
            self.sync_to_auth_db()
        
        if direction in ['to-research', 'both']:
            self.sync_to_research_db()
        
        self.stdout.write(self.style.SUCCESS('User synchronization completed successfully!'))

    def sync_to_auth_db(self):
        """Sync users from research_asssistant_db to auth_db"""
        self.stdout.write('Syncing users from research_asssistant_db to auth_db...')
        
        # Get all users from the research_asssistant_db
        users = User.objects.using('default').all()
        
        with connections['auth_db'].cursor() as cursor:
            for user in users:
                try:
                    # Check if user exists in auth_db
                    cursor.execute("SELECT id FROM auth_user WHERE username = %s", [user.username])
                    result = cursor.fetchone()
                    
                    if not result:
                        # User doesn't exist, create it
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
                        self.stdout.write(f'Created user {user.username} (ID: {user_id_in_auth_db}) in auth_db')
                        
                        # Now sync profile
                        if hasattr(user, 'profile'):
                            profile = user.profile
                            cursor.execute(
                                """
                                INSERT INTO users_userprofile
                                (user_id, full_name, faculty_institute, school, keywords, position, 
                                google_scholar_link, is_profile_completed, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                [
                                    user_id_in_auth_db, profile.full_name, profile.faculty_institute, 
                                    profile.school, profile.keywords, profile.position, 
                                    profile.google_scholar_link, profile.is_profile_completed,
                                    profile.created_at, profile.updated_at
                                ]
                            )
                            self.stdout.write(f'Created profile for user {user.username} in auth_db')
                    else:
                        # User exists, update it
                        user_id_in_auth_db = result[0]
                        cursor.execute(
                            """
                            UPDATE auth_user 
                            SET password = %s, last_login = %s, is_superuser = %s, 
                                first_name = %s, last_name = %s, email = %s, 
                                is_staff = %s, is_active = %s, date_joined = %s
                            WHERE id = %s
                            """,
                            [
                                user.password, user.last_login, user.is_superuser, 
                                user.first_name, user.last_name, user.email, 
                                user.is_staff, user.is_active, user.date_joined,
                                user_id_in_auth_db
                            ]
                        )
                        self.stdout.write(f'Updated user {user.username} (ID: {user_id_in_auth_db}) in auth_db')
                        
                        # Now update profile
                        if hasattr(user, 'profile'):
                            profile = user.profile
                            # Check if profile exists
                            cursor.execute("SELECT id FROM users_userprofile WHERE user_id = %s", [user_id_in_auth_db])
                            profile_exists = cursor.fetchone() is not None
                            
                            if profile_exists:
                                cursor.execute(
                                    """
                                    UPDATE users_userprofile
                                    SET full_name = %s, faculty_institute = %s, school = %s, 
                                        keywords = %s, position = %s, google_scholar_link = %s,
                                        is_profile_completed = %s, updated_at = %s
                                    WHERE user_id = %s
                                    """,
                                    [
                                        profile.full_name, profile.faculty_institute, profile.school,
                                        profile.keywords, profile.position, profile.google_scholar_link,
                                        profile.is_profile_completed, profile.updated_at,
                                        user_id_in_auth_db
                                    ]
                                )
                                self.stdout.write(f'Updated profile for user {user.username} in auth_db')
                            else:
                                # Insert profile
                                cursor.execute(
                                    """
                                    INSERT INTO users_userprofile
                                    (user_id, full_name, faculty_institute, school, keywords, position, 
                                    google_scholar_link, is_profile_completed, created_at, updated_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    [
                                        user_id_in_auth_db, profile.full_name, profile.faculty_institute, 
                                        profile.school, profile.keywords, profile.position, 
                                        profile.google_scholar_link, profile.is_profile_completed,
                                        profile.created_at, profile.updated_at
                                    ]
                                )
                                self.stdout.write(f'Created missing profile for user {user.username} in auth_db')
                
                except Exception as e:
                    self.stderr.write(f'Error syncing user {user.username} to auth_db: {e}')
            
            connections['auth_db'].commit()

    def sync_to_research_db(self):
        """Sync users from auth_db to research_asssistant_db"""
        self.stdout.write('Syncing users from auth_db to research_asssistant_db...')
        
        # We need to query auth_db directly since it's not the default database for models
        with connections['auth_db'].cursor() as cursor:
            cursor.execute(
                """
                SELECT id, password, last_login, is_superuser, username, first_name, 
                last_name, email, is_staff, is_active, date_joined
                FROM auth_user
                """
            )
            auth_users = cursor.fetchall()
            
            for auth_user in auth_users:
                (user_id, password, last_login, is_superuser, username, first_name, 
                 last_name, email, is_staff, is_active, date_joined) = auth_user
                
                try:
                    # Check if user exists in research_asssistant_db
                    user_exists = User.objects.using('default').filter(username=username).exists()
                    
                    if not user_exists:
                        with transaction.atomic(using='default'):
                            # Create user in research_asssistant_db
                            new_user = User(
                                username=username,
                                password=password,
                                first_name=first_name,
                                last_name=last_name,
                                email=email,
                                is_staff=is_staff,
                                is_superuser=is_superuser,
                                is_active=is_active,
                                date_joined=date_joined
                            )
                            if last_login:
                                new_user.last_login = last_login
                            new_user.save(using='default')
                            
                            self.stdout.write(f'Created user {username} in research_asssistant_db')
                            
                            # Now get and create profile
                            cursor.execute(
                                """
                                SELECT full_name, faculty_institute, school, keywords, position, 
                                google_scholar_link, is_profile_completed, created_at, updated_at
                                FROM users_userprofile
                                WHERE user_id = %s
                                """,
                                [user_id]
                            )
                            profile_data = cursor.fetchone()
                            
                            if profile_data:
                                (full_name, faculty_institute, school, keywords, position, 
                                 google_scholar_link, is_profile_completed, created_at, updated_at) = profile_data
                                
                                # Profile should be created by the post_save signal, just update it
                                profile = new_user.profile
                                profile.full_name = full_name
                                profile.faculty_institute = faculty_institute
                                profile.school = school
                                profile.keywords = keywords
                                profile.position = position
                                profile.google_scholar_link = google_scholar_link
                                profile.is_profile_completed = is_profile_completed
                                profile.created_at = created_at
                                profile.updated_at = updated_at
                                profile.save(using='default')
                                
                                self.stdout.write(f'Created profile for user {username} in research_asssistant_db')
                    else:
                        # User exists, update it
                        with transaction.atomic(using='default'):
                            user = User.objects.using('default').get(username=username)
                            user.password = password
                            if last_login:
                                user.last_login = last_login
                            user.is_superuser = is_superuser
                            user.first_name = first_name
                            user.last_name = last_name
                            user.email = email
                            user.is_staff = is_staff
                            user.is_active = is_active
                            user.date_joined = date_joined
                            user.save(using='default')
                            
                            self.stdout.write(f'Updated user {username} in research_asssistant_db')
                            
                            # Now update profile
                            cursor.execute(
                                """
                                SELECT full_name, faculty_institute, school, keywords, position, 
                                google_scholar_link, is_profile_completed, created_at, updated_at
                                FROM users_userprofile
                                WHERE user_id = %s
                                """,
                                [user_id]
                            )
                            profile_data = cursor.fetchone()
                            
                            if profile_data:
                                (full_name, faculty_institute, school, keywords, position, 
                                 google_scholar_link, is_profile_completed, created_at, updated_at) = profile_data
                                
                                if hasattr(user, 'profile'):
                                    profile = user.profile
                                    profile.full_name = full_name
                                    profile.faculty_institute = faculty_institute
                                    profile.school = school
                                    profile.keywords = keywords
                                    profile.position = position
                                    profile.google_scholar_link = google_scholar_link
                                    profile.is_profile_completed = is_profile_completed
                                    profile.save(using='default')
                                    
                                    self.stdout.write(f'Updated profile for user {username} in research_asssistant_db')
                
                except Exception as e:
                    self.stderr.write(f'Error syncing user {username} to research_asssistant_db: {e}') 