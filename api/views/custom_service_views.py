from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from api.models.custom_service import CustomServiceRequest
from api.serializers import CustomServiceRequestSerializer
from django.utils import timezone
from django.conf import settings
import requests
import threading

def send_telegram_notification(data):
    """Background task to send Telegram notification for new leads"""
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
    
    if not bot_token or not chat_id:
        return
        
    message = f"""🚀 *New Expert Meeting Request!* 🚀

👤 *Name:* {data.get('name')}
🏢 *Company:* {data.get('company_name', 'N/A')}
📞 *Phone:* {data.get('phone')}
✉️ *Email:* {data.get('email')}
🛠 *Service:* {data.get('service_type')}
💰 *Budget:* {data.get('budget_range', 'N/A')}
📅 *Timeline:* {data.get('timeline', 'N/A')}

📝 *Description:*
{data.get('description', '')}"""
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send telegram notification: {e}")


class CustomServiceRequestCreateView(APIView):
    """API endpoint to create custom service requests from homepage"""
    permission_classes = [AllowAny]  # Public endpoint
    
    def post(self, request):
        serializer = CustomServiceRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            
            # Send Telegram notification in background to not block response
            threading.Thread(target=send_telegram_notification, args=(serializer.data,)).start()
            
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
    # An empty list here would leave the endpoint completely open (DRF's
    # default permission classes are only applied when this attribute is
    # unset) - the "handled in urls" comment was never actually true since
    # urls.py wires these views with plain .as_view(), no wrapper.
    permission_classes = [IsAdminUser]

    def get(self, request):
        requests = CustomServiceRequest.objects.all()
        serializer = CustomServiceRequestSerializer(requests, many=True)
        return Response(serializer.data)

class CustomServiceRequestDetailView(APIView):
    """API endpoint to get/update a specific request (admin only)"""
    permission_classes = [IsAdminUser]
    
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

