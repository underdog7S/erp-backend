from django.db import models
from .user import Tenant

class TenantFeatureConfig(models.Model):
    """
    Manages SaaS feature toggles, API keys, and usage quotas for a Tenant.
    """
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="feature_config")
    
    # 0. Managed Telecom Assets (White-Glove Fulfillment)
    managed_phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="The dedicated Twilio/Meta number you purchased for this tenant")
    managed_email_address = models.CharField(max_length=100, blank=True, null=True, help_text="The dedicated support email (e.g., info@tenant-domain.com)")
    
    # 1. Custom Domain & Email
    custom_domain = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., mail.theirsalon.com")
    is_custom_email_enabled = models.BooleanField(default=False)
    
    # BYOK Email (SMTP)
    smtp_host = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., smtp.gmail.com")
    smtp_port = models.IntegerField(blank=True, null=True, help_text="e.g., 587 or 465")
    smtp_username = models.CharField(max_length=255, blank=True, null=True)
    smtp_password = models.CharField(max_length=255, blank=True, null=True, help_text="App Password")
    smtp_use_tls = models.BooleanField(default=True)
    
    # 2. SMS Configuration (Managed by Master Account)
    is_sms_enabled = models.BooleanField(default=False)
    sms_used_this_month = models.IntegerField(default=0)
    sms_monthly_limit = models.IntegerField(default=0)

    # BYOK SMS (Twilio)
    twilio_account_sid = models.CharField(max_length=255, blank=True, null=True)
    twilio_auth_token = models.CharField(max_length=255, blank=True, null=True)
    twilio_phone_number = models.CharField(max_length=50, blank=True, null=True)

    # BYOK SMS (AWS SNS)
    aws_access_key_id = models.CharField(max_length=255, blank=True, null=True)
    aws_secret_access_key = models.CharField(max_length=255, blank=True, null=True)
    aws_region = models.CharField(max_length=50, blank=True, null=True, default='ap-south-1')

    
    # 3. WhatsApp Cloud API (Meta Embedded Signup)
    is_whatsapp_enabled = models.BooleanField(default=False)
    whatsapp_access_token = models.CharField(max_length=500, blank=True, null=True, help_text="OAuth token from Meta")
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_waba_id = models.CharField(max_length=100, blank=True, null=True, help_text="WhatsApp Business Account ID")
    whatsapp_used_this_month = models.IntegerField(default=0)
    whatsapp_monthly_limit = models.IntegerField(default=0)
    
    # 4. OpenAI Integration (Managed by Master Account)
    is_ai_enabled = models.BooleanField(default=False)
    ai_tokens_used_this_month = models.IntegerField(default=0)
    ai_tokens_monthly_limit = models.IntegerField(default=0)
    
    # BYOK OpenAI key — Pro/Enterprise/Platform tenants can bring their own
    openai_api_key = models.CharField(max_length=255, blank=True, null=True, help_text="BYOK OpenAI API key (sk-proj-...)")

    # BYOK AI provider selection — which provider's key to actually use for AI replies
    AI_PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('azure_openai', 'Azure OpenAI'),
        ('gemini', 'Google Gemini'),
        ('claude', 'Anthropic Claude'),
    ]
    ai_provider = models.CharField(max_length=20, choices=AI_PROVIDER_CHOICES, default='openai', help_text="Which AI provider to use for AI Auto-Responder replies")

    # BYOK Azure OpenAI
    azure_openai_api_key = models.CharField(max_length=255, blank=True, null=True)
    azure_openai_endpoint = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., https://your-resource.openai.azure.com/")
    azure_openai_deployment_name = models.CharField(max_length=100, blank=True, null=True, help_text="Your deployed model's name, e.g., gpt-4o-mini")

    # BYOK Google Gemini
    gemini_api_key = models.CharField(max_length=255, blank=True, null=True)
    gemini_model = models.CharField(max_length=100, blank=True, null=True, default='gemini-1.5-flash')

    # BYOK Anthropic Claude
    claude_api_key = models.CharField(max_length=255, blank=True, null=True)
    claude_model = models.CharField(max_length=100, blank=True, null=True, default='claude-3-5-sonnet-latest')

    # 5. Telegram Integration (Optional BYOK for small tenants)
    is_telegram_enabled = models.BooleanField(default=False)
    telegram_bot_token = models.CharField(max_length=255, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.name} - Feature Config"
