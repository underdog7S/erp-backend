from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from api.models.communications import CommunicationThread, CommunicationMessage
from api.models.user import UserProfile
from api.utils.ai_utils import generate_smart_reply
import logging

logger = logging.getLogger(__name__)

class OmnichannelThreadListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            if not tenant:
                return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

            threads = CommunicationThread.objects.filter(tenant=tenant)
            
            # Format for the frontend UI
            data = []
            for t in threads:
                last_msg = t.messages.order_by('-created_at').first()
                data.append({
                    'id': t.id,
                    'name': t.contact.full_name if t.contact else 'Unknown Sender',
                    'lastMessage': last_msg.content if last_msg else 'No messages yet',
                    'time': last_msg.created_at.strftime('%I:%M %p') if last_msg else t.created_at.strftime('%I:%M %p'),
                    'source': t.source,
                    'unread': 1 if t.has_unread else 0
                })
                
            return Response(data)
        except Exception as e:
            logger.error(f"Error fetching threads: {str(e)}")
            return Response({'error': 'Failed to fetch threads'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OmnichannelMessageListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, thread_id):
        try:
            profile = UserProfile.objects.get(user=request.user)
            thread = CommunicationThread.objects.get(id=thread_id, tenant=profile.tenant)
            
            # Mark read
            thread.has_unread = False
            thread.save()

            messages = thread.messages.all().order_by('created_at')
            
            data = []
            for m in messages:
                data.append({
                    'id': m.id,
                    'text': m.content,
                    'sender': m.sender_type,  # 'client', 'agent', 'ai'
                    'time': m.created_at.strftime('%I:%M %p'),
                    'channel': thread.source
                })
                
            return Response(data)
        except CommunicationThread.DoesNotExist:
            return Response({'error': 'Thread not found'}, status=status.HTTP_404_NOT_FOUND)


class OmnichannelReplyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        try:
            profile = UserProfile.objects.get(user=request.user)
            thread = CommunicationThread.objects.get(id=thread_id, tenant=profile.tenant)
            content = request.data.get('content')
            
            if not content:
                return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Save the agent's reply
            msg = CommunicationMessage.objects.create(
                thread=thread,
                sender_type='agent',
                agent=request.user,
                content=content
            )
            
            # Here we would normally trigger Celery to actually dispatch the SMS/WhatsApp/Email
            # For now, we just simulate the dispatch success.
            
            return Response({
                'id': msg.id,
                'text': msg.content,
                'sender': 'agent',
                'time': msg.created_at.strftime('%I:%M %p'),
                'channel': thread.source
            })
        except CommunicationThread.DoesNotExist:
            return Response({'error': 'Thread not found'}, status=status.HTTP_404_NOT_FOUND)


class OmnichannelAiSuggestView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, thread_id):
        try:
            profile = UserProfile.objects.get(user=request.user)
            thread = CommunicationThread.objects.get(id=thread_id, tenant=profile.tenant)
            
            # Use our existing ai_utils smart reply generator
            suggestion = generate_smart_reply(thread)
            
            if suggestion:
                return Response({'suggestion': suggestion})
            return Response({'error': 'AI failed to generate suggestion'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except CommunicationThread.DoesNotExist:
            return Response({'error': 'Thread not found'}, status=status.HTTP_404_NOT_FOUND)
