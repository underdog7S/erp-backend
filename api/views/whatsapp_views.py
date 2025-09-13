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
		Requires env WHATSAPP_TOKEN and WHATSAPP_PHONE_ID
		"""
		try:
			profile = UserProfile.objects.get(user=request.user)
			if not profile.role or profile.role.name not in ['admin', 'pharmacy_admin', 'retail_admin']:
				return Response({'error': 'Admin access required'}, status=403)
			to = request.data.get('to')
			message = request.data.get('message')
			if not to or not message:
				return Response({'error': 'to and message are required'}, status=400)
			token = os.getenv('WHATSAPP_TOKEN')
			phone_id = os.getenv('WHATSAPP_PHONE_ID')
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
			return Response({'message': 'Sent', 'whatsapp_response': resp.json()})
		except Exception as e:
			return Response({'error': str(e)}, status=400)

