from django.db import models
from .user import Tenant

class TenantFeatureConfig(models.Model):
    """
    Manages SaaS feature toggles, API keys, and usage quotas for a Tenant.
    """
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="feature_config")
    
    # 1. Custom Domain & Email
    custom_domain = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., mail.theirsalon.com")
    is_custom_email_enabled = models.BooleanField(default=False)
    
    # 2. SMS Configuration (Managed by Master Account)
    is_sms_enabled = models.BooleanField(default=False)
    sms_used_this_month = models.IntegerField(default=0)
    sms_monthly_limit = models.IntegerField(default=500)
    
    # 3. WhatsApp Cloud API (Meta Embedded Signup)
    is_whatsapp_enabled = models.BooleanField(default=False)
    whatsapp_access_token = models.CharField(max_length=500, blank=True, null=True, help_text="OAuth token from Meta")
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_waba_id = models.CharField(max_length=100, blank=True, null=True, help_text="WhatsApp Business Account ID")
    whatsapp_used_this_month = models.IntegerField(default=0)
    whatsapp_monthly_limit = models.IntegerField(default=500)
    
    # 4. OpenAI Integration (Managed by Master Account)
    is_ai_enabled = models.BooleanField(default=False)
    ai_tokens_used_this_month = models.IntegerField(default=0)
    ai_tokens_monthly_limit = models.IntegerField(default=100000)
    
    # 5. Telegram Integration (Optional BYOK for small tenants)
    is_telegram_enabled = models.BooleanField(default=False)
    telegram_bot_token = models.CharField(max_length=255, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.name} - Feature Config"
