
import socket
import threading
import logging
import os
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from api.models.user import Tenant, UserProfile, Role
from api.models.plan import Plan
from api.models.email_verification import EmailVerification
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Override to check subscription status before allowing login"""
        # First, get the tokens (this validates credentials)
        response = super().post(request, *args, **kwargs)
        
        # If login successful (status 200), check subscription
        if response.status_code == status.HTTP_200_OK:
            try:
                # Get user from username
                username = request.data.get('username')
                if username:
                    user = User.objects.get(username=username)
                    profile = UserProfile.objects.get(user=user)
                    tenant = profile.tenant
                    
                    # Check if subscription has expired
                    if tenant.is_subscription_expired():
                        if tenant.subscription_status == 'expired':
                            # Block login completely
                            return Response({
                                'error': 'Your plan has expired. Please renew your subscription to access the system.',
                                'subscription_end_date': tenant.subscription_end_date.isoformat() if tenant.subscription_end_date else None,
                                'plan_name': tenant.plan.name if tenant.plan else 'N/A',
                                'renewal_required': True
                            }, status=status.HTTP_403_FORBIDDEN)
                        elif tenant.is_in_grace_period():
                            # Allow login but add warning to response
                            data = response.data
                            data['subscription_warning'] = {
                                'message': 'Your plan has expired. You are in a grace period with limited access.',
                                'grace_period_end': tenant.grace_period_end_date.isoformat() if tenant.grace_period_end_date else None,
                                'renewal_required': True
                            }
                            return Response(data, status=status.HTTP_200_OK)
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                # If we can't find user/profile, let normal login proceed
                pass
            except Exception as e:
                # Log error but don't block login
                logger.error(f"Error checking subscription during login: {e}")
        
        return response

class TokenRefresh(TokenRefreshView):
    permission_classes = [AllowAny]

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        try:
            # Check if user already exists
            if User.objects.filter(email=data["email"]).exists():
                return Response({"error": "User with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)
            
            if User.objects.filter(username=data["username"]).exists():
                return Response({"error": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Always assign the free plan to new tenants, regardless of frontend input
            plan = Plan.objects.get(name__iexact="Free")
            tenant = Tenant.objects.create(
                name=data["company"],
                industry=data["industry"],
                plan=plan
            )
            
            # Create user and activate immediately (email verification disabled)
            user = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"],
                is_active=True  # User is active immediately
            )
            
            # Always assign admin role to the first user of a new tenant
            admin_role, _ = Role.objects.get_or_create(name="admin")
            UserProfile.objects.create(
                user=user,
                tenant=tenant,
                role=admin_role  # Always admin for first user
                # department is not set for first user
            )
            
            # Create email verification
            email_verification = EmailVerification.objects.create(
                user=user,
                email=data["email"]
            )
            
            # Send verification email asynchronously (don't block registration)
            # This prevents timeout issues on slow email servers like SendGrid
            logger.info(f"🔄 Starting email thread for {data['email']}")
            try:
                email_thread = threading.Thread(
                    target=self.send_verification_email_async,
                    args=(email_verification,),
                    daemon=True
                )
                email_thread.start()
                logger.info(f"✅ Email thread started for {data['email']}")
            except Exception as e:
                logger.error(f"❌ Failed to start email thread for {data['email']}: {e}")
            
            # Return success immediately - email will be sent in background
            response_data = {
                "message": "Registration successful! Please check your email for verification link.",
                "email": data["email"]
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def send_verification_email_async(self, email_verification):
        """Send verification email asynchronously (in background thread)"""
        try:
            logger.info(f"📧 Starting background email send for {email_verification.email}")
            self.send_verification_email(email_verification)
            logger.info(f"✅ Background email sent successfully to {email_verification.email}")
        except socket.timeout as e:
            logger.error(f"⏱️ Email sending timed out for {email_verification.email}: {e}")
        except Exception as e:
            logger.error(f"❌ Background email sending failed for {email_verification.email}: {type(e).__name__}: {e}")
    
    def send_verification_email(self, email_verification):
        """Send verification email using SendGrid HTTP API (more reliable than SMTP)"""
        # Check if SendGrid API key is configured
        sendgrid_api_key = os.getenv('SENDGRID_API_KEY', settings.EMAIL_HOST_PASSWORD)
        
        # If EMAIL_HOST_PASSWORD looks like a SendGrid API key (starts with SG.), use HTTP API
        if sendgrid_api_key and sendgrid_api_key.startswith('SG.'):
            logger.info("Using SendGrid HTTP API for email sending")
            return self._send_via_sendgrid_api(email_verification, sendgrid_api_key)
        
        # Otherwise, fall back to SMTP
        logger.info(f"Using SMTP: EMAIL_HOST={settings.EMAIL_HOST}")
        logger.info(f"DEBUG: EMAIL_HOST_USER set: {bool(settings.EMAIL_HOST_USER)}, value: {settings.EMAIL_HOST_USER[:10] if settings.EMAIL_HOST_USER else 'EMPTY'}...")
        logger.info(f"DEBUG: EMAIL_HOST_PASSWORD set: {bool(settings.EMAIL_HOST_PASSWORD)}, length: {len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 0}")
        
        # Check if email is configured
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            error_msg = f"Email configuration missing. EMAIL_HOST_USER={'SET' if settings.EMAIL_HOST_USER else 'NOT SET'}, EMAIL_HOST_PASSWORD={'SET' if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}."
            logger.error(f"Failed to send verification email: {error_msg}")
            raise Exception(error_msg)
        
        if not settings.DEFAULT_FROM_EMAIL or settings.DEFAULT_FROM_EMAIL == 'noreply@zenitherp.com':
            if settings.EMAIL_HOST_USER:
                from_email = settings.EMAIL_HOST_USER
            else:
                error_msg = "DEFAULT_FROM_EMAIL is not configured."
                logger.error(f"Failed to send verification email: {error_msg}")
                raise Exception(error_msg)
        else:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={email_verification.token}"
        subject = "Verify Your Zenith ERP Account"
        # HTML email body
        html_message = f"""
        <div style='font-family: Arial, sans-serif; background: #f9f9f9; padding: 32px;'>
            <div style='max-width: 480px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #e0e0e0; padding: 32px;'>
                <h2 style='color: #1a237e; text-align: center;'>Welcome to <span style='color: #4caf50;'>Zenith ERP</span>!</h2>
                <p style='font-size: 16px; color: #333;'>Thank you for registering. To activate your account, please verify your email address by clicking the button below:</p>
                <div style='text-align: center; margin: 32px 0;'>
                    <a href='{verification_url}' style='background: #4caf50; color: #fff; text-decoration: none; padding: 14px 32px; border-radius: 4px; font-size: 18px; font-weight: bold; display: inline-block;'>Verify Email</a>
                </div>
                <p style='font-size: 15px; color: #555;'>Or copy and paste this link into your browser:</p>
                <p style='word-break: break-all; color: #1a237e; font-size: 14px;'>{verification_url}</p>
                <p style='font-size: 14px; color: #888; margin-top: 32px;'>This link will expire in 24 hours.<br>If you did not create this account, you can safely ignore this email.</p>
                <hr style='margin: 32px 0; border: none; border-top: 1px solid #eee;'>
                <p style='text-align: center; color: #888; font-size: 13px;'>Best regards,<br><b>Zenith ERP Team</b></p>
            </div>
        </div>
        """
        # Plain text fallback
        message = f"""
Welcome to Zenith ERP!

Thank you for registering. To activate your account, please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.
If you did not create this account, you can safely ignore this email.

Best regards,
Zenith ERP Team
        """
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[email_verification.email],
        )
        email.attach_alternative(html_message, "text/html")
        
        # Send email with timeout to prevent hanging
        socket.setdefaulttimeout(30)  # 30 second timeout (increased for SendGrid)
        try:
            email.send(fail_silently=False)
            logger.info(f"✅ Verification email sent successfully to {email_verification.email}")
        except socket.timeout:
            logger.error(f"⚠️ Email sending timed out for {email_verification.email}")
            raise Exception("Email sending timed out. Please check your email configuration or try again later.")
        except Exception as e:
            logger.error(f"❌ Failed to send verification email to {email_verification.email}: {str(e)}")
            raise Exception(f"Failed to send verification email: {str(e)}")
        finally:
            socket.setdefaulttimeout(None)  # Reset timeout
    
    def _send_via_sendgrid_api(self, email_verification, api_key):
        """Send email using SendGrid HTTP API"""
        from_email = os.getenv('DEFAULT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER or 'noreply@zenitherp.com')
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={email_verification.token}"
        
        html_content = f"""
        <div style='font-family: Arial, sans-serif; background: #f9f9f9; padding: 32px;'>
            <div style='max-width: 480px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #e0e0e0; padding: 32px;'>
                <h2 style='color: #1a237e; text-align: center;'>Welcome to <span style='color: #4caf50;'>Zenith ERP</span>!</h2>
                <p style='font-size: 16px; color: #333;'>Thank you for registering. To activate your account, please verify your email address by clicking the button below:</p>
                <div style='text-align: center; margin: 32px 0;'>
                    <a href='{verification_url}' style='background: #4caf50; color: #fff; text-decoration: none; padding: 14px 32px; border-radius: 4px; font-size: 18px; font-weight: bold; display: inline-block;'>Verify Email</a>
                </div>
                <p style='font-size: 15px; color: #555;'>Or copy and paste this link into your browser:</p>
                <p style='word-break: break-all; color: #1a237e; font-size: 14px;'>{verification_url}</p>
                <p style='font-size: 14px; color: #888; margin-top: 32px;'>This link will expire in 24 hours.<br>If you did not create this account, you can safely ignore this email.</p>
                <hr style='margin: 32px 0; border: none; border-top: 1px solid #eee;'>
                <p style='text-align: center; color: #888; font-size: 13px;'>Best regards,<br><b>Zenith ERP Team</b></p>
            </div>
        </div>
        """
        
        text_content = f"""
Welcome to Zenith ERP!

Thank you for registering. To activate your account, please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.
If you did not create this account, you can safely ignore this email.

Best regards,
Zenith ERP Team
        """
        
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "personalizations": [{
                "to": [{"email": email_verification.email}],
                "subject": "Verify Your Zenith ERP Account"
            }],
            "from": {"email": from_email},
            "content": [
                {"type": "text/plain", "value": text_content},
                {"type": "text/html", "value": html_content}
            ]
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            logger.info(f"✅ Verification email sent successfully via SendGrid API to {email_verification.email}")
        except requests.exceptions.RequestException as e:
            error_msg = f"SendGrid API error: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" - Response: {e.response.text}"
            logger.error(f"❌ Failed to send email via SendGrid API: {error_msg}")
            raise Exception(error_msg)

class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        logger.info(f"DEBUG: Verification request received. Token: {token}, Type: {type(token)}")
        logger.info(f"DEBUG: Request data: {request.data}")
        
        if not token:
            logger.warning("DEBUG: No token provided in request")
            return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Try to convert token to UUID format if it's a string
            import uuid
            try:
                token_uuid = uuid.UUID(str(token))
                logger.info(f"DEBUG: Token converted to UUID: {token_uuid}")
            except (ValueError, AttributeError) as e:
                logger.error(f"DEBUG: Invalid token format: {token}, Error: {e}")
                return Response({"error": f"Invalid token format: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"DEBUG: Looking for token: {token_uuid}")
            email_verification = EmailVerification.objects.get(token=token_uuid)
            logger.info(f"DEBUG: Found verification for: {email_verification.email}")
            logger.info(f"DEBUG: Is verified: {email_verification.is_verified}, Is expired: {email_verification.is_expired}")
            
            if email_verification.is_verified:
                return Response({"error": "Email already verified."}, status=status.HTTP_400_BAD_REQUEST)
            
            if email_verification.is_expired:
                return Response({"error": "Verification link has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify the email
            email_verification.verify()
            
            # Generate tokens for automatic login
            refresh = RefreshToken.for_user(email_verification.user)
            
            return Response({
                "message": "Email verified successfully! You can now log in.",
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }, status=status.HTTP_200_OK)
            
        except EmailVerification.DoesNotExist:
            logger.error(f"DEBUG: Token not found in database: {token}")
            # Check if any tokens exist (for debugging)
            count = EmailVerification.objects.count()
            logger.info(f"DEBUG: Total email verifications in DB: {count}")
            return Response({"error": "Invalid verification token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"DEBUG: Verification error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                return Response({"error": "Email is already verified."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete old verification tokens
            EmailVerification.objects.filter(user=user).delete()
            
            # Create new verification
            email_verification = EmailVerification.objects.create(
                user=user,
                email=email
            )
            
            # Send new verification email
            self.send_verification_email(email_verification)
            
            return Response({
                "message": "Verification email sent successfully."
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({"error": "User with this email not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def send_verification_email(self, email_verification):
        """Send verification email to user"""
        try:
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={email_verification.token}"
            
            subject = "Verify Your Zenith ERP Account"
            message = f"""
            Welcome to Zenith ERP!
            
            Please click the link below to verify your email address:
            {verification_url}
            
            This link will expire in 24 hours.
            
            If you didn't create this account, please ignore this email.
            
            Best regards,
            Zenith ERP Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_verification.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send verification email: {e}")
