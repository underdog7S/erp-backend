from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from api.models.communications import CommunicationThread, CommunicationMessage
from api.models.tenant_features import TenantFeatureConfig
from api.models.user import UserProfile
from api.utils.ai_utils import generate_smart_reply
import logging
import os
import requests as http_requests

logger = logging.getLogger(__name__)

# Twilio MMS and WhatsApp media messages both cap out well under this, and it
# keeps a single misclicked upload from eating a meaningful chunk of the free
# Supabase Storage tier (1GB) in one go.
MAX_ATTACHMENT_SIZE_MB = 16
ALLOWED_ATTACHMENT_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt',
    '.mp3', '.ogg', '.wav', '.m4a', '.mp4', '.mov',
}


class OmnichannelAttachmentUploadView(APIView):
    """Uploads a file to Supabase Storage for use as a message attachment.
    Separate from the reply endpoint since the file needs to be uploaded and
    have a stable URL *before* it can be attached to a Twilio MMS / WhatsApp
    media send - those APIs fetch the media from the URL themselves."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile = UserProfile.objects.get(user=request.user)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file_obj.name)[1].lower()
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            return Response({'error': f"File type '{ext}' is not allowed."}, status=status.HTTP_400_BAD_REQUEST)

        size_mb = file_obj.size / (1024 * 1024)
        if size_mb > MAX_ATTACHMENT_SIZE_MB:
            return Response({'error': f'File exceeds the {MAX_ATTACHMENT_SIZE_MB}MB limit.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from api.utils.supabase_storage import upload_file, classify_attachment
            url = upload_file(profile.tenant.id, file_obj.name, file_obj.read(), file_obj.content_type)
        except Exception as e:
            logger.error(f"Attachment upload failed: {e}")
            return Response({'error': 'Upload failed. Please try again.'}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            'url': url,
            'name': file_obj.name,
            'type': classify_attachment(file_obj.content_type, file_obj.name),
        })

class OmnichannelThreadListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            if not tenant:
                return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

            # select_related('contact') avoids a query per thread for the
            # name; bulk-fetching every message once and reducing to
            # last-message-per-thread in Python avoids the second
            # per-thread query this used to make - was a real contributor
            # to "Omnichannel Inbox takes forever to load" with more than
            # a couple of threads.
            threads = list(CommunicationThread.objects.filter(tenant=tenant).select_related('contact'))
            thread_ids = [t.id for t in threads]

            messages = CommunicationMessage.objects.filter(thread_id__in=thread_ids).order_by('created_at').values('thread_id', 'content', 'created_at')
            last_message_by_thread = {}
            for msg in messages:
                last_message_by_thread[msg['thread_id']] = msg  # last write wins, ordered ascending

            data = []
            for t in threads:
                last_msg = last_message_by_thread.get(t.id)
                data.append({
                    'id': t.id,
                    'name': t.contact.full_name if t.contact else 'Unknown Sender',
                    'lastMessage': last_msg['content'] if last_msg else 'No messages yet',
                    'time': (last_msg['created_at'] if last_msg else t.created_at).strftime('%I:%M %p'),
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
                    'channel': thread.source,
                    'attachment_url': m.attachment_url,
                    'attachment_name': m.attachment_name,
                    'attachment_type': m.attachment_type,
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
            content = request.data.get('content') or ''
            attachment_url = request.data.get('attachment_url') or None
            attachment_name = request.data.get('attachment_name') or None
            attachment_type = request.data.get('attachment_type') or None

            if not content and not attachment_url:
                return Response({'error': 'Message content or an attachment is required'}, status=status.HTTP_400_BAD_REQUEST)

            config, _ = TenantFeatureConfig.objects.get_or_create(tenant=profile.tenant)

            if thread.source == 'sms':
                if not config.is_sms_enabled:
                    return Response({'error': 'SMS is locked on your current plan.'}, status=status.HTTP_403_FORBIDDEN)
                # For managed plans (limit > 0), enforce quota. Platform/Enterprise (limit=0) = unlimited via own keys.
                if config.sms_monthly_limit > 0 and config.sms_used_this_month >= config.sms_monthly_limit:
                    return Response({'error': 'Monthly SMS limit reached. Upgrade plan.'}, status=status.HTTP_403_FORBIDDEN)
                config.sms_used_this_month += 1
                config.save()

                # --- REAL SMS DELIVERY via Twilio ---
                if config.twilio_account_sid and config.twilio_auth_token and config.twilio_phone_number:
                    try:
                        from twilio.rest import Client as TwilioClient
                        twilio = TwilioClient(config.twilio_account_sid, config.twilio_auth_token)
                        recipient_phone = thread.contact.phone if thread.contact and thread.contact.phone else None
                        if recipient_phone:
                            twilio_kwargs = {'from_': config.twilio_phone_number, 'to': recipient_phone}
                            if content:
                                twilio_kwargs['body'] = content
                            if attachment_url:
                                # MMS - Twilio fetches the media from this URL itself,
                                # so it must be publicly reachable (Supabase Storage is).
                                twilio_kwargs['media_url'] = [attachment_url]
                            twilio.messages.create(**twilio_kwargs)
                            logger.info(f"SMS sent to {recipient_phone} for tenant {profile.tenant.name}")
                        else:
                            logger.warning(f"No phone number on contact for thread {thread_id}")
                    except Exception as sms_err:
                        logger.error(f"Twilio SMS failed: {sms_err}")
                        # Don't block the message save — record it in DB regardless
                else:
                    logger.warning(f"Tenant {profile.tenant.name} has no Twilio credentials configured. Message saved to DB only.")

            elif thread.source == 'whatsapp':
                if not config.is_whatsapp_enabled:
                    return Response({'error': 'WhatsApp is locked on your current plan.'}, status=status.HTTP_403_FORBIDDEN)
                if config.whatsapp_monthly_limit > 0 and config.whatsapp_used_this_month >= config.whatsapp_monthly_limit:
                    return Response({'error': 'Monthly WhatsApp limit reached. Upgrade plan.'}, status=status.HTTP_403_FORBIDDEN)
                config.whatsapp_used_this_month += 1
                config.save()

                # --- REAL WHATSAPP DELIVERY via Meta Cloud API ---
                if config.whatsapp_phone_number_id and config.whatsapp_access_token:
                    try:
                        recipient_phone = thread.contact.phone if thread.contact and thread.contact.phone else None
                        if recipient_phone:
                            meta_url = f"https://graph.facebook.com/v18.0/{config.whatsapp_phone_number_id}/messages"
                            if attachment_url:
                                # Meta's media message types only take a caption on
                                # image/video/document, not a separate text message
                                media_key = attachment_type if attachment_type in ('image', 'video', 'audio', 'document') else 'document'
                                media_payload = {'link': attachment_url}
                                if content and media_key != 'audio':
                                    media_payload['caption'] = content
                                payload = {
                                    "messaging_product": "whatsapp",
                                    "to": recipient_phone,
                                    "type": media_key,
                                    media_key: media_payload,
                                }
                            else:
                                payload = {
                                    "messaging_product": "whatsapp",
                                    "to": recipient_phone,
                                    "type": "text",
                                    "text": {"body": content}
                                }
                            headers = {
                                "Authorization": f"Bearer {config.whatsapp_access_token}",
                                "Content-Type": "application/json"
                            }
                            resp = http_requests.post(meta_url, json=payload, headers=headers, timeout=10)
                            if resp.status_code != 200:
                                logger.error(f"Meta WhatsApp API error: {resp.status_code} {resp.text}")
                            else:
                                logger.info(f"WhatsApp sent to {recipient_phone} for tenant {profile.tenant.name}")
                        else:
                            logger.warning(f"No phone number on contact for WA thread {thread_id}")
                    except Exception as wa_err:
                        logger.error(f"Meta WhatsApp send failed: {wa_err}")
                else:
                    logger.warning(f"Tenant {profile.tenant.name} has no WhatsApp credentials. Message saved to DB only.")

            elif thread.source == 'email':
                recipient_email = thread.contact.email if thread.contact and thread.contact.email else None
                if recipient_email:
                    try:
                        from api.utils.dynamic_mailer import send_tenant_email
                        subject = f"Re: {thread.subject}" if thread.subject else f"Message from {profile.tenant.name}"
                        body = content
                        if attachment_url:
                            body = f"{body}\n\nAttachment: {attachment_url}" if body else f"Attachment: {attachment_url}"
                        send_tenant_email(
                            tenant=profile.tenant,
                            subject=subject,
                            message=body,
                            recipient_list=[recipient_email],
                        )
                        logger.info(f"Email sent to {recipient_email} for tenant {profile.tenant.name}")
                    except Exception as email_err:
                        logger.error(f"Tenant email send failed: {email_err}")
                else:
                    logger.warning(f"No email address on contact for thread {thread_id}")

            msg = CommunicationMessage.objects.create(
                thread=thread,
                sender_type='agent',
                agent=request.user,
                content=content,
                attachment_url=attachment_url,
                attachment_name=attachment_name,
                attachment_type=attachment_type,
            )

            return Response({
                'id': msg.id,
                'text': msg.content,
                'sender': 'agent',
                'time': msg.created_at.strftime('%I:%M %p'),
                'channel': thread.source,
                'attachment_url': msg.attachment_url,
                'attachment_name': msg.attachment_name,
                'attachment_type': msg.attachment_type,
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
            
            config, _ = TenantFeatureConfig.objects.get_or_create(tenant=profile.tenant)
            if not config.is_ai_enabled:
                return Response({'error': 'AI services are locked on your current plan.'}, status=status.HTTP_403_FORBIDDEN)
            if config.ai_tokens_used_this_month >= config.ai_tokens_monthly_limit:
                return Response({'error': 'Monthly AI Token limit reached. Upgrade plan.'}, status=status.HTTP_403_FORBIDDEN)
            
            suggestion = generate_smart_reply(thread)
            
            if suggestion:
                # Simulate using 50 tokens per reply generation
                config.ai_tokens_used_this_month += 50
                config.save()
                return Response({'suggestion': suggestion})
                
            return Response({'error': 'AI failed to generate suggestion'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except CommunicationThread.DoesNotExist:
            return Response({'error': 'Thread not found'}, status=status.HTTP_404_NOT_FOUND)
