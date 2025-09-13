from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from api.models.user import UserProfile
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

class FileUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        tenant = profile.tenant
        plan = tenant.plan
        if not plan:
            return Response({"error": "No plan assigned to tenant."}, status=status.HTTP_400_BAD_REQUEST)
        if tenant.storage_used_mb >= plan.storage_limit_mb:
            return Response({"error": f"Storage limit reached for your plan ({plan.storage_limit_mb} MB)."}, status=status.HTTP_403_FORBIDDEN)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        file_size_mb = file_obj.size / (1024 * 1024)
        if tenant.storage_used_mb + file_size_mb > plan.storage_limit_mb:
            return Response({"error": f"Uploading this file would exceed your storage limit ({plan.storage_limit_mb} MB)."}, status=status.HTTP_403_FORBIDDEN)
        # Save file (for demo, use default_storage and a tenant-specific path)
        path = f"tenant_{tenant.id}/{file_obj.name}"
        default_storage.save(path, file_obj)
        # Update storage usage
        tenant.storage_used_mb += file_size_mb
        tenant.save()
        return Response({"message": "File uploaded successfully.", "file": path, "storage_used_mb": tenant.storage_used_mb}, status=status.HTTP_201_CREATED) 