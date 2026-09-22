import logging
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
                    thread.has_unread = True
                    thread.save()

                    CommunicationMessage.objects.create(
                        thread=thread,
                        sender_type='client',
                        content=message_text,
                        external_message_id=message_sid
                    )

                    if config.is_ai_enabled and config.ai_tokens_used_this_month < config.ai_tokens_monthly_limit:
                        ai_reply = generate_smart_reply(thread)

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
                    logger.warning(f"No tenant found for Twilio number {recipient_phone}")

            # Twilio expects a valid TwiML response (even if empty) - a bare
            # 200 with a non-TwiML body can show as an error in their console.
            return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', content_type='text/xml')
        except Exception as e:
            logger.error(f"Twilio webhook error: {e}")
            return Response(status=500)
