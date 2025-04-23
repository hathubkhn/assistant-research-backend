from django.shortcuts import redirect
from social_core.pipeline.partial import partial
from urllib.parse import urlencode
from rest_framework.authtoken.models import Token

@partial
def redirect_to_signup(strategy, details, user=None, is_new=False, *args, **kwargs):
    """
    Custom pipeline function to redirect user to signup page if they are new or
    if their profile is incomplete.
    """
    if user:
        # Create or get auth token for the user
        token, _ = Token.objects.get_or_create(user=user)
        
        # Check if the profile is already completed
        if hasattr(user, 'profile') and user.profile.is_profile_completed:
            return
            
        # Get the current backend name (google or microsoft)
        backend_name = kwargs.get('backend').name.split('-')[0]
        
        # User exists but profile is incomplete, redirect to signup
        query_params = {
            'token': token.key,
            'is_new': is_new,
            'provider': backend_name
        }
        
        redirect_url = f"{strategy.session_get('frontend_url', 'http://localhost:3000')}/signup?{urlencode(query_params)}"
        return redirect(redirect_url) 