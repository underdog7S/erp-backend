import os
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
import requests


class WhatsAppSendView(APIView):
	authentication_classes = [JWTAuthentication]
	permission_classes = [IsAuthenticated]

	def post(self, request):
		"""Send a manual WhatsApp text message using WhatsApp Cloud API.
		Payload: { to: "+1234567890", message: "text..." }
		"""
		try:
			profile = UserProfile.objects.get(user=request.user)
			if not profile.role or profile.role.name not in ['admin', 'pharmacy_admin', 'retail_admin']:
				return Response({'error': 'Admin access required'}, status=403)
			to = request.data.get('to')
			message = request.data.get('message')
			if not to or not message:
				return Response({'error': 'to and message are required'}, status=400)
			
			# --- SAAS BILLING & QUOTA CHECK ---
			from api.models.tenant_features import TenantFeatureConfig
			config, _ = TenantFeatureConfig.objects.get_or_create(tenant=profile.tenant)
			
			if not config.is_whatsapp_enabled:
				return Response({'error': 'WhatsApp API is locked for this tenant. Please upgrade your plan.'}, status=403)
				
			if config.whatsapp_used_this_month >= config.whatsapp_monthly_limit:
				return Response({'error': 'WhatsApp monthly quota exceeded. Please buy an add-on.'}, status=402) # Payment required

			# Prefer Tenant's custom token, fallback to Master Token
			token = config.whatsapp_access_token or os.getenv('WHATSAPP_TOKEN')
			phone_id = config.whatsapp_phone_number_id or os.getenv('WHATSAPP_PHONE_ID')
			if not token or not phone_id:
				return Response({'error': 'WhatsApp not configured'}, status=501)
			url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
			headers = {
				'Authorization': f'Bearer {token}',
				'Content-Type': 'application/json'
			}
			payload = {
				'messaging_product': 'whatsapp',
				'to': to,
				'type': 'text',
				'text': { 'body': message }
			}
			resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
			if resp.status_code >= 400:
				return Response({'error': 'WhatsApp API error', 'details': resp.text}, status=502)
			config.whatsapp_used_this_month += 1
			config.save(update_fields=['whatsapp_used_this_month'])
			
			return Response({'message': 'Sent', 'whatsapp_response': resp.json()})
		except Exception as e:
			return Response({'error': str(e)}, status=400)



from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(APIView):
    permission_classes = [AllowAny]  # Webhooks come from Meta, no JWT auth

    def get(self, request):
        """
        Meta Webhook Verification.
        When setting up the webhook in the Meta Developer Dashboard,
        Meta sends a GET request with hub.mode, hub.challenge, and hub.verify_token.
        """
        verify_token = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "zenverse_secure_webhook_123")
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == verify_token:
                from django.http import HttpResponse
                return HttpResponse(challenge, status=200)
            else:
                return Response({'error': 'Verification failed'}, status=403)
        return Response({'error': 'Invalid request'}, status=400)

    def post(self, request):
        """
        Receives incoming WhatsApp messages from customers.
        """
        try:
            data = request.data
            
            # Basic validation of WhatsApp webhook payload
            if data.get("object") == "whatsapp_business_account":
                for entry in data.get("entry", []):
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        
                        # Check if this is a new message
                        if "messages" in value:
                            for msg in value["messages"]:
                                sender_phone = msg.get("from")
                                message_text = msg.get("text", {}).get("body", "")
                                message_id = msg.get("id")

                                # Meta includes the sender's WhatsApp display
                                # name alongside the message, keyed by phone
                                sender_name = None
                                for c in value.get("contacts", []):
                                    if c.get("wa_id") == sender_phone:
                                        sender_name = c.get("profile", {}).get("name")
                                        break

                                # Find the business phone number ID this was sent to
                                recipient_phone_id = value.get("metadata", {}).get("phone_number_id")
                                
                                # --- SAAS & AI AUTO-RESPONDER LOGIC ---
                                from api.models.tenant_features import TenantFeatureConfig
                                from api.models.communications import CommunicationThread, CommunicationMessage
                                from api.utils.ai_utils import generate_smart_reply
                                
                                print(f"📞 Incoming WhatsApp from {sender_phone}: {message_text}")
                                
                                # 1. Find Tenant by the WhatsApp Phone Number ID they connected
                                config = TenantFeatureConfig.objects.filter(whatsapp_phone_number_id=recipient_phone_id).first()
                                
                                if config and config.tenant:
                                    tenant = config.tenant
                                    
                                    # 2. Find or create the Chat Thread for this customer
                                    thread, _ = CommunicationThread.objects.get_or_create(
                                        tenant=tenant,
                                        source='whatsapp',
                                        external_thread_id=sender_phone
                                    )
                                    if not thread.contact:
                                        from api.utils.contact_utils import get_or_create_contact
                                        thread.contact = get_or_create_contact(tenant, phone=sender_phone, name=sender_name)
                                    thread.has_unread = True
                                    thread.save()
                                    
                                    # 3. Save incoming message to database
                                    CommunicationMessage.objects.create(
                                        thread=thread,
                                        sender_type='client',
                                        content=message_text,
                                        external_message_id=message_id
                                    )

                                    from api.utils.notification_utils import notify_new_inbound_message
                                    notify_new_inbound_message(tenant, 'whatsapp', sender_phone, message_text)

                                    # 4. Trigger AI Auto-Responder if enabled
                                    if config.is_ai_enabled and config.ai_tokens_used_this_month < config.ai_tokens_monthly_limit:
                                        # Get AI response
                                        ai_reply = generate_smart_reply(thread)

                                        if ai_reply:
                                            # Save AI's reply to database
                                            CommunicationMessage.objects.create(
                                                thread=thread,
                                                sender_type='ai',
                                                content=ai_reply
                                            )

                                            # Send reply back via Meta WhatsApp API
                                            import requests, json, os
                                            token = config.whatsapp_access_token or os.getenv('WHATSAPP_TOKEN')
                                            url = f"https://graph.facebook.com/v17.0/{recipient_phone_id}/messages"
                                            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                                            payload = {'messaging_product': 'whatsapp', 'to': sender_phone, 'type': 'text', 'text': {'body': ai_reply}}
                                            requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)

                                            # Increment WhatsApp usage bill
                                            config.whatsapp_used_this_month += 1
                                            config.save(update_fields=['whatsapp_used_this_month'])
                                        else:
                                            print(f"⚠️ AI auto-reply failed for thread {thread.id}; no reply sent to {sender_phone}")
                                
                return Response("EVENT_RECEIVED", status=200)
            return Response(status=404)
        except Exception as e:
            print(f"Webhook Error: {e}")
            return Response(status=500)
