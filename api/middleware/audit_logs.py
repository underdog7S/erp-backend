import json
import logging
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from api.models.audit_logs import AuditLog

logger = logging.getLogger(__name__)

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # Log the action
        self.log_action(request, response)
        
        return response

    def log_action(self, request, response):
        try:
            # Skip logging for certain paths
            skip_paths = ['/static/', '/media/', '/admin/jsi18n/', '/favicon.ico']
            if any(path in request.path for path in skip_paths):
                return

            # Get user info
            user = request.user
            if isinstance(user, AnonymousUser):
                return

            # Get tenant info
            tenant = None
            if hasattr(user, 'userprofile') and user.userprofile.tenant:
                tenant = user.userprofile.tenant

            # Determine action type
            action_type = self.get_action_type(request)
            
            # Get request data (sanitized)
            request_data = self.sanitize_request_data(request)
            
            # Get response status
            status_code = response.status_code

            # Create audit log entry
            AuditLog.objects.create(
                user=user,
                tenant=tenant,
                action_type=action_type,
                resource_type=self.get_resource_type(request.path),
                resource_id=self.get_resource_id(request.path),
                request_method=request.method,
                request_path=request.path,
                request_data=request_data,
                response_status=status_code,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                timestamp=timezone.now()
            )

        except Exception as e:
            logger.error(f"Error logging audit: {str(e)}")

    def get_action_type(self, request):
        """Determine the type of action being performed"""
        method = request.method
        path = request.path.lower()
        
        if method == 'GET':
            return 'VIEW'
        elif method == 'POST':
            if 'create' in path or 'add' in path:
                return 'CREATE'
            elif 'login' in path:
                return 'LOGIN'
            elif 'logout' in path:
                return 'LOGOUT'
            else:
                return 'UPDATE'
        elif method == 'PUT' or method == 'PATCH':
            return 'UPDATE'
        elif method == 'DELETE':
            return 'DELETE'
        else:
            return 'OTHER'

    def get_resource_type(self, path):
        """Extract resource type from URL path"""
        path_parts = path.strip('/').split('/')
        if len(path_parts) >= 2:
            return path_parts[1].upper()  # e.g., 'manufacturing', 'education', 'healthcare'
        return 'UNKNOWN'

    def get_resource_id(self, path):
        """Extract resource ID from URL path if present"""
        path_parts = path.strip('/').split('/')
        if len(path_parts) >= 3 and path_parts[2].isdigit():
            return int(path_parts[2])
        return None

    def sanitize_request_data(self, request):
        """Sanitize sensitive data from request"""
        data = {}
        
        # Get data from different sources
        if request.method == 'GET':
            data = dict(request.GET)
        elif request.method in ['POST', 'PUT', 'PATCH']:
            data = dict(request.POST)
            # Also get JSON data if present
            if request.content_type == 'application/json':
                try:
                    json_data = json.loads(request.body.decode('utf-8'))
                    data.update(json_data)
                except:
                    pass

        # Remove sensitive fields
        sensitive_fields = ['password', 'token', 'secret', 'key', 'authorization']
        sanitized_data = {}
        
        for key, value in data.items():
            if not any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized_data[key] = value

        return sanitized_data

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 