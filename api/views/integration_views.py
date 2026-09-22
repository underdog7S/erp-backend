from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
from api.models.tenant_features import TenantFeatureConfig

class TenantIntegrationSettingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        config, _ = TenantFeatureConfig.objects.get_or_create(tenant=profile.tenant)
        
        # SECURITY: Never expose raw secrets to the browser. Return masked flags instead.
        # Frontend uses `has_*` booleans to show "✓ Configured" vs empty state.
        return Response({
            # Twilio — masked
            'twilio_account_sid': config.twilio_account_sid or '',
            'twilio_auth_token': '••••••••' if config.twilio_auth_token else '',
            'twilio_phone_number': config.twilio_phone_number or '',
            'has_twilio': bool(config.twilio_account_sid and config.twilio_auth_token),
            # Meta WhatsApp — masked
            'whatsapp_phone_number_id': config.whatsapp_phone_number_id or '',
            'whatsapp_access_token': '••••••••' if config.whatsapp_access_token else '',
            'has_whatsapp': bool(config.whatsapp_phone_number_id and config.whatsapp_access_token),
            # Telegram — masked
            'telegram_bot_token': '••••••••' if config.telegram_bot_token else '',
            'telegram_chat_id': config.telegram_chat_id or '',
            # AWS — masked
            'aws_access_key_id': config.aws_access_key_id or '',
            'aws_secret_access_key': '••••••••' if config.aws_secret_access_key else '',
            'aws_region': config.aws_region or 'ap-south-1',
            # SMTP — masked password only
            'smtp_host': config.smtp_host or '',
            'smtp_port': config.smtp_port or 587,
            'smtp_username': config.smtp_username or '',
            'smtp_password': '••••••••' if config.smtp_password else '',
            'smtp_use_tls': config.smtp_use_tls,
            'has_smtp': bool(config.smtp_host and config.smtp_username and config.smtp_password),
            # OpenAI — masked
            'openai_api_key': '••••••••' if config.openai_api_key else '',
            'has_openai': bool(config.openai_api_key),
        })

    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        config, _ = TenantFeatureConfig.objects.get_or_create(tenant=profile.tenant)
        
        data = request.data
        MASKED = '••••••••'
        
        if 'twilio_account_sid' in data:
            config.twilio_account_sid = data['twilio_account_sid']
        if 'twilio_auth_token' in data and data['twilio_auth_token'] != MASKED:
            config.twilio_auth_token = data['twilio_auth_token']
        if 'twilio_phone_number' in data:
            config.twilio_phone_number = data['twilio_phone_number']
            
        if 'whatsapp_phone_number_id' in data:
            config.whatsapp_phone_number_id = data['whatsapp_phone_number_id']
        if 'whatsapp_access_token' in data and data['whatsapp_access_token'] != MASKED:
            config.whatsapp_access_token = data['whatsapp_access_token']
            
        if 'telegram_bot_token' in data and data['telegram_bot_token'] != MASKED:
            config.telegram_bot_token = data['telegram_bot_token']
        if 'telegram_chat_id' in data:
            config.telegram_chat_id = data['telegram_chat_id']
            
        if 'aws_access_key_id' in data:
            config.aws_access_key_id = data['aws_access_key_id']
        if 'aws_secret_access_key' in data and data['aws_secret_access_key'] != MASKED:
            config.aws_secret_access_key = data['aws_secret_access_key']
        if 'aws_region' in data:
            config.aws_region = data['aws_region']
            
        if 'smtp_host' in data:
            config.smtp_host = data['smtp_host']
        if 'smtp_port' in data:
            config.smtp_port = data['smtp_port']
        if 'smtp_username' in data:
            config.smtp_username = data['smtp_username']
        if 'smtp_password' in data and data['smtp_password'] != MASKED:
            config.smtp_password = data['smtp_password']
        if 'smtp_use_tls' in data:
            config.smtp_use_tls = data['smtp_use_tls']
        
        if 'openai_api_key' in data and data['openai_api_key'] != MASKED:
            config.openai_api_key = data['openai_api_key']
            
        config.save()
        
        return Response({'status': 'Integrations updated successfully'})
