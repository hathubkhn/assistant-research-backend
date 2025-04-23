from rest_framework.authentication import BaseAuthentication

class AllowAnyAuthentication(BaseAuthentication):
    """
    Custom authentication class that allows any user,
    authenticated or not, to access the view.
    """
    def authenticate(self, request):
        # Return None to indicate no authentication is performed
        # This will still allow the request to proceed
        return None 