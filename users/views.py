from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect

from allauth.socialaccount.models import SocialApp, SocialLogin, SocialToken, SocialAccount
from allauth.socialaccount.helpers import render_authentication_error

from .models import UserProfile, Paper, ResearchPaper, Dataset, DatasetReference, Publication
from .serializers import (
    UserSerializer, UserProfileSerializer, PaperSerializer, 
    UserRegistrationSerializer, ResearchPaperSerializer, DatasetSerializer,
    DatasetReferenceSerializer, PublicationSerializer
)
from .utils import extract_text_from_pdf, extract_metadata_with_openai

class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint that allows new users to register.
    
    Creates a new user account and optionally sets up the user profile.
    
    * Requires no authentication
    * Returns a token for the new user and profile completion status
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Register a new user with optional profile information.
        
        Required fields:
        - username: User's unique username
        - email: User's email address
        - password: User's password
        
        Optional fields:
        - password2: Password confirmation
        - full_name: User's full name
        - faculty_institute: User's affiliated institution
        - school: User's school
        - position: User's position (e.g., Professor, Student)
        - keywords: Research interests and keywords
        - google_scholar_link: Link to Google Scholar profile
        
        Returns:
        - token: Authentication token for the new user
        - user_id: ID of the newly created user
        - email: User's email
        - username: User's username
        - is_profile_completed: Boolean indicating if the profile is complete
        """
        # Print request data for debugging
        print(f"Registration request data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate token for the user
        token, created = Token.objects.get_or_create(user=user)
        
        # Get or create user profile
        profile = user.profile
        
        # Print profile data for debugging
        print(f"User profile after creation: {profile.__dict__}")
        
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username,
            'is_profile_completed': profile.is_profile_completed
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    """
    API endpoint that provides login options.
    
    Returns URLs for various authentication methods, including:
    - Google SSO login
    - Microsoft SSO login
    - Username/password login
    
    * Requires no authentication
    * Returns URLs for different login methods
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """
        Get available login methods.
        
        Returns:
        - google_login: URL for Google SSO login
        - microsoft_login: URL for Microsoft SSO login
        - token_login: URL for username/password login
        """
        return Response({
            'google_login': '/accounts/google/login/',
            'microsoft_login': '/accounts/microsoft/login/',
            'token_login': '/api/token-login/',
        })

class LogoutView(APIView):
    """
    API endpoint for logging out users.
    
    Invalidates the user's authentication token.
    
    * Requires authentication
    * Deletes the user's authentication token
    * Returns a success message
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Log out the current user.
        
        Invalidates the user's authentication token and logs them out.
        
        Returns:
        - A success message confirming logout
        """
        # Delete the user's token to logout
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        logout(request)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint that allows users to view and update their profile.
    
    Retrieves and updates the authenticated user's profile information.
    
    * Requires token authentication
    * Only the authenticated user can access their own profile
    * PUT and PATCH methods supported for updates
    * Returns complete profile information including user details
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """
        Returns the authenticated user's profile.
        """
        return self.request.user.profile
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve the user profile with publications.
        """
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        user_publications = Publication.objects.filter(user=request.user).order_by('-year')
        publications_serializer = PublicationSerializer(user_publications, many=True)
        
        # Combine profile data with publications
        data = serializer.data
        data['publications'] = publications_serializer.data
        
        return Response(data)
    
    def update(self, request, *args, **kwargs):
        """
        Update the user profile.
        
        Fields that can be updated:
        - full_name: User's full name
        - faculty_institute: User's affiliated institution
        - school: User's school
        - position: User's position (e.g., Professor, Student)
        - keywords: Research interests and keywords
        - google_scholar_link: Link to Google Scholar profile
        - bio: User biography
        
        Returns the complete updated profile with user information.
        Profile is marked as completed if all required fields are filled.
        """
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Get the updated profile
        profile.refresh_from_db()
        
        # Get publications
        user_publications = Publication.objects.filter(user=request.user).order_by('-year')
        publications_serializer = PublicationSerializer(user_publications, many=True)
        
        # Return detailed response including user information and publications
        return Response({
            'id': profile.id,
            'user': {
                'id': profile.user.id,
                'username': profile.user.username,
                'email': profile.user.email,
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
            },
            'full_name': profile.full_name,
            'faculty_institute': profile.faculty_institute,
            'school': profile.school,
            'keywords': profile.keywords,
            'position': profile.position,
            'google_scholar_link': profile.google_scholar_link,
            'bio': profile.bio,
            'is_profile_completed': profile.is_profile_completed,
            'created_at': profile.created_at,
            'updated_at': profile.updated_at,
            'publications': publications_serializer.data,
        })

class UserView(generics.RetrieveAPIView):
    """
    API endpoint that returns the current user's information.
    
    Returns basic information about the authenticated user.
    
    * Requires authentication
    * Returns user ID, username, email, first name, and last name
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """
        Returns the current authenticated user.
        """
        return self.request.user

class SSOCallbackView(APIView):
    """
    API endpoint that handles SSO callbacks from authentication providers.
    
    This endpoint is designed to receive redirects from OAuth providers (Google, Microsoft)
    after successful authentication. It should not be called directly from client applications.
    
    * Requires no authentication
    * Redirects to frontend with authentication token
    * Not intended for direct API calls or testing via Swagger
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="This endpoint is not meant to be called directly from Swagger UI. Please use the /api/sso-info/ endpoint for information about the SSO flow.",
        responses={
            302: openapi.Response('Redirect to frontend with token'),
            400: openapi.Response('Error response when called directly from Swagger')
        }
    )
    def get(self, request, provider):
        """
        Handle the SSO callback and redirect to frontend.
        
        This is a server-side endpoint that handles OAuth provider redirects.
        It is not meant to be called directly from clients or tested via Swagger UI.
        
        Parameters:
        - provider: The OAuth provider name (e.g., 'google', 'microsoft')
        
        Returns:
        - HTTP redirect to frontend with token parameter
        """
        # Check if the request is coming from Swagger UI
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referer = request.META.get('HTTP_REFERER', '')
        
        if 'swagger' in referer.lower() or 'api-docs' in referer.lower():
            return Response({
                "error": "This endpoint is not meant to be called directly from Swagger UI",
                "message": "This endpoint is designed to handle OAuth provider redirects, not direct API calls",
                "help": "Please use the /api/sso-info/ endpoint for information about the SSO flow",
                "alternative": "To test authenticated endpoints, use /api/token-login/ or /api/register/ to obtain a token"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # This view is for handling the SSO callback and redirecting to frontend with token
        if request.user.is_authenticated:
            # Get or create a token for the user
            token, created = Token.objects.get_or_create(user=request.user)
            
            # Redirect to frontend with token
            redirect_url = f"{settings.FRONTEND_URL}/sso-callback?token={token.key}&provider={provider}"
            return HttpResponseRedirect(redirect_url)
        
        # If user is not authenticated, redirect to login
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/login?error=authentication_failed")

class TokenLoginView(ObtainAuthToken):
    """
    API endpoint for authenticating users with username and password.
    
    Validates the username and password and returns an authentication token
    if credentials are valid.
    
    * Requires no authentication
    * Returns a token, user ID, email, and profile completion status
    """
    def post(self, request, *args, **kwargs):
        """
        Authenticate a user and return a token.
        
        Required fields:
        - username: User's username
        - password: User's password
        
        Returns:
        - token: Authentication token for the user
        - user_id: ID of the authenticated user
        - email: User's email address
        - is_profile_completed: Boolean indicating if the profile is complete
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'is_profile_completed': profile.is_profile_completed
        })

class MicrosoftAuthCallbackView(APIView):
    """
    API endpoint that handles Microsoft OAuth callbacks and token generation.
    
    This endpoint handles the server-side exchange of OAuth code for token
    and user information from Microsoft Graph API.
    
    * Requires no authentication
    * Exchanges authorization code for Microsoft Graph access token
    * Creates or retrieves user account based on Microsoft profile
    * Returns an authentication token for the user
    
    Note: This endpoint is not meant to be called directly from Swagger UI.
    It is designed to work with the frontend's OAuth flow.
    
    When accessed from a private IP address, device_id and device_name parameters are required.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Handle Microsoft OAuth code exchange and user creation/login.
        
        Required fields:
        - code: Authorization code from Microsoft OAuth flow
        - redirect_uri: The redirect URI used in the OAuth flow
        - device_id: Unique identifier for the device (required for private IP access)
        - device_name: Name of the device (required for private IP access)
        
        Process:
        1. Exchanges code for access token with Microsoft
        2. Retrieves user information from Microsoft Graph API
        3. Creates or retrieves a user account based on the email
        4. Generates an authentication token
        
        Returns:
        - token: Authentication token for the user
        - user_id: User's ID
        - email: User's email address
        """
        try:
            code = request.data.get('code')
            redirect_uri = request.data.get('redirect_uri')
            device_id = request.data.get('device_id')
            device_name = request.data.get('device_name')
            
            print(f"Microsoft callback received - code: {code[:10] if code else None}... redirect_uri: {redirect_uri}")
            
            # Check if request is coming from a private IP
            client_ip = request.META.get('REMOTE_ADDR', '')
            is_private_ip = (
                client_ip.startswith('10.') or 
                client_ip.startswith('172.16.') or 
                client_ip.startswith('192.168.') or
                client_ip == '127.0.0.1'
            )
            
            # For private IP addresses, device_id and device_name are required
            if is_private_ip and (not device_id or not device_name):
                return Response(
                    {"error": "invalid_request", "error_description": "device_id and device_name are required for private IP access"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not code or not redirect_uri:
                return Response(
                    {"error": "Missing code or redirect_uri parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get OAuth credentials
            client_id = settings.SOCIAL_AUTH_MICROSOFT_OAUTH2_KEY
            client_secret = settings.SOCIAL_AUTH_MICROSOFT_OAUTH2_SECRET
            
            print(f"Using Microsoft OAuth credentials - client_id: {client_id[:5]}... client_secret: {client_secret[:5]}...")
            
            # Exchange code for token with Microsoft
            import requests
            token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            }
            
            token_response = requests.post(token_url, data=token_data)
            token_json = token_response.json()
            
            print(f"Microsoft token response status: {token_response.status_code}")
            
            if 'access_token' not in token_json:
                error_details = token_json.get('error_description', token_json.get('error', 'Unknown error'))
                print(f"Failed to obtain Microsoft access token: {error_details}")
                return Response(
                    {"error": "Failed to obtain access token", "details": token_json},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user info from Microsoft Graph
            access_token = token_json['access_token']
            user_info_url = 'https://graph.microsoft.com/v1.0/me'
            user_response = requests.get(
                user_info_url,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            user_data = user_response.json()
            
            # Get or create user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            email = user_data.get('mail') or user_data.get('userPrincipalName')
            if not email:
                print(f"No email found in Microsoft user data: {user_data}")
                return Response(
                    {"error": "No email found in Microsoft user data"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user exists with this email
            try:
                user = User.objects.get(email=email)
                print(f"Found existing user with email: {email}")
            except User.DoesNotExist:
                # Create new user
                username = email.split('@')[0]
                # Ensure last_name is never null by using a default value 
                surname = user_data.get('surname')
                last_name = surname if surname else " "  # Use a space as default
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=user_data.get('givenName', ''),
                    last_name=last_name
                )
                # Create user profile
                UserProfile.objects.create(user=user)
                print(f"Created new user with email: {email}")
            
            # Create or get social account
            social_account, created = SocialAccount.objects.get_or_create(
                provider='microsoft',
                uid=user_data.get('id'),
                user=user
            )
            
            # Generate auth token
            token, created = Token.objects.get_or_create(user=user)
            
            print(f"Microsoft authentication successful for user: {email}")
            return Response({
                'token': token.key,
                'user_id': user.id,
                'email': user.email
            })
            
        except Exception as e:
            import traceback
            print(f"Microsoft OAuth Error: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Authentication failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GoogleAuthCallbackView(APIView):
    """
    API endpoint that handles Google OAuth callbacks and token generation.
    
    This endpoint handles the server-side exchange of OAuth code for token
    and user information from Google APIs.
    
    * Requires no authentication
    * Exchanges authorization code for Google access token
    * Creates or retrieves user account based on Google profile
    * Returns an authentication token for the user
    
    Note: This endpoint is not meant to be called directly from Swagger UI.
    It is designed to work with the frontend's OAuth flow.
    
    When accessed from a private IP address, device_id and device_name parameters are required.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Handle Google OAuth code exchange and user creation/login.
        
        Required fields:
        - code: Authorization code from Google OAuth flow
        - redirect_uri: The redirect URI used in the OAuth flow
        - device_id: Unique identifier for the device (required for private IP access)
        - device_name: Name of the device (required for private IP access)
        
        Process:
        1. Exchanges code for access token with Google
        2. Retrieves user information from Google API
        3. Creates or retrieves a user account based on the email
        4. Generates an authentication token
        
        Returns:
        - token: Authentication token for the user
        - user_id: User's ID
        - email: User's email address
        """
        try:
            code = request.data.get('code')
            redirect_uri = request.data.get('redirect_uri')
            device_id = request.data.get('device_id')
            device_name = request.data.get('device_name')
            
            # Check if request is coming from a private IP
            client_ip = request.META.get('REMOTE_ADDR', '')
            is_private_ip = (
                client_ip.startswith('10.') or 
                client_ip.startswith('172.16.') or 
                client_ip.startswith('192.168.') or
                client_ip == '127.0.0.1'
            )
            
            # For private IP addresses, device_id and device_name are required
            if is_private_ip and (not device_id or not device_name):
                return Response(
                    {"error": "invalid_request", "error_description": "device_id and device_name are required for private IP access"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not code or not redirect_uri:
                return Response(
                    {"error": "Missing code or redirect_uri parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get OAuth credentials
            client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            client_secret = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
            
            # Exchange code for token with Google
            import requests
            token_url = 'https://oauth2.googleapis.com/token'
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            }
            
            token_response = requests.post(token_url, data=token_data)
            token_json = token_response.json()
            
            if 'access_token' not in token_json:
                return Response(
                    {"error": "Failed to obtain access token", "details": token_json},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user info from Google
            access_token = token_json['access_token']
            user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            user_response = requests.get(
                user_info_url,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            user_data = user_response.json()
            
            # Get or create user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            email = user_data.get('email')
            if not email:
                return Response(
                    {"error": "No email found in Google user data"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user exists with this email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create new user
                username = email.split('@')[0]
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=user_data.get('given_name', ''),
                    last_name=user_data.get('family_name', '')
                )
                # Create user profile - this is redundant since we have a signal in models.py
                # that automatically creates a profile when a user is created
                # UserProfile.objects.create(user=user)
            
            # Create or get social account
            social_account, created = SocialAccount.objects.get_or_create(
                provider='google',
                uid=user_data.get('id'),
                user=user
            )
            
            # Generate auth token
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'token': token.key,
                'user_id': user.id,
                'email': user.email
            })
            
        except Exception as e:
            import traceback
            print(f"Google OAuth Error: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Authentication failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PaperUploadView(APIView):
    """
    API endpoint that allows users to upload academic papers.
    
    Handles PDF file uploads and automatically extracts metadata using Azure OpenAI.
    
    * Requires token authentication
    * Supports multipart/form-data for file uploads
    * Automatically extracts metadata from the paper
    * Returns the created paper with extracted metadata
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """
        Upload a PDF academic paper and extract metadata.
        
        Required:
        - file: PDF file upload (multipart/form-data)
        
        Process:
        1. Validates the uploaded file is a PDF
        2. Extracts text from the PDF
        3. Analyzes the content using Azure OpenAI to extract metadata
        4. Creates a paper record with the extracted metadata
        
        Returns:
        - Complete paper object with extracted metadata including:
          - title: Paper title
          - authors: List of authors
          - conference: Conference or journal name
          - year: Publication year
          - field: Research field
          - keywords: List of keywords
          - abstract: Paper abstract
          - doi: Digital Object Identifier
          - bibtex: BibTeX citation
          - sourceCode: Source code
          - file information (name, size)
        """
        # Debug information
        print("---- Paper Upload Debug ----")
        print(f"User: {request.user}")
        print(f"Auth: {request.auth}")
        print(f"FILES: {request.FILES}")
        print(f"Content-Type: {request.headers.get('Content-Type')}")
        
        # Check if 'file' is in the request
        if 'file' not in request.FILES:
            return Response(
                {"error": "No file was provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        # Check if the file is a PDF
        if not file.name.lower().endswith('.pdf'):
            return Response(
                {"error": "Only PDF files are supported."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract text from PDF
        try:
            pdf_text = extract_text_from_pdf(file)
            
            # Extract metadata using OpenAI
            metadata = extract_metadata_with_openai(pdf_text, file.name)
            
            # Create a paper object
            paper_data = {
                'user': request.user,
                'title': metadata['title'],
                'authors': metadata['authors'],
                'conference': metadata['conference'],
                'year': metadata['year'],
                'field': metadata['field'],
                'keywords': metadata['keywords'],
                'abstract': metadata['abstract'],
                'doi': metadata['doi'],
                'bibtex': metadata['bibtex'],
                'sourceCode': metadata['sourceCode'],
                'is_interesting': False,
                'is_downloaded': False,
                'is_uploaded': True,
                'file': file,
                'file_name': file.name,
                'file_size': file.size
            }
            
            paper = Paper.objects.create(**paper_data)
            
            # Serialize and return the paper
            serializer = PaperSerializer(paper)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print(f"Error processing the PDF: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Error processing the PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserPapersView(generics.ListAPIView):
    """
    API endpoint that lists all papers for the authenticated user.
    
    Returns a paginated list of papers owned by the authenticated user,
    sorted by date added (newest first).
    
    * Requires token authentication
    * Only returns papers owned by the authenticated user
    """
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Returns all papers belonging to the current user, ordered by date added (newest first).
        """
        user = self.request.user
        return Paper.objects.filter(user=user).order_by('-added_date')

class PaperDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint that allows retrieving, updating, or deleting a specific paper.
    
    * Requires token authentication
    * Users can only access their own papers
    * Supports GET, PUT, PATCH, and DELETE methods
    * Only selected fields can be updated
    """
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Returns papers belonging to the current user.
        """
        user = self.request.user
        return Paper.objects.filter(user=user)
    
    def perform_update(self, serializer):
        """
        Update only the is_interesting and is_downloaded fields.
        
        Other fields are read-only and cannot be modified after creation.
        """
        serializer.save(
            is_interesting=serializer.validated_data.get('is_interesting', 
                                                       serializer.instance.is_interesting),
            is_downloaded=serializer.validated_data.get('is_downloaded',
                                                      serializer.instance.is_downloaded)
        )

class SSOExplanationView(APIView):
    """
    API endpoint that explains how to use the SSO authentication flow.
    
    This endpoint provides instructions on how to properly implement
    the OAuth flow with the API. It does not perform any action.
    
    * Requires no authentication
    * Simply returns documentation about the OAuth flow
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get information about how to implement SSO authentication with this API",
        responses={200: openapi.Response('SSO flow documentation')}
    )
    def get(self, request):
        """
        Get documentation on how to implement the SSO authentication flow.
        
        Returns:
        - Instructions for implementing OAuth flow with Google and Microsoft
        - Details on how the SSO callback endpoints should be used
        """
        return Response({
            'title': 'Using Single Sign-On (SSO) with this API',
            'description': 'This document describes how to implement SSO authentication properly with this API.',
            'steps': [
                {
                    'step': 1,
                    'description': 'Redirect user to the appropriate OAuth provider login page.',
                    'details': 'For Google: https://accounts.google.com/o/oauth2/auth with appropriate parameters. For Microsoft: https://login.microsoftonline.com/common/oauth2/v2.0/authorize with appropriate parameters.'
                },
                {
                    'step': 2,
                    'description': 'After successful authentication, the provider redirects back to your callback URL with an authorization code.',
                    'details': 'Your frontend should capture this code from the URL parameters.'
                },
                {
                    'step': 3,
                    'description': 'Send the authorization code to the appropriate backend endpoint.',
                    'details': 'For Google: POST to /api/auth/google/callback with the code. For Microsoft: POST to /api/auth/microsoft/callback with the code.'
                },
                {
                    'step': 4,
                    'description': 'Receive the API authentication token from the response.',
                    'details': 'The response will include a token that should be included in the Authorization header of subsequent API requests as "Token YOUR_TOKEN".'
                }
            ],
            'notes': [
                'The SSO-callback endpoint is not meant to be called directly. It exists for the OAuth providers to redirect users after authentication.',
                'All OAuth-related parameters should be properly URL-encoded.',
                'For testing purposes, you can use the token-login endpoint with username and password.'
            ]
        })

# New views for Research Papers and Datasets
class ResearchPaperListView(generics.ListAPIView):
    """
    API endpoint to list all research papers.
    
    Returns a paginated list of all research papers with their details and associated datasets.
    
    * Requires no authentication
    * Supports filtering by year, field, and keywords
    """
    serializer_class = ResearchPaperSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = ResearchPaper.objects.all().order_by('-year')
        
        # Filter by year
        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)
            
        # Filter by field
        field = self.request.query_params.get('field')
        if field:
            queryset = queryset.filter(field=field)
            
        # Filter by keywords
        keyword = self.request.query_params.get('keyword')
        if keyword:
            # Filter papers where the keyword exists in the JSON array
            queryset = queryset.filter(keywords__contains=[keyword])
            
        return queryset

class ResearchPaperDetailView(generics.RetrieveAPIView):
    """
    API endpoint to retrieve details for a specific research paper.
    
    Returns detailed information about a specific research paper including
    associated datasets.
    
    * Requires no authentication
    * Returns complete paper information with related datasets
    """
    queryset = ResearchPaper.objects.all()
    serializer_class = ResearchPaperSerializer
    permission_classes = [permissions.AllowAny]

class DatasetListView(generics.ListAPIView):
    """
    API endpoint to list all datasets.
    
    Returns a paginated list of all datasets with their details.
    
    * Requires no authentication
    * Supports filtering by category and language
    """
    serializer_class = DatasetSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Dataset.objects.all().order_by('-paperCount')
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
            
        # Filter by language
        language = self.request.query_params.get('language')
        if language:
            queryset = queryset.filter(language=language)
            
        return queryset

class DatasetDetailView(generics.RetrieveAPIView):
    """
    API endpoint to retrieve details for a specific dataset.
    
    Returns detailed information about a specific dataset.
    
    * Requires no authentication
    * Returns complete dataset information
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.AllowAny]
    
class DatasetPapersView(APIView):
    """
    API endpoint to retrieve all papers associated with a specific dataset.
    
    Returns a list of all research papers that use the specified dataset.
    
    * Requires no authentication
    * Returns papers associated with the dataset
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, dataset_id):
        try:
            dataset = Dataset.objects.get(pk=dataset_id)
            
            # Get all papers associated with this dataset
            dataset_refs = DatasetReference.objects.filter(dataset=dataset)
            papers = [ref.paper for ref in dataset_refs]
            
            serializer = ResearchPaperSerializer(papers, many=True)
            return Response(serializer.data)
        except Dataset.DoesNotExist:
            return Response(
                {"error": "Dataset not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class PublicationsView(APIView):
    """
    API endpoint to handle user publications
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        publications = Publication.objects.filter(user=request.user).order_by('-year')
        serializer = PublicationSerializer(publications, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = PublicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PublicationDetailView(APIView):
    """
    API endpoint to handle a specific publication
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk, user):
        try:
            return Publication.objects.get(pk=pk, user=user)
        except Publication.DoesNotExist:
            raise Http404("Publication not found")
    
    def get(self, request, pk):
        publication = self.get_object(pk, request.user)
        serializer = PublicationSerializer(publication)
        return Response(serializer.data)
    
    def put(self, request, pk):
        publication = self.get_object(pk, request.user)
        serializer = PublicationSerializer(publication, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        publication = self.get_object(pk, request.user)
        print(f"[DEBUG] Deleting publication with ID {pk} (from Users app)")
        publication.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
