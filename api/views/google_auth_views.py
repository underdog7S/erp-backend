import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from api.models.user import UserProfile, Tenant
from api.models.plan import Plan
import json

class GoogleOAuthView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Handle Google OAuth login/registration"""
        try:
            # Get the access token from request
            access_token = request.data.get('access_token')
            if not access_token:
                return Response({'error': 'Access token is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify the token with Google
            google_user_info = self.get_google_user_info(access_token)
            if not google_user_info:
                return Response({'error': 'Invalid access token'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Extract user information
            google_id = google_user_info.get('id')
            email = google_user_info.get('email')
            first_name = google_user_info.get('given_name', '')
            last_name = google_user_info.get('family_name', '')
            name = google_user_info.get('name', f"{first_name} {last_name}".strip())
            picture = google_user_info.get('picture', '')
            
            # Check if user already exists
            user = self.get_or_create_user(google_id, email, name, first_name, last_name, picture)
            
            # Get or create user profile
            profile = self.get_or_create_profile(user, request.data)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': profile.role.name if profile.role else None,
                    'tenant': profile.tenant.name if profile.tenant else None,
                    'industry': profile.tenant.industry if profile.tenant else None,
                },
                'is_new_user': profile.is_new_user
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_google_user_info(self, access_token):
        """Get user information from Google using access token"""
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception:
            return None
    
    def get_or_create_user(self, google_id, email, name, first_name, last_name, picture):
        """Get existing user or create new one"""
        # Try to find user by email first
        try:
            user = User.objects.get(email=email)
            # Update user info if needed
            if not user.first_name and first_name:
                user.first_name = first_name
            if not user.last_name and last_name:
                user.last_name = last_name
            user.save()
            return user
        except User.DoesNotExist:
            pass
        
        # Create new user
        username = self.generate_unique_username(email)
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=None  # No password for OAuth users
        )
        
        # Store Google ID in user profile or custom field
        # Note: We'll store this in UserProfile model instead
        # user.profile.google_id = google_id
        # user.profile.profile_picture = picture
        # user.profile.save()
        
        return user
    
    def get_or_create_profile(self, user, request_data):
        """Get or create user profile with tenant"""
        try:
            profile = UserProfile.objects.get(user=user)
            profile.is_new_user = False
            return profile
        except UserProfile.DoesNotExist:
            # Create new profile with tenant
            company = request_data.get('company', '')
            industry = request_data.get('industry', 'manufacturing')
            plan_name = request_data.get('plan', 'free')
            
            # Get or create tenant
            tenant, created = Tenant.objects.get_or_create(
                name=company or f"{user.first_name}'s Organization",
                defaults={
                    'industry': industry,
                    'storage_used_mb': 0
                }
            )
            
            # Get plan
            try:
                plan = Plan.objects.get(name__iexact=plan_name)
                tenant.plan = plan
                tenant.save()
            except Plan.DoesNotExist:
                # Use free plan as default
                plan = Plan.objects.get(name='Free')
                tenant.plan = plan
                tenant.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                tenant=tenant,
                is_new_user=True
            )
            
            return profile
    
    def generate_unique_username(self, email):
        """Generate unique username from email"""
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username

class GoogleOAuthCallbackView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Handle Google OAuth callback with authorization code"""
        try:
            # Get authorization code from request
            code = request.data.get('code')
            if not code:
                return Response({'error': 'Authorization code is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Exchange code for access token
            access_token = self.exchange_code_for_token(code)
            if not access_token:
                return Response({'error': 'Failed to exchange code for token'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user info using access token
            google_user_info = self.get_google_user_info(access_token)
            if not google_user_info:
                return Response({'error': 'Failed to get user info'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Process the same as direct OAuth
            google_id = google_user_info.get('id')
            email = google_user_info.get('email')
            first_name = google_user_info.get('given_name', '')
            last_name = google_user_info.get('family_name', '')
            name = google_user_info.get('name', f"{first_name} {last_name}".strip())
            picture = google_user_info.get('picture', '')
            
            # Get or create user
            user = self.get_or_create_user(google_id, email, name, first_name, last_name, picture)
            profile = self.get_or_create_profile(user, request.data)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': profile.role.name if profile.role else None,
                    'tenant': profile.tenant.name if profile.tenant else None,
                    'industry': profile.tenant.industry if profile.tenant else None,
                },
                'is_new_user': profile.is_new_user
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        try:
            # Get Google OAuth settings from Django settings
            client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
            client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')
            redirect_uri = getattr(settings, 'GOOGLE_OAUTH_REDIRECT_URI', '')
            
            if not all([client_id, client_secret, redirect_uri]):
                return None
            
            response = requests.post('https://oauth2.googleapis.com/token', data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
            })
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get('access_token')
            else:
                return None
                
        except Exception:
            return None
    
    def get_google_user_info(self, access_token):
        """Get user information from Google using access token"""
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception:
            return None
    
    def get_or_create_user(self, google_id, email, name, first_name, last_name, picture):
        """Get existing user or create new one"""
        # Try to find user by email first
        try:
            user = User.objects.get(email=email)
            # Update user info if needed
            if not user.first_name and first_name:
                user.first_name = first_name
            if not user.last_name and last_name:
                user.last_name = last_name
            user.save()
            return user
        except User.DoesNotExist:
            pass
        
        # Create new user
        username = self.generate_unique_username(email)
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=None  # No password for OAuth users
        )
        
        # Store Google ID in user profile or custom field
        # Note: We'll store this in UserProfile model instead
        # user.profile.google_id = google_id
        # user.profile.profile_picture = picture
        # user.profile.save()
        
        return user
    
    def get_or_create_profile(self, user, request_data):
        """Get or create user profile with tenant"""
        try:
            profile = UserProfile.objects.get(user=user)
            profile.is_new_user = False
            return profile
        except UserProfile.DoesNotExist:
            # Create new profile with tenant
            company = request_data.get('company', '')
            industry = request_data.get('industry', 'manufacturing')
            plan_name = request_data.get('plan', 'free')
            
            # Get or create tenant
            tenant, created = Tenant.objects.get_or_create(
                name=company or f"{user.first_name}'s Organization",
                defaults={
                    'industry': industry,
                    'storage_used_mb': 0
                }
            )
            
            # Get plan
            try:
                plan = Plan.objects.get(name__iexact=plan_name)
                tenant.plan = plan
                tenant.save()
            except Plan.DoesNotExist:
                # Use free plan as default
                plan = Plan.objects.get(name='Free')
                tenant.plan = plan
                tenant.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                tenant=tenant,
                is_new_user=True
            )
            
            return profile
    
    def generate_unique_username(self, email):
        """Generate unique username from email"""
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username 