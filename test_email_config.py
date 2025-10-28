#!/usr/bin/env python
"""
Test script to check email configuration
Run: python manage.py shell < test_email_config.py
Or: python test_email_config.py (with Django setup)
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives

def test_email_config():
    """Test email configuration"""
    print("=" * 60)
    print("EMAIL CONFIGURATION TEST")
    print("=" * 60)
    
    print(f"\nEMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER or '(NOT SET)'}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * 10 if settings.EMAIL_HOST_PASSWORD else '(NOT SET)'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    print("\n" + "-" * 60)
    
    # Check if email is configured
    if not settings.EMAIL_HOST_USER:
        print("❌ ERROR: EMAIL_HOST_USER is not set!")
        print("   Set it in your environment variables.")
        return False
    
    if not settings.EMAIL_HOST_PASSWORD:
        print("❌ ERROR: EMAIL_HOST_PASSWORD is not set!")
        print("   Set it in your environment variables (Gmail App Password).")
        return False
    
    print("✅ Email credentials are set")
    
    # Test sending email
    print("\n" + "-" * 60)
    print("Testing email send...")
    print("-" * 60)
    
    test_email = input("\nEnter your email address to test: ").strip()
    
    if not test_email:
        print("❌ No email provided. Exiting.")
        return False
    
    try:
        subject = "Test Email from Zenith ERP"
        message = "This is a test email. If you receive this, email configuration is working!"
        html_message = f"""
        <div style='font-family: Arial, sans-serif; padding: 20px;'>
            <h2>Test Email</h2>
            <p>This is a test email from Zenith ERP.</p>
            <p>If you receive this, your email configuration is working correctly!</p>
        </div>
        """
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            to=[test_email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        print(f"✅ Test email sent successfully to {test_email}!")
        print("   Check your inbox (and spam folder).")
        return True
        
    except Exception as e:
        print(f"❌ ERROR sending email: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        if "SMTPAuthenticationError" in str(type(e).__name__):
            print("\n💡 Fix: Check your Gmail App Password")
            print("   - Enable 2-Step Verification")
            print("   - Generate App Password")
            print("   - Update EMAIL_HOST_PASSWORD")
        elif "SMTPServerDisconnected" in str(type(e).__name__):
            print("\n💡 Fix: Check SMTP connection settings")
        elif "Connection refused" in str(e):
            print("\n💡 Fix: Check network/firewall settings")
        else:
            print(f"\n💡 Review the error above for specific fix.")
        
        return False

if __name__ == '__main__':
    test_email_config()

