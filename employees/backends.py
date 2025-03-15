from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User, Team, Management

class CustomAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # First try to find user by email or phone
            user = User.objects.filter(
                Q(email=username) | Q(phone=username)
            ).first()
            
            if not user:
                # Try to find by team_id
                team = Team.objects.filter(team_id=username).first()
                if team:
                    user = team.user
                
                # Try to find by management_id
                management = Management.objects.filter(management_id=username).first()
                if management:
                    user = management.user
            
            if user and user.check_password(password):
                return user
            
            return None
            
        except Exception:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None 