from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

class Command(BaseCommand):
    help = 'Creates a test user for development'

    def handle(self, *args, **options):
        username = 'testuser'
        email = 'test@example.com'
        password = 'testpassword'

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            self.stdout.write(self.style.WARNING(f'User {username} already exists'))
        else:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created user: {username}'))
        
        # Create or get token
        token, created = Token.objects.get_or_create(user=user)
        status = 'Created new' if created else 'Using existing'
        
        self.stdout.write(self.style.SUCCESS(f'{status} token for {username}: {token.key}'))
        self.stdout.write(self.style.SUCCESS(f'Use these credentials for testing:'))
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'Token: {token.key}') 