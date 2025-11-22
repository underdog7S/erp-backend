"""
Razorpay Integration Views
Handles Razorpay setup wizard and payment processing for all sectors
"""
try:
    import razorpay
except ImportError:
    razorpay = None

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile, Tenant
from django.utils import timezone
import hmac
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class RazorpaySetupStatusView(APIView):
    """Check Razorpay setup status for tenant"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            setup_status = {
                'is_configured': tenant.has_razorpay_configured(),
                'has_key_id': bool(tenant.razorpay_key_id),
                'has_key_secret': bool(tenant.razorpay_key_secret),
                'has_webhook_secret': bool(tenant.razorpay_webhook_secret),
                'is_enabled': tenant.razorpay_enabled,
                'setup_completed': tenant.razorpay_setup_completed,
                'setup_steps': self._get_setup_steps(request, tenant)
            }
            
            return Response(setup_status)
        except Exception as e:
            logger.error(f"Error checking Razorpay setup: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_setup_steps(self, request, tenant):
        """Get setup steps with completion status"""
        steps = [
            {
                'step': 1,
                'title': 'Create Razorpay Account',
                'description': 'Sign up at https://razorpay.com and verify your business',
                'completed': tenant.razorpay_setup_completed,
                'action_url': 'https://razorpay.com/signup'
            },
            {
                'step': 2,
                'title': 'Get API Keys',
                'description': 'Go to Settings > API Keys in Razorpay Dashboard and copy your Key ID and Key Secret',
                'completed': bool(tenant.razorpay_key_id and tenant.razorpay_key_secret),
                'action_url': 'https://dashboard.razorpay.com/app/keys'
            },
            {
                'step': 3,
                'title': 'Configure Webhook',
                'description': 'Set up webhook URL in Razorpay Dashboard: Settings > Webhooks',
                'completed': bool(tenant.razorpay_webhook_secret),
                'action_url': 'https://dashboard.razorpay.com/app/webhooks',
                'webhook_url': self._get_webhook_url(request, tenant.id)
            },
            {
                'step': 4,
                'title': 'Enable Payments',
                'description': 'Enable Razorpay payments for your organization',
                'completed': tenant.razorpay_enabled
            }
        ]
        return steps
    
    def _get_webhook_url(self, request, tenant_id):
        """Generate webhook URL"""
        try:
            return f"{request.build_absolute_uri('/').rstrip('/')}/api/razorpay/webhook/{tenant_id}/"
        except:
            return f"/api/razorpay/webhook/{tenant_id}/"


class RazorpaySetupView(APIView):
    """Configure Razorpay for tenant"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            # Check if user is admin
            if not profile.role or profile.role.name != 'admin':
                return Response({
                    'error': 'Only administrators can configure Razorpay'
                }, status=status.HTTP_403_FORBIDDEN)
            
            razorpay_key_id = request.data.get('razorpay_key_id', '').strip()
            razorpay_key_secret = request.data.get('razorpay_key_secret', '').strip()
            razorpay_webhook_secret = request.data.get('razorpay_webhook_secret', '').strip()
            razorpay_enabled = request.data.get('razorpay_enabled', False)
            
            # Validate keys if provided
            if razorpay_key_id and razorpay_key_secret:
                if razorpay is None:
                    return Response({
                        'error': 'Razorpay library not installed. Please contact support.'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
                # Test Razorpay connection
                try:
                    client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
                    # Test API call
                    client.payment.fetch_all({'count': 1})
                except Exception as e:
                    return Response({
                        'error': f'Invalid Razorpay credentials: {str(e)}',
                        'details': 'Please verify your Key ID and Key Secret from Razorpay Dashboard'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update tenant Razorpay settings
            if razorpay_key_id:
                tenant.razorpay_key_id = razorpay_key_id
            if razorpay_key_secret:
                tenant.razorpay_key_secret = razorpay_key_secret
            if razorpay_webhook_secret:
                tenant.razorpay_webhook_secret = razorpay_webhook_secret
            
            tenant.razorpay_enabled = razorpay_enabled
            
            # Mark setup as completed if all required fields are present
            if tenant.razorpay_key_id and tenant.razorpay_key_secret:
                tenant.razorpay_setup_completed = True
            
            tenant.save()
            
            return Response({
                'message': 'Razorpay configuration updated successfully',
                'is_configured': tenant.has_razorpay_configured(),
                'setup_completed': tenant.razorpay_setup_completed
            })
            
        except Exception as e:
            logger.error(f"Error configuring Razorpay: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RazorpaySetupGuideView(APIView):
    """Get detailed setup guide for Razorpay"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            guide = {
                'title': 'Razorpay Payment Gateway Setup Guide',
                'description': 'Follow these steps to integrate Razorpay and start accepting online payments',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Create Razorpay Account',
                        'description': 'Sign up for a Razorpay account',
                        'instructions': [
                            'Visit https://razorpay.com/signup',
                            'Enter your business details',
                            'Verify your email and phone number',
                            'Complete KYC verification (required for live payments)'
                        ],
                        'help_url': 'https://razorpay.com/signup',
                        'estimated_time': '5-10 minutes'
                    },
                    {
                        'step': 2,
                        'title': 'Get API Keys',
                        'description': 'Retrieve your API credentials from Razorpay Dashboard',
                        'instructions': [
                            'Login to Razorpay Dashboard: https://dashboard.razorpay.com',
                            'Navigate to Settings > API Keys',
                            'Copy your "Key ID" (starts with rzp_)',
                            'Click "Reveal" to see your "Key Secret"',
                            'Copy the Key Secret (keep it secure)'
                        ],
                        'help_url': 'https://dashboard.razorpay.com/app/keys',
                        'estimated_time': '2 minutes',
                        'note': 'Use Test Mode keys for testing, Live Mode keys for production'
                    },
                    {
                        'step': 3,
                        'title': 'Configure Webhook',
                        'description': 'Set up webhook for payment notifications',
                        'instructions': [
                            'Go to Settings > Webhooks in Razorpay Dashboard',
                            'Click "Add New Webhook"',
                            f'Enter Webhook URL: {self._get_webhook_url(request, tenant.id)}',
                            'Select events: payment.captured, payment.failed',
                            'Copy the Webhook Secret',
                            'Save the webhook secret in the setup form'
                        ],
                        'help_url': 'https://dashboard.razorpay.com/app/webhooks',
                        'estimated_time': '3 minutes',
                        'webhook_url': self._get_webhook_url(request, tenant.id)
                    },
                    {
                        'step': 4,
                        'title': 'Enter Credentials',
                        'description': 'Add your Razorpay credentials in the setup form',
                        'instructions': [
                            'Enter your Key ID',
                            'Enter your Key Secret',
                            'Enter your Webhook Secret (optional but recommended)',
                            'Enable Razorpay payments',
                            'Click "Save Configuration"'
                        ],
                        'estimated_time': '1 minute'
                    },
                    {
                        'step': 5,
                        'title': 'Test Payment',
                        'description': 'Test your integration with a small amount',
                        'instructions': [
                            'Use Test Mode keys for testing',
                            'Try making a test payment',
                            'Verify payment appears in transactions',
                            'Switch to Live Mode when ready for production'
                        ],
                        'estimated_time': '5 minutes'
                    }
                ],
                'faq': [
                    {
                        'question': 'What is the difference between Test Mode and Live Mode?',
                        'answer': 'Test Mode allows you to test payments without real money. Use Test Mode keys during development. Live Mode processes real payments - use Live Mode keys in production.'
                    },
                    {
                        'question': 'How do I switch from Test Mode to Live Mode?',
                        'answer': 'In Razorpay Dashboard, go to Settings > API Keys and toggle to Live Mode. Copy the new Live Mode keys and update them in your configuration.'
                    },
                    {
                        'question': 'Is webhook configuration mandatory?',
                        'answer': 'Webhooks are recommended for reliable payment status updates. They ensure your system is notified when payments are captured or failed.'
                    },
                    {
                        'question': 'What payment methods are supported?',
                        'answer': 'Razorpay supports Credit/Debit Cards, UPI, Net Banking, Wallets, and more. All methods are automatically available once configured.'
                    }
                ],
                'support': {
                    'razorpay_docs': 'https://razorpay.com/docs/',
                    'razorpay_support': 'https://razorpay.com/support/',
                    'dashboard': 'https://dashboard.razorpay.com'
                }
            }
            
            return Response(guide)
        except Exception as e:
            logger.error(f"Error getting setup guide: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_webhook_url(self, request, tenant_id):
        """Generate webhook URL"""
        try:
            return f"{request.build_absolute_uri('/').rstrip('/')}/api/razorpay/webhook/{tenant_id}/"
        except:
            return f"/api/razorpay/webhook/{tenant_id}/"


class RazorpayCreateOrderView(APIView):
    """Create Razorpay order for any sector payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if razorpay is None:
            return Response({
                'error': 'Razorpay is not available. Please check configuration.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            # Check if Razorpay is configured
            if not tenant.has_razorpay_configured():
                return Response({
                    'error': 'Razorpay is not configured. Please complete the setup wizard.',
                    'setup_required': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            amount = request.data.get('amount')
            currency = request.data.get('currency', 'INR')
            receipt = request.data.get('receipt', None)
            description = request.data.get('description', 'Payment')
            sector = request.data.get('sector', 'general')  # education, restaurant, salon, etc.
            reference_id = request.data.get('reference_id')  # fee_payment_id, order_id, appointment_id, etc.
            
            if not amount:
                return Response({'error': 'Amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                amount_float = float(amount)
                if amount_float <= 0:
                    return Response({
                        'error': 'Amount must be greater than 0.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Use tenant-specific Razorpay keys
                client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
                
                order_data = {
                    'amount': int(amount_float * 100),  # Razorpay expects paise
                    'currency': currency,
                    'payment_capture': 1,
                    'notes': {
                        'sector': sector,
                        'reference_id': str(reference_id) if reference_id else None,
                        'tenant_id': str(tenant.id),
                        'description': description
                    }
                }
                
                if receipt:
                    order_data['receipt'] = receipt
                else:
                    # Generate receipt ID
                    order_data['receipt'] = f"{sector.upper()}-{reference_id or 'TXN'}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                
                order = client.order.create(data=order_data)
                
                return Response({
                    'order_id': order['id'],
                    'amount': order['amount'],
                    'currency': order['currency'],
                    'key_id': tenant.razorpay_key_id,  # Frontend needs this
                    'receipt': order.get('receipt'),
                    'notes': order.get('notes', {})
                }, status=status.HTTP_201_CREATED)
                
            except ValueError:
                return Response({
                    'error': 'Invalid amount format.'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Razorpay order creation error: {str(e)}")
                return Response({
                    'error': f'Payment order creation failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except UserProfile.DoesNotExist:
            return Response({
                'error': 'User profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating Razorpay order: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RazorpayVerifyPaymentView(APIView):
    """Verify Razorpay payment for any sector"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            if not tenant.has_razorpay_configured():
                return Response({
                    'error': 'Razorpay is not configured.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            payment_id = request.data.get('razorpay_payment_id')
            order_id = request.data.get('razorpay_order_id')
            signature = request.data.get('razorpay_signature')
            sector = request.data.get('sector', 'general')
            reference_id = request.data.get('reference_id')  # fee_payment_id, order_id, etc.
            
            if not (payment_id and order_id and signature):
                return Response({
                    'error': 'Missing payment verification data.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify signature
            key_secret = tenant.razorpay_key_secret
            msg = f"{order_id}|{payment_id}"
            generated_signature = hmac.new(
                key_secret.encode(),
                msg.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if generated_signature != signature:
                return Response({
                    'error': 'Invalid payment signature.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get payment details from Razorpay
            if razorpay is None:
                return Response({
                    'error': 'Razorpay is not available.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
            payment = client.payment.fetch(payment_id)
            
            if payment['status'] != 'captured':
                return Response({
                    'error': f'Payment not captured. Status: {payment["status"]}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check for duplicate payment - prevent processing same payment twice
            from api.models.payments import PaymentTransaction
            existing_transaction = PaymentTransaction.objects.filter(payment_id=payment_id).first()
            if existing_transaction:
                # If transaction exists for different tenant, this is a security issue
                if existing_transaction.tenant != tenant:
                    logger.error(f"Payment {payment_id} attempted to be processed by different tenant. Original: {existing_transaction.tenant.id}, Attempted: {tenant.id}")
                    return Response({
                        'error': 'This payment has already been processed by another organization.',
                        'security_alert': True
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Same tenant - return existing transaction
                return Response({
                    'message': 'Payment already processed',
                    'payment_id': payment_id,
                    'order_id': order_id,
                    'sector': existing_transaction.sector,
                    'reference_id': existing_transaction.reference_id,
                    'amount': float(existing_transaction.amount),
                    'status': existing_transaction.status,
                    'already_processed': True
                })
            
            # Verify order belongs to this tenant by checking Razorpay order notes
            try:
                razorpay_order = client.order.fetch(order_id)
                order_notes = razorpay_order.get('notes', {})
                order_tenant_id = order_notes.get('tenant_id')
                
                # Validate tenant matches
                if order_tenant_id and str(order_tenant_id) != str(tenant.id):
                    logger.error(f"Order {order_id} tenant mismatch. Order tenant: {order_tenant_id}, Request tenant: {tenant.id}")
                    return Response({
                        'error': 'Payment order does not belong to this organization.',
                        'security_alert': True
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Get sector and reference from order notes if not provided
                if not sector or sector == 'general':
                    sector = order_notes.get('sector', 'general')
                if not reference_id:
                    reference_id = order_notes.get('reference_id')
                    
            except Exception as e:
                logger.warning(f"Could not verify order tenant: {str(e)}")
                # Continue but log warning
            
            # Payment verified - handle based on sector
            payment_data = {
                'payment_id': payment_id,
                'order_id': order_id,
                'signature': signature,
                'sector': sector,
                'reference_id': reference_id,
                'tenant_id': tenant.id,
                'user_id': request.user.id,
                'amount': payment['amount'] / 100.0,
                'currency': payment['currency']
            }
            
            # Validate reference_id belongs to this tenant
            if reference_id and not self._validate_reference_tenant(sector, reference_id, tenant):
                return Response({
                    'error': 'Payment reference does not belong to this organization.',
                    'security_alert': True
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Call sector-specific payment handler
            result = self._handle_sector_payment(payment_data, tenant)
            
            if 'error' in result:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate description
            description = self._generate_description(sector, result, payment_data)
            
            # Create payment transaction record
            PaymentTransaction.objects.create(
                user=request.user,
                tenant=tenant,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
                amount=payment_data['amount'],
                currency=payment_data['currency'],
                status='verified',
                sector=sector,
                reference_id=str(reference_id) if reference_id else None,
                description=description,
                verified_at=timezone.now()
            )
            
            return Response({
                'message': 'Payment verified successfully',
                'payment_id': payment_id,
                'order_id': order_id,
                'sector': sector,
                'amount': payment_data['amount'],
                'result': result
            })
            
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}", exc_info=True)
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_reference_tenant(self, sector, reference_id, tenant):
        """Validate that reference_id belongs to the correct tenant"""
        try:
            if sector == 'education' and reference_id:
                from education.models import FeePayment
                return FeePayment.objects.filter(id=reference_id, tenant=tenant).exists()
            elif sector == 'restaurant' and reference_id:
                from restaurant.models import Order
                return Order.objects.filter(id=reference_id, tenant=tenant).exists()
            elif sector == 'salon' and reference_id:
                from salon.models import Appointment
                return Appointment.objects.filter(id=reference_id, tenant=tenant).exists()
            elif sector == 'pharmacy' and reference_id:
                from pharmacy.models import Sale
                return Sale.objects.filter(id=reference_id, tenant=tenant).exists()
            elif sector == 'retail' and reference_id:
                from retail.models import Sale
                return Sale.objects.filter(id=reference_id, tenant=tenant).exists()
            elif sector == 'hotel' and reference_id:
                from hotel.models import Booking
                return Booking.objects.filter(id=reference_id, tenant=tenant).exists()
            # For plan or general, no reference validation needed
            return True
        except Exception as e:
            logger.error(f"Error validating reference tenant: {str(e)}")
            return False
    
    def _generate_description(self, sector, result, payment_data):
        """Generate human-readable description for transaction"""
        try:
            if sector == 'education' and result.get('type') == 'fee_payment':
                return f"Education Fee Payment - Student ID: {payment_data.get('reference_id')}"
            elif sector == 'restaurant' and result.get('type') == 'order':
                return f"Restaurant Order Payment - Order ID: {payment_data.get('reference_id')}"
            elif sector == 'salon' and result.get('type') == 'appointment':
                return f"Salon Appointment Payment - Appointment ID: {payment_data.get('reference_id')}"
            elif sector == 'pharmacy' and result.get('type') == 'sale':
                return f"Pharmacy Sale Payment - Sale ID: {payment_data.get('reference_id')}"
            elif sector == 'retail' and result.get('type') == 'sale':
                return f"Retail Sale Payment - Sale ID: {payment_data.get('reference_id')}"
            elif sector == 'hotel' and result.get('type') == 'booking':
                return f"Hotel Booking Payment - Booking ID: {payment_data.get('reference_id')}"
            elif sector == 'plan':
                return f"Plan Subscription Payment"
            else:
                return f"Payment - {sector.title()}"
        except:
            return f"Payment - {sector}"
    
    def _handle_sector_payment(self, payment_data, tenant):
        """Handle payment based on sector"""
        sector = payment_data['sector']
        reference_id = payment_data['reference_id']
        
        try:
            if sector == 'education' and reference_id:
                # Update fee payment
                from education.models import FeePayment
                fee_payment = FeePayment.objects.select_related('student', 'fee_structure', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if fee_payment:
                    fee_payment.payment_method = 'RAZORPAY'
                    fee_payment.save()
                    return {'type': 'fee_payment', 'id': fee_payment.id, 'status': 'paid'}
                return {'error': 'Fee payment not found'}
            
            elif sector == 'restaurant' and reference_id:
                # Update restaurant order
                from restaurant.models import Order
                order = Order.objects.select_related('table', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if order:
                    order.status = 'paid'
                    order.save()
                    return {'type': 'order', 'id': order.id, 'status': 'paid'}
                return {'error': 'Order not found'}
            
            elif sector == 'salon' and reference_id:
                # Update salon appointment
                from salon.models import Appointment
                appointment = Appointment.objects.select_related('service', 'stylist', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if appointment:
                    appointment.status = 'completed'
                    appointment.payment_status = 'paid'
                    appointment.payment_method = 'RAZORPAY'
                    appointment.save()
                    return {'type': 'appointment', 'id': appointment.id, 'status': 'paid'}
                return {'error': 'Appointment not found'}
            
            elif sector == 'pharmacy' and reference_id:
                # Update pharmacy sale
                from pharmacy.models import Sale
                sale = Sale.objects.select_related('customer', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if sale:
                    sale.payment_method = 'RAZORPAY'
                    sale.payment_status = 'PAID'
                    sale.save()
                    return {'type': 'sale', 'id': sale.id, 'status': 'paid'}
                return {'error': 'Sale not found'}
            
            elif sector == 'retail' and reference_id:
                # Update retail sale
                from retail.models import Sale
                sale = Sale.objects.select_related('customer', 'warehouse', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if sale:
                    sale.payment_method = 'RAZORPAY'
                    sale.payment_status = 'PAID'
                    sale.save()
                    return {'type': 'sale', 'id': sale.id, 'status': 'paid'}
                return {'error': 'Sale not found'}
            
            elif sector == 'hotel' and reference_id:
                # Update hotel booking
                from hotel.models import Booking
                booking = Booking.objects.select_related('room', 'guest', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if booking:
                    booking.status = 'reserved'
                    booking.save()
                    return {'type': 'booking', 'id': booking.id, 'status': 'reserved'}
                return {'error': 'Booking not found'}
            
            return {'type': 'general', 'status': 'verified'}
            
        except Exception as e:
            logger.error(f"Error handling sector payment: {str(e)}", exc_info=True)
            return {'error': str(e)}


class RazorpayWebhookView(APIView):
    """Handle Razorpay webhook events"""
    authentication_classes = []
    permission_classes = []
    
    from django.views.decorators.csrf import csrf_exempt
    from django.utils.decorators import method_decorator
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, tenant_id):
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            
            if not tenant.razorpay_webhook_secret:
                logger.warning(f"Webhook received for tenant {tenant_id} but no webhook secret configured")
                return Response({'status': 'webhook secret not configured'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify webhook signature
            payload = request.body.decode('utf-8')
            received_signature = request.headers.get('X-Razorpay-Signature', '')
            
            expected_signature = hmac.new(
                tenant.razorpay_webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if received_signature != expected_signature:
                logger.warning(f"Invalid webhook signature for tenant {tenant_id}")
                return Response({'status': 'invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
            
            event = json.loads(payload)
            event_type = event.get('event')
            
            # Handle payment events
            if event_type == 'payment.captured':
                payment_entity = event['payload']['payment']['entity']
                payment_id = payment_entity['id']
                order_id = payment_entity.get('order_id')
                amount = payment_entity['amount'] / 100.0
                currency = payment_entity.get('currency', 'INR')
                
                # Check for duplicate - prevent processing same payment twice
                from api.models.payments import PaymentTransaction
                existing_transaction = PaymentTransaction.objects.filter(payment_id=payment_id).first()
                if existing_transaction:
                    logger.info(f"Payment {payment_id} already processed, skipping webhook")
                    return Response({'status': 'already_processed'})
                
                # Fetch order to get notes
                try:
                    if razorpay and tenant.has_razorpay_configured():
                        client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
                        razorpay_order = client.order.fetch(order_id) if order_id else None
                        order_notes = razorpay_order.get('notes', {}) if razorpay_order else payment_entity.get('notes', {})
                    else:
                        order_notes = payment_entity.get('notes', {})
                    
                    # Validate tenant from order notes
                    order_tenant_id = order_notes.get('tenant_id')
                    if order_tenant_id and str(order_tenant_id) != str(tenant.id):
                        logger.error(f"Webhook: Order {order_id} tenant mismatch. Order tenant: {order_tenant_id}, Webhook tenant: {tenant.id}")
                        return Response({'status': 'tenant_mismatch'}, status=status.HTTP_403_FORBIDDEN)
                    
                    sector = order_notes.get('sector', 'general')
                    reference_id = order_notes.get('reference_id')
                    
                    # Validate reference belongs to tenant
                    if reference_id:
                        validator = RazorpayVerifyPaymentView()
                        if not validator._validate_reference_tenant(sector, reference_id, tenant):
                            logger.error(f"Webhook: Reference {reference_id} does not belong to tenant {tenant.id}")
                            return Response({'status': 'reference_validation_failed'}, status=status.HTTP_403_FORBIDDEN)
                    
                    # Update payment status based on sector
                    result = self._update_payment_status(tenant, sector, reference_id, 'paid', payment_id, order_id)
                    
                    # Create transaction record (webhook payments don't have user context)
                    description = f"Webhook: {sector.title()} Payment"
                    PaymentTransaction.objects.create(
                        tenant=tenant,
                        user=None,  # Webhook doesn't have user context - user field is nullable
                        order_id=order_id or '',
                        payment_id=payment_id,
                        signature='',  # Webhook doesn't provide signature
                        amount=amount,
                        currency=currency,
                        status='verified',
                        sector=sector,
                        reference_id=str(reference_id) if reference_id else None,
                        description=description,
                        verified_at=timezone.now()
                    )
                    
                    logger.info(f"Payment captured via webhook: {payment_id} for tenant {tenant_id}, sector {sector}")
                except Exception as e:
                    logger.error(f"Error processing webhook payment: {str(e)}", exc_info=True)
                    return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            elif event_type == 'payment.failed':
                payment_entity = event['payload']['payment']['entity']
                payment_id = payment_entity['id']
                order_id = payment_entity.get('order_id')
                
                # Get order notes
                try:
                    if razorpay and tenant.has_razorpay_configured():
                        client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
                        razorpay_order = client.order.fetch(order_id) if order_id else None
                        order_notes = razorpay_order.get('notes', {}) if razorpay_order else payment_entity.get('notes', {})
                    else:
                        order_notes = payment_entity.get('notes', {})
                    
                    sector = order_notes.get('sector', 'general')
                    reference_id = order_notes.get('reference_id')
                    
                    self._update_payment_status(tenant, sector, reference_id, 'failed', payment_id, order_id)
                    
                    logger.info(f"Payment failed via webhook: {payment_id} for tenant {tenant_id}, sector {sector}")
                except Exception as e:
                    logger.error(f"Error processing failed payment webhook: {str(e)}")
            
            return Response({'status': 'webhook received'})
            
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def _update_payment_status(self, tenant, sector, reference_id, status, payment_id, order_id):
        """Update payment status based on sector"""
        try:
            if sector == 'education' and reference_id:
                from education.models import FeePayment
                fee_payment = FeePayment.objects.filter(id=reference_id, tenant=tenant).first()
                if fee_payment:
                    fee_payment.payment_method = 'RAZORPAY' if status == 'paid' else fee_payment.payment_method
                    fee_payment.save()
            
            elif sector == 'restaurant' and reference_id:
                from restaurant.models import Order
                order = Order.objects.filter(id=reference_id, tenant=tenant).first()
                if order:
                    order.status = 'paid' if status == 'paid' else 'cancelled'
                    order.save()
            
            elif sector == 'salon' and reference_id:
                from salon.models import Appointment
                appointment = Appointment.objects.filter(id=reference_id, tenant=tenant).first()
                if appointment:
                    appointment.payment_status = status
                    if status == 'paid':
                        appointment.status = 'completed'
                    appointment.save()
            
            elif sector == 'pharmacy' and reference_id:
                from pharmacy.models import Sale
                sale = Sale.objects.select_related('customer', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if sale:
                    sale.payment_method = 'RAZORPAY' if status == 'paid' else sale.payment_method
                    sale.payment_status = 'PAID' if status == 'paid' else sale.payment_status
                    sale.save()
            
            elif sector == 'retail' and reference_id:
                from retail.models import Sale
                sale = Sale.objects.select_related('customer', 'warehouse', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if sale:
                    sale.payment_method = 'RAZORPAY' if status == 'paid' else sale.payment_method
                    sale.payment_status = 'PAID' if status == 'paid' else sale.payment_status
                    sale.save()
            
            elif sector == 'hotel' and reference_id:
                from hotel.models import Booking
                booking = Booking.objects.select_related('room', 'guest', 'tenant').filter(id=reference_id, tenant=tenant).first()
                if booking:
                    booking.status = 'reserved' if status == 'paid' else booking.status
                    booking.save()
            
        except Exception as e:
            logger.error(f"Error updating payment status: {str(e)}")


# ==================== Sector-Specific Payment Views ====================

class EducationFeePaymentView(APIView):
    """Create Razorpay order for education fee payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            if not tenant.has_razorpay_configured():
                return Response({
                    'error': 'Razorpay is not configured. Please complete the setup wizard.',
                    'setup_required': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from education.models import FeePayment
            fee_payment = FeePayment.objects.select_related('student', 'fee_structure', 'student__assigned_class', 'fee_structure__class_obj').get(id=payment_id, tenant=tenant)
            
            # Create Razorpay order
            if razorpay is None:
                return Response({
                    'error': 'Razorpay is not available.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
            
            amount = float(fee_payment.amount_paid)
            order_data = {
                'amount': int(amount * 100),
                'currency': 'INR',
                'payment_capture': 1,
                'receipt': f"FEE-{fee_payment.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'notes': {
                    'sector': 'education',
                    'reference_id': str(fee_payment.id),
                    'student_id': str(fee_payment.student.id),
                    'student_name': fee_payment.student.name,
                    'fee_type': fee_payment.fee_structure.fee_type,
                    'tenant_id': str(tenant.id)
                }
            }
            
            order = client.order.create(data=order_data)
            
            return Response({
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'key_id': tenant.razorpay_key_id,
                'receipt': order.get('receipt'),
                'fee_payment_id': fee_payment.id,
                'student_name': fee_payment.student.name,
                'amount_display': f"₹{amount:.2f}"
            }, status=status.HTTP_201_CREATED)
            
        except FeePayment.DoesNotExist:
            return Response({
                'error': 'Fee payment not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating fee payment order: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RestaurantOrderPaymentView(APIView):
    """Create Razorpay order for restaurant order payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            if not tenant.has_razorpay_configured():
                return Response({
                    'error': 'Razorpay is not configured. Please complete the setup wizard.',
                    'setup_required': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from restaurant.models import Order
            order = Order.objects.select_related('table', 'tenant').prefetch_related('items', 'items__menu_item').get(id=order_id, tenant=tenant)
            
            if razorpay is None:
                return Response({
                    'error': 'Razorpay is not available.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
            
            amount = float(order.total_amount)
            order_data = {
                'amount': int(amount * 100),
                'currency': 'INR',
                'payment_capture': 1,
                'receipt': f"ORD-{order.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'notes': {
                    'sector': 'restaurant',
                    'reference_id': str(order.id),
                    'customer_name': order.customer_name,
                    'order_type': order.order_type,
                    'tenant_id': str(tenant.id)
                }
            }
            
            razorpay_order = client.order.create(data=order_data)
            
            return Response({
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'key_id': tenant.razorpay_key_id,
                'receipt': razorpay_order.get('receipt'),
                'restaurant_order_id': order.id,
                'customer_name': order.customer_name,
                'amount_display': f"₹{amount:.2f}"
            }, status=status.HTTP_201_CREATED)
            
        except Order.DoesNotExist:
            return Response({
                'error': 'Order not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating restaurant order payment: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SalonAppointmentPaymentView(APIView):
    """Create Razorpay order for salon appointment payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, appointment_id):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            if not tenant.has_razorpay_configured():
                return Response({
                    'error': 'Razorpay is not configured. Please complete the setup wizard.',
                    'setup_required': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from salon.models import Appointment
            appointment = Appointment.objects.select_related('service', 'stylist').get(id=appointment_id, tenant=tenant)
            
            if razorpay is None:
                return Response({
                    'error': 'Razorpay is not available.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
            
            amount = float(appointment.price)
            order_data = {
                'amount': int(amount * 100),
                'currency': 'INR',
                'payment_capture': 1,
                'receipt': f"APT-{appointment.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'notes': {
                    'sector': 'salon',
                    'reference_id': str(appointment.id),
                    'customer_name': appointment.customer_name,
                    'service_name': appointment.service.name if appointment.service else '',
                    'tenant_id': str(tenant.id)
                }
            }
            
            razorpay_order = client.order.create(data=order_data)
            
            return Response({
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'key_id': tenant.razorpay_key_id,
                'receipt': razorpay_order.get('receipt'),
                'appointment_id': appointment.id,
                'customer_name': appointment.customer_name,
                'service_name': appointment.service.name if appointment.service else '',
                'amount_display': f"₹{amount:.2f}"
            }, status=status.HTTP_201_CREATED)
            
        except Appointment.DoesNotExist:
            return Response({
                'error': 'Appointment not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating salon appointment payment: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PharmacySalePaymentView(APIView):
    """Create Razorpay order for pharmacy sale payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, sale_id):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            if not tenant.has_razorpay_configured():
                return Response({
                    'error': 'Razorpay is not configured. Please complete the setup wizard.',
                    'setup_required': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from pharmacy.models import Sale
            sale = Sale.objects.select_related('customer', 'tenant', 'sold_by', 'sold_by__user').prefetch_related('items', 'items__medicine_batch', 'items__medicine_batch__medicine').get(id=sale_id, tenant=tenant)
            
            if razorpay is None:
                return Response({
                    'error': 'Razorpay is not available.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
            
            amount = float(sale.total_amount)
            order_data = {
                'amount': int(amount * 100),
                'currency': 'INR',
                'payment_capture': 1,
                'receipt': f"PHARM-{sale.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'notes': {
                    'sector': 'pharmacy',
                    'reference_id': str(sale.id),
                    'customer_name': sale.customer.name if sale.customer else '',
                    'tenant_id': str(tenant.id)
                }
            }
            
            razorpay_order = client.order.create(data=order_data)
            
            return Response({
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'key_id': tenant.razorpay_key_id,
                'receipt': razorpay_order.get('receipt'),
                'sale_id': sale.id,
                'amount_display': f"₹{amount:.2f}"
            }, status=status.HTTP_201_CREATED)
            
        except Sale.DoesNotExist:
            return Response({
                'error': 'Sale not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating pharmacy sale payment: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetailSalePaymentView(APIView):
    """Create Razorpay order for retail sale payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, sale_id):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            if not tenant.has_razorpay_configured():
                return Response({
                    'error': 'Razorpay is not configured. Please complete the setup wizard.',
                    'setup_required': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from retail.models import Sale
            sale = Sale.objects.select_related('customer', 'warehouse', 'tenant', 'sold_by', 'sold_by__user').prefetch_related('items', 'items__product').get(id=sale_id, tenant=tenant)
            
            if razorpay is None:
                return Response({
                    'error': 'Razorpay is not available.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
            
            amount = float(sale.total_amount)
            order_data = {
                'amount': int(amount * 100),
                'currency': 'INR',
                'payment_capture': 1,
                'receipt': f"RETAIL-{sale.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'notes': {
                    'sector': 'retail',
                    'reference_id': str(sale.id),
                    'customer_name': sale.customer.name if sale.customer else '',
                    'tenant_id': str(tenant.id)
                }
            }
            
            razorpay_order = client.order.create(data=order_data)
            
            return Response({
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'key_id': tenant.razorpay_key_id,
                'receipt': razorpay_order.get('receipt'),
                'sale_id': sale.id,
                'amount_display': f"₹{amount:.2f}"
            }, status=status.HTTP_201_CREATED)
            
        except Sale.DoesNotExist:
            return Response({
                'error': 'Sale not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating retail sale payment: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HotelBookingPaymentView(APIView):
    """Create Razorpay order for hotel booking payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            if not tenant.has_razorpay_configured():
                return Response({
                    'error': 'Razorpay is not configured. Please complete the setup wizard.',
                    'setup_required': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from hotel.models import Booking
            booking = Booking.objects.select_related('room', 'room__room_type', 'guest', 'tenant').get(id=booking_id, tenant=tenant)
            
            if razorpay is None:
                return Response({
                    'error': 'Razorpay is not available.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
            
            amount = float(booking.total_amount)
            order_data = {
                'amount': int(amount * 100),
                'currency': 'INR',
                'payment_capture': 1,
                'receipt': f"HOTEL-{booking.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                'notes': {
                    'sector': 'hotel',
                    'reference_id': str(booking.id),
                    'guest_name': booking.guest.name if booking.guest else '',
                    'room_number': booking.room.room_number if booking.room else '',
                    'tenant_id': str(tenant.id)
                }
            }
            
            razorpay_order = client.order.create(data=order_data)
            
            return Response({
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'key_id': tenant.razorpay_key_id,
                'receipt': razorpay_order.get('receipt'),
                'booking_id': booking.id,
                'guest_name': booking.guest.name if booking.guest else '',
                'amount_display': f"₹{amount:.2f}"
            }, status=status.HTTP_201_CREATED)
            
        except Booking.DoesNotExist:
            return Response({
                'error': 'Booking not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating hotel booking payment: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


