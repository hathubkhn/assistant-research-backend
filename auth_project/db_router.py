class AuthRouter:
    """
    A router to control database operations for auth and user models.
    This router will:
    1. Ensure user models are saved to both databases
    2. Allow reads from the default database
    """
    auth_app_labels = {'auth', 'users', 'contenttypes', 'sessions', 'admin', 'authtoken', 'social_django', 'sites', 'account', 'socialaccount'}
    
    def db_for_read(self, model, **hints):
        """
        Attempts to read auth models go to default database.
        """
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Attempts to write auth models go to default database.
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between objects in the auth apps.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the auth apps are migrated on both databases.
        """
        if app_label in self.auth_app_labels:
            return True
        return None
        
    def allow_syncdb(self, db, model):
        """
        Make sure the auth app appears on both databases.
        """
        if db == 'default':
            return True
        elif db == 'auth_db' and model._meta.app_label in self.auth_app_labels:
            return True
        return None 