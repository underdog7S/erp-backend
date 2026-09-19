from django.core.mail import get_connection, EmailMultiAlternatives
from django.conf import settings
from api.models.tenant_features import TenantFeatureConfig

def send_tenant_email(tenant, subject, message, recipient_list, html_message=None):
    """
    Sends an email on behalf of a tenant.
    If the tenant has custom BYOK SMTP settings, it logs into their server to send it.
    Otherwise, it falls back to the Master ERP email settings.
    """
    try:
        config = tenant.feature_config
    except TenantFeatureConfig.DoesNotExist:
        config = None

    connection = None
    from_email = settings.DEFAULT_FROM_EMAIL

    # Check for custom BYOK SMTP
    if config and config.smtp_host and config.smtp_username and config.smtp_password:
        connection = get_connection(
            host=config.smtp_host,
            port=config.smtp_port or 587,
            username=config.smtp_username,
            password=config.smtp_password,
            use_tls=config.smtp_use_tls,
            fail_silently=False
        )
        from_email = config.smtp_username
    elif config and config.managed_email_address:
        from_email = config.managed_email_address

    msg = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient_list,
        connection=connection
    )
    
    if html_message:
        msg.attach_alternative(html_message, "text/html")

    return msg.send(fail_silently=True)
