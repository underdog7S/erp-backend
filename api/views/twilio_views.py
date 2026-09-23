import logging
import requests as http_requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TwilioSMSWebhookView(APIView):
    """Receives incoming SMS replies from customers via Twilio.

    Configure this URL as the "A MESSAGE COMES IN" webhook on the tenant's
    Twilio phone number (Twilio Console -> Phone Numbers -> your number ->
    Messaging configuration). Twilio POSTs form-encoded fields, not JSON.
    """
    permission_classes = [AllowAny]  # Webhook comes from Twilio, no JWT auth
    authentication_classes = []

    def post(self, request):
        try:
            sender_phone = request.data.get('From')
            recipient_phone = request.data.get('To')
            message_text = request.data.get('Body', '')
            message_sid = request.data.get('MessageSid')

            if sender_phone and recipient_phone:
                from api.models.tenant_features import TenantFeatureConfig
                from api.models.communications import CommunicationThread, CommunicationMessage
                from api.utils.ai_utils import generate_smart_reply

                logger.info(f"Incoming SMS from {sender_phone} to {recipient_phone}")

                # Find the tenant that owns this Twilio number
                config = TenantFeatureConfig.objects.filter(twilio_phone_number=recipient_phone).first()

                if config and config.tenant:
                    tenant = config.tenant

                    thread, _ = CommunicationThread.objects.get_or_create(
                        tenant=tenant,
                        source='sms',
                        external_thread_id=sender_phone
                    )
                    if not thread.contact:
                        from api.utils.contact_utils import get_or_create_contact
                        thread.contact = get_or_create_contact(tenant, phone=sender_phone)
                    thread.has_unread = True
                    thread.save()

                    # MMS - Twilio's own MediaUrl expires after a while, so
                    # re-host it in Supabase Storage for a durable link
                    # (same reasoning as outbound attachments).
                    attachment_url = attachment_name = attachment_type = None
                    num_media = int(request.data.get('NumMedia', 0) or 0)
                    if num_media > 0:
                        media_source_url = request.data.get('MediaUrl0')
                        media_content_type = request.data.get('MediaContentType0', '')
                        try:
                            media_resp = http_requests.get(
                                media_source_url,
                                auth=(config.twilio_account_sid, config.twilio_auth_token),
                                timeout=15,
                            )
                            if media_resp.status_code == 200:
                                import mimetypes
                                from api.utils.supabase_storage import upload_file, classify_attachment
                                ext = mimetypes.guess_extension(media_content_type.split(';')[0].strip()) or ''
                                attachment_name = f"mms-media{ext}"
                                attachment_url = upload_file(tenant.id, attachment_name, media_resp.content, media_content_type)
                                attachment_type = classify_attachment(media_content_type, attachment_name)
                        except Exception as media_err:
                            logger.error(f"Failed to re-host inbound MMS media: {media_err}")

                    CommunicationMessage.objects.create(
                        thread=thread,
                        sender_type='client',
                        content=message_text,
                        external_message_id=message_sid,
                        attachment_url=attachment_url,
                        attachment_name=attachment_name,
                        attachment_type=attachment_type,
                    )

                    from api.utils.notification_utils import notify_new_inbound_message
                    notify_new_inbound_message(tenant, 'sms', sender_phone, message_text)

                    if config.is_ai_enabled and config.ai_tokens_used_this_month < config.ai_tokens_monthly_limit:
                        ai_reply = generate_smart_reply(thread)

                        if ai_reply:
                            CommunicationMessage.objects.create(
                                thread=thread,
                                sender_type='ai',
                                content=ai_reply
                            )

                            if config.twilio_account_sid and config.twilio_auth_token:
                                try:
                                    from twilio.rest import Client as TwilioClient
                                    twilio_client = TwilioClient(config.twilio_account_sid, config.twilio_auth_token)
                                    twilio_client.messages.create(
                                        body=ai_reply,
                                        from_=recipient_phone,
                                        to=sender_phone
                                    )
                                except Exception as sms_err:
                                    logger.error(f"Twilio AI auto-reply send failed: {sms_err}")

                            if config.sms_monthly_limit == 0 or config.sms_used_this_month < config.sms_monthly_limit:
                                config.sms_used_this_month += 1
                                config.save(update_fields=['sms_used_this_month'])
                        else:
                            logger.warning(f"AI auto-reply failed for thread {thread.id}; no reply sent to {sender_phone}")
                else:
                    logger.warning(f"No tenant found for Twilio number {recipient_phone}")

            # Twilio expects a valid TwiML response (even if empty) - a bare
            # 200 with a non-TwiML body can show as an error in their console.
            return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', content_type='text/xml')
        except Exception as e:
            logger.error(f"Twilio webhook error: {e}")
            return Response(status=500)
