from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from api.models.custom_service import CustomServiceRequest
from api.serializers import CustomServiceRequestSerializer
from django.utils import timezone

class CustomServiceRequestCreateView(APIView):
    """API endpoint to create custom service requests from homepage"""
    permission_classes = [AllowAny]  # Public endpoint
    
    def post(self, request):
        serializer = CustomServiceRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Your request has been submitted successfully! We will contact you soon.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class CustomServiceRequestListView(APIView):
    """API endpoint to list all custom service requests (admin only)"""
    permission_classes = []  # Will be handled by IsAdminUser in urls
    
    def get(self, request):
        requests = CustomServiceRequest.objects.all()
        serializer = CustomServiceRequestSerializer(requests, many=True)
        return Response(serializer.data)

class CustomServiceRequestDetailView(APIView):
    """API endpoint to get/update a specific request (admin only)"""
    permission_classes = []  # Will be handled by IsAdminUser in urls
    
    def get(self, request, pk):
        try:
            service_request = CustomServiceRequest.objects.get(pk=pk)
            serializer = CustomServiceRequestSerializer(service_request)
            return Response(serializer.data)
        except CustomServiceRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request, pk):
        try:
            service_request = CustomServiceRequest.objects.get(pk=pk)
            serializer = CustomServiceRequestSerializer(service_request, data=request.data, partial=True)
            if serializer.is_valid():
                if 'status' in request.data and request.data['status'] == 'contacted' and not service_request.contacted_at:
                    service_request.contacted_at = timezone.now()
                    service_request.save(update_fields=['contacted_at'])
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CustomServiceRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

