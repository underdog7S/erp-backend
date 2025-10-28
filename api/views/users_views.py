from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth.models import User
from api.models.user import UserProfile, Tenant, Role
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import update_session_auth_hash
from django.conf import settings
from api.models.user import Role
from api.models.permissions import role_required
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework import viewsets
from api.models.serializers import UserProfileSerializer

# --- UserProfileSerializer ---
class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'tenant', 'role', 'assigned_classes', 'department',
            'photo', 'phone', 'address', 'date_of_birth', 'gender', 'emergency_contact',
            'job_title', 'joining_date', 'qualifications', 'bio', 'linkedin'
        ]
        read_only_fields = ['id', 'user', 'tenant']

    def get_user(self, obj):
        return {
            'username': obj.user.username if obj.user else None,
            'email': obj.user.email if obj.user else None,
            'first_name': obj.user.first_name if obj.user else None,
            'last_name': obj.user.last_name if obj.user else None,
        }

    def get_role(self, obj):
        return obj.role.name if obj.role else None

    def get_department(self, obj):
        return {'id': obj.department.id, 'name': obj.department.name} if obj.department else None

class UserListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class UserListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        tenant = profile.tenant
        users = UserProfile._default_manager.filter(tenant=tenant)
        # Filtering
        search = request.query_params.get('search')
        department = request.query_params.get('department')
        role = request.query_params.get('role')
        if search:
            users = users.filter(
                (
                    (Q(user__username__icontains=search)) |
                    (Q(user__email__icontains=search)) |
                    (Q(phone__icontains=search)) |
                    (Q(address__icontains=search)) |
                    (Q(job_title__icontains=search))
                )
            )
        if department:
            users = users.filter(department_id=department)
        if role:
            users = users.filter(role__name__iexact=role)
        # Pagination
        paginator = UserListPagination()
        page = paginator.paginate_queryset(users, request)
        serializer = UserProfileSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

class AddUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        tenant = profile.tenant
        # Enforce user limit
        current_user_count = UserProfile._default_manager.filter(tenant=tenant).count()
        if tenant.plan and hasattr(tenant.plan, 'max_users'):
            max_users = tenant.plan.max_users
            if current_user_count >= max_users:
                return Response({"error": f"User limit reached for your plan ({max_users}). Upgrade your plan to add more users."}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        try:
            # Validate required fields
            if not data.get("username") or not data.get("email") or not data.get("password"):
                return Response({"error": "Username, email, and password are required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if username or email already exists
            if User.objects.filter(username=data["username"]).exists():
                return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(email=data["email"]).exists():
                return Response({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"]
            )
            # Make role assignment case-insensitive
            role_name = data.get("role", "staff")
            try:
                role = Role._default_manager.get(name__iexact=role_name)
            except Role._default_manager.model.DoesNotExist:
                user.delete()
                return Response({"error": f"Role '{role_name}' does not exist. Available roles: {list(Role._default_manager.values_list('name', flat=True))}"}, status=status.HTTP_400_BAD_REQUEST)
            # Prepare UserProfile data
            profile_data = {
                'user': user.id,
                'tenant': tenant.id,
                'role': role.id,
                'department': data.get('department'),
                'photo': request.FILES.get('photo'),
                'phone': data.get('phone'),
                'address': data.get('address'),
                'date_of_birth': data.get('date_of_birth'),
                'gender': data.get('gender'),
                'emergency_contact': data.get('emergency_contact'),
                'job_title': data.get('job_title'),
                'joining_date': data.get('joining_date'),
                'qualifications': data.get('qualifications'),
                'bio': data.get('bio'),
                'linkedin': data.get('linkedin'),
            }
            serializer = UserProfileSerializer(data=profile_data)
            if serializer.is_valid():
                try:
                    user_profile = UserProfile._default_manager.create(
                        user=user,
                        tenant=tenant,
                        role=role,
                        department=data.get('department'),
                        photo=request.FILES.get('photo'),
                        phone=data.get('phone'),
                        address=data.get('address'),
                        date_of_birth=data.get('date_of_birth'),
                        gender=data.get('gender'),
                        emergency_contact=data.get('emergency_contact'),
                        job_title=data.get('job_title'),
                        joining_date=data.get('joining_date'),
                        qualifications=data.get('qualifications'),
                        bio=data.get('bio'),
                        linkedin=data.get('linkedin'),
                    )
                    # Assign classes if provided (after creation)
                    class_ids = data.get("assigned_classes", [])
                    if class_ids:
                        user_profile.assigned_classes.set(class_ids)
                    return Response(UserProfileSerializer(user_profile).data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    user.delete()
                    return Response({"error": f"Failed to create user profile: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                user.delete()
                return Response({"error": f"Invalid user data: {serializer.errors}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RemoveUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        if profile.role.name != "admin":
            return Response({"error": "Only admins can remove users."}, status=status.HTTP_403_FORBIDDEN)
        username = request.data.get("username")
        try:
            user = User.objects.get(username=username)
            if user == request.user:
                return Response({"error": "You cannot remove yourself."}, status=status.HTTP_400_BAD_REQUEST)
            user.delete()
            return Response({"message": "User removed successfully."})
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class InviteUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        if profile.role.name != "admin":
            return Response({"error": "Only admins can invite users."}, status=status.HTTP_403_FORBIDDEN)
        tenant = profile.tenant
        data = request.data
        email = data.get("email")
        role_name = data.get("role", "staff")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        # Generate activation token
        token = get_random_string(32)
        # Store token in a simple way (in production, use a model)
        # For demo, send token in email
        activation_link = f"https://erp-frontend-psi-six.vercel.app/activate?email={email}&token={token}"
        send_mail(
            "You're invited to Zenith ERP",
            f"Click the link to activate your account: {activation_link}",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=True,
        )
        # In production, store token and email in a model for later verification
        return Response({"message": f"Invitation sent to {email}."})

class ActivateUserView(APIView):
    def post(self, request):
        # In production, verify token from DB
        email = request.data.get("email")
        token = request.data.get("token")
        password = request.data.get("password")
        if not all([email, token, password]):
            return Response({"error": "Missing fields."}, status=status.HTTP_400_BAD_REQUEST)
        # For demo, just create user
        try:
            user = User.objects.create_user(username=email, email=email, password=password)
            # Assign to tenant and role as needed
            return Response({"message": "Account activated. You can now log in."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            reset_link = f"https://your-frontend-url.com/reset-password?email={email}&token={token}"
            send_mail(
                "Password Reset Request",
                f"Click the link to reset your password: {reset_link}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )
            return Response({"message": "Password reset email sent."})
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class PasswordResetConfirmView(APIView):
    def post(self, request):
        email = request.data.get("email")
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        if not all([email, token, new_password]):
            return Response({"error": "Missing fields."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
            if default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({"message": "Password has been reset."})
            else:
                return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class PasswordChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        if not all([old_password, new_password]):
            return Response({"error": "Missing fields."}, status=status.HTTP_400_BAD_REQUEST)
        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        return Response({"message": "Password changed successfully."})

class UserEditView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        tenant = profile.tenant
        data = request.data.copy()
        user_id = data.get('id')
        if not user_id:
            return Response({"error": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_profile = UserProfile._default_manager.get(id=user_id, tenant=tenant)
            user = user_profile.user
            
            # Update user fields
            if data.get('username') and data['username'] != user.username:
                if User.objects.filter(username=data['username']).exclude(id=user.id).exists():
                    return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
                user.username = data['username']
            
            if data.get('email') and data['email'] != user.email:
                if User.objects.filter(email=data['email']).exclude(id=user.id).exists():
                    return Response({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)
                user.email = data['email']
            
            if data.get('first_name'):
                user.first_name = data['first_name']
            if data.get('last_name'):
                user.last_name = data['last_name']
            
            user.save()
            
            # Update profile fields
            if data.get('role'):
                try:
                    role = Role._default_manager.get(name__iexact=data['role'])
                    user_profile.role = role
                except Role._default_manager.model.DoesNotExist:
                    return Response({"error": f"Role '{data['role']}' does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Department: set to None if not provided or empty
            if 'department' in data:
                department_value = data.get('department')
                if department_value in [None, '', 'null', 'None']:
                    user_profile.department = None
                else:
                    user_profile.department_id = department_value
            if data.get('phone'):
                user_profile.phone = data['phone']
            if data.get('job_title'):
                user_profile.job_title = data['job_title']
            if data.get('is_active') is not None:
                user.is_active = data['is_active']
                user.save()

            # Update assigned_classes if provided
            if 'assigned_classes' in data or request.FILES.getlist('assigned_classes'):
                # Support both form-data and JSON
                class_ids = data.getlist('assigned_classes') if hasattr(data, 'getlist') else data.get('assigned_classes', [])
                if isinstance(class_ids, str):
                    # If sent as comma-separated string
                    class_ids = [cid.strip() for cid in class_ids.split(',') if cid.strip()]
                user_profile.assigned_classes.set(class_ids)

            user_profile.save()
            
            return Response(UserProfileSerializer(user_profile).data)
        except UserProfile._default_manager.model.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DeleteUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def delete(self, request, user_id):
        profile = UserProfile._default_manager.get(user=request.user)
        tenant = profile.tenant
        
        try:
            user_profile = UserProfile._default_manager.get(id=user_id, tenant=tenant)
            user = user_profile.user
            
            # Prevent self-deletion
            if user == request.user:
                return Response({"error": "You cannot delete yourself."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete the user (this will cascade to UserProfile)
            user.delete()
            
            return Response({"message": "User deleted successfully."}, status=status.HTTP_200_OK)
        except UserProfile._default_manager.model.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RoleListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            industry = tenant.industry.lower() if tenant else 'education'
            
            # Define industry-specific roles
            industry_roles = {
                'education': ['admin', 'staff', 'teacher', 'principal', 'accountant', 'librarian', 'student'],
                'pharmacy': ['pharmacy_admin', 'pharmacist', 'pharmacy_staff', 'pharmacy_cashier', 'pharmacy_manager', 'pharmacy_assistant'],
                'retail': ['retail_admin', 'retail_manager', 'retail_staff', 'retail_cashier', 'retail_assistant'],
                'healthcare': ['healthcare_admin', 'doctor', 'nurse', 'healthcare_staff', 'receptionist'],
                'manufacturing': ['manufacturing_admin', 'production_manager', 'quality_control', 'warehouse_manager', 'manufacturing_staff']
            }
            
            # Get roles for the current industry
            allowed_roles = industry_roles.get(industry, ['admin', 'staff'])
            
            # Filter roles based on industry
            roles = Role._default_manager.filter(name__in=allowed_roles).values_list('name', flat=True)
            
            if not roles:
                return Response({"roles": [], "error": f"No roles found for {industry} industry."}, status=200)
            
            return Response({"roles": list(roles), "industry": industry})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class IsAdminOrPrincipalForWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow safe methods for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only allow update/delete for admin or principal
        user_profile = getattr(request.user, 'userprofile', None)
        if user_profile and user_profile.role and user_profile.role.name in ['admin', 'principal']:
            return True
        return False

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated & IsAdminOrPrincipalForWrite]

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def user_me(request):
    try:
        profile = UserProfile._default_manager.get(user=request.user)
        tenant = profile.tenant
        # Determine module availability
        modules = {}
        try:
            # Plan-based modules
            plan = tenant.plan if tenant else None
            modules['education'] = bool(plan and getattr(plan, 'has_education', False))
            modules['pharmacy'] = bool(plan and getattr(plan, 'has_pharmacy', False))
            modules['retail'] = bool(plan and getattr(plan, 'has_retail', False))
            modules['healthcare'] = bool(plan and getattr(plan, 'has_healthcare', False))
            modules['hotel'] = bool(tenant and tenant.has_module('hotel'))
            modules['restaurant'] = bool(tenant and tenant.has_module('restaurant'))
            modules['salon'] = bool(tenant and tenant.has_module('salon'))
        except Exception:
            # Fallback in case of unexpected errors
            modules = {}
        data = {
            "id": profile.id,  # <--- CRITICAL: UserProfile ID
            "username": request.user.username,
            "email": request.user.email,
            "industry": tenant.industry if tenant else None,
            "role": profile.role.name if profile.role else None,
            "tenant": tenant.name if tenant else None,
            "plan": tenant.plan.name if tenant and tenant.plan else None,
            "department_id": profile.department.id if hasattr(profile, 'department') and profile.department else None,
            "modules": modules,
            # Add more fields as needed
        }
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserToggleStatusView(APIView):
    """Toggle user active status"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            print(f"Toggle status request data: {request.data}")
            user_id = request.data.get('user_id')
            is_active = request.data.get('is_active', True)
            
            if not user_id:
                return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the user
            try:
                user = User.objects.get(id=user_id)
                print(f"Found user: {user.username}, current is_active: {user.is_active}")
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Update the user's active status
            user.is_active = is_active
            user.save()
            print(f"Updated user {user.username} is_active to: {user.is_active}")
            
            return Response({
                "message": f"User {'activated' if is_active else 'deactivated'} successfully",
                "user_id": user_id,
                "is_active": is_active
            })
            
        except Exception as e:
            print(f"Error in toggle status: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST) 