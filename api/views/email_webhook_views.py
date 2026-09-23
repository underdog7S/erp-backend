import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from api.models.tenant_features import TenantFeatureConfig
from api.models.communications import CommunicationThread, CommunicationMessage
from api.utils.ai_utils import generate_smart_reply

@method_decorator(csrf_exempt, name='dispatch')
class EmailWebhookView(APIView):
    """
    Receives incoming emails via SendGrid Inbound Parse or similar webhook.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # SendGrid sends data as multipart/form-data
            data = request.data
            
            sender_email = data.get('from', '')
            recipient_email = data.get('to', '')
            subject = data.get('subject', 'No Subject')
            text_body = data.get('text', '')
            
            # Clean up sender format like "Name <email@domain.com>"
            import re
            sender_match = re.search(r'<(.+?)>', sender_email)
            if sender_match:
                sender_email = sender_match.group(1)
                
            recipient_match = re.search(r'<(.+?)>', recipient_email)
            if recipient_match:
                recipient_email = recipient_match.group(1)
            
            # 1. Find Tenant by the recipient email domain
            # E.g., if recipient is info@theirsalon.com, find config with custom_domain='theirsalon.com'
            domain = recipient_email.split('@')[-1] if '@' in recipient_email else ''
            config = TenantFeatureConfig.objects.filter(custom_domain__icontains=domain).first()
            
            if config and config.tenant:
                tenant = config.tenant
                
                # 2. Find or create the Chat Thread for this customer email
                thread, _ = CommunicationThread.objects.get_or_create(
                    tenant=tenant,
                    source='email',
                    external_thread_id=sender_email
                )
                if not thread.contact:
                    from api.utils.contact_utils import get_or_create_contact
                    thread.contact = get_or_create_contact(tenant, email=sender_email)
                thread.has_unread = True
                thread.subject = subject
                thread.save()
                
                # 3. Save incoming message to database
                new_msg = CommunicationMessage.objects.create(
                    thread=thread,
                    sender_type='client',
                    content=text_body,
                )
                
                # Broadcast to WebSocket
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                
                channel_layer = get_channel_layer()
                if channel_layer:
                    room_name = f'inbox_{tenant.slug if tenant.slug else tenant.id}'
                    async_to_sync(channel_layer.group_send)(
                        room_name,
                        {
                            'type': 'new_message',
                            'message_data': {
                                'id': new_msg.id,
                                'thread_id': thread.id,
                                'text': new_msg.content,
                                'sender': new_msg.sender_type,
                                'source': thread.source,
                                'thread_name': thread.contact.full_name if thread.contact else str(thread.external_thread_id)
                            }
                        }
                    )
                
                # 4. Trigger AI Auto-Responder if enabled
                if config.is_ai_enabled and config.ai_tokens_used_this_month < config.ai_tokens_monthly_limit:
                    ai_reply = generate_smart_reply(thread)

                    if ai_reply:
                        ai_msg = CommunicationMessage.objects.create(
                            thread=thread,
                            sender_type='ai',
                            content=ai_reply
                        )

                        if channel_layer:
                            async_to_sync(channel_layer.group_send)(
                                room_name,
                                {
                                    'type': 'new_message',
                                    'message_data': {
                                        'id': ai_msg.id,
                                        'thread_id': thread.id,
                                        'text': ai_msg.content,
                                        'sender': ai_msg.sender_type,
                                        'source': thread.source,
                                        'thread_name': thread.contact.full_name if thread.contact else str(thread.external_thread_id)
                                    }
                                }
                            )

                        # Send email back via the tenant's own SMTP (BYOK) if
                        # configured, falling back to the platform's sender
                        from api.utils.dynamic_mailer import send_tenant_email
                        send_tenant_email(
                            tenant=tenant,
                            subject=f"Re: {subject}",
                            message=ai_reply,
                            recipient_list=[sender_email],
                        )
                    
            return Response("OK", status=200)
        except Exception as e:
            print(f"Email Webhook Error: {e}")
            return Response("Error", status=500)
