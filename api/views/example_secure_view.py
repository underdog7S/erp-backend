"""
Example of a secure view implementation with audit logging
This demonstrates best practices for security in your API views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.audit import AuditLog
from api.utils.security import sanitize_string, validate_email, validate_amount
from api.models.permissions import role_required
from api.models.user import UserProfile

class SecureExampleView(APIView):
    """
    Example view showing security best practices
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @role_required('admin', 'principal')
    def post(self, request):
        """
        Example secure POST endpoint
        """
        try:
            # 1. Get user profile
            profile = UserProfile._default_manager.get(user=request.user)
            
            # 2. Sanitize and validate input
            email = request.data.get('email')
            if email:
                email = validate_email(email)
            
            name = request.data.get('name')
            if name:
                name = sanitize_string(name, max_length=100)
            
            amount = request.data.get('amount')
            if amount:
                amount = validate_amount(amount, min_value=0, max_value=1000000)
            
            # 3. Perform business logic
            # ... your code here ...
            
            # 4. Log successful action
            AuditLog.log_action(
                request=request,
                action='CREATE',
                resource_type='Example',
                resource_name=name,
                success=True,
                description=f'Created new example resource: {name}',
                request_data=request.data
            )
            
            return Response({'message': 'Success'}, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # 5. Log failed action
            AuditLog.log_action(
                request=request,
                action='CREATE',
                resource_type='Example',
                success=False,
                description='Failed to create example resource',
                error_message=str(e),
                request_data=request.data
            )
            
            # 6. Return safe error message (don't expose internals)
            return Response(
                {'error': 'Failed to process request. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )

