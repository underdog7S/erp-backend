try:
    import razorpay
except ImportError:
    razorpay = None
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, authentication_classes
import hmac
import hashlib
from api.models.user import UserProfile, Tenant
from api.models.plan import Plan
from api.models.payments import PaymentTransaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import json
from rest_framework import viewsets
from api.models.serializers import PaymentTransactionSerializer

class RazorpayOrderCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if razorpay is available
        if razorpay is None:
            return Response({'error': 'Razorpay is not available. Please check configuration.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Check if Razorpay keys are configured
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            return Response({'error': 'Razorpay keys not configured. Please contact administrator.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Get amount and currency from request data
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'INR')
        receipt = request.data.get('receipt', None)
        
        if not amount:
            return Response({'error': 'Amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate amount
            amount_float = float(amount)
            if amount_float <= 0:
                return Response({'error': 'Amount must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_data = {
                'amount': int(amount_float * 100),  # Razorpay expects paise
                'currency': currency,
                'payment_capture': 1,
            }
            if receipt:
                order_data['receipt'] = receipt
            order = client.order.create(data=order_data)
            return Response({'order': order}, status=status.HTTP_201_CREATED)
        except ValueError:
            return Response({'error': 'Invalid amount format.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Payment order creation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RazorpayPaymentVerifyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')
        plan_name = request.data.get('plan')  # Expect plan name from frontend (e.g., 'pro', 'starter')
        if not (payment_id and order_id and signature):
            return Response({'error': 'Missing payment verification data.'}, status=status.HTTP_400_BAD_REQUEST)
        # Prevent duplicate payment processing
        if PaymentTransaction._default_manager.filter(order_id=order_id).exists() or PaymentTransaction._default_manager.filter(payment_id=payment_id).exists():
            return Response({'error': 'This payment has already been processed.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Verify signature
            key_secret = settings.RAZORPAY_KEY_SECRET
            msg = f"{order_id}|{payment_id}"
            generated_signature = hmac.new(
                key_secret.encode(),
                msg.encode(),
                hashlib.sha256
            ).hexdigest()
            if generated_signature == signature:
                # Activate user plan
                try:
                    profile = UserProfile._default_manager.get(user=request.user)
                except UserProfile._default_manager.model.DoesNotExist:
                    return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
                tenant = profile.tenant
                plan = None
                if plan_name:
                    try:
                        plan = Plan._default_manager.get(name__iexact=plan_name)
                        tenant.plan = plan
                        
                        # Calculate subscription expiration date based on billing cycle
                        today = timezone.now().date()
                        
                        # Check if this is a renewal (existing subscription not expired)
                        is_renewal = False
                        if tenant.subscription_end_date and tenant.subscription_end_date >= today:
                            is_renewal = True
                        
                        if plan.billing_cycle == 'annual':
                            # 1 year (365 days)
                            if is_renewal:
                                # Extend from existing expiration date
                                tenant.subscription_end_date = tenant.subscription_end_date + timedelta(days=365)
                            else:
                                # New subscription or expired plan - start from today
                                tenant.subscription_start_date = today
                                tenant.subscription_end_date = today + timedelta(days=365)
                        elif plan.billing_cycle == 'monthly':
                            # 1 month (30 days)
                            if is_renewal:
                                tenant.subscription_end_date = tenant.subscription_end_date + timedelta(days=30)
                            else:
                                tenant.subscription_start_date = today
                                tenant.subscription_end_date = today + timedelta(days=30)
                        else:
                            # Custom or default to 30 days
                            if is_renewal and tenant.subscription_end_date:
                                tenant.subscription_end_date = tenant.subscription_end_date + timedelta(days=30)
                            else:
                                tenant.subscription_start_date = today
                                tenant.subscription_end_date = today + timedelta(days=30)
                        
                        # Update subscription status
                        tenant.subscription_status = 'active'
                        tenant.grace_period_end_date = None  # Clear grace period if exists
                        tenant.save()
                    except Plan._default_manager.model.DoesNotExist:
                        return Response({'error': 'Selected plan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
                # Store transaction record
                PaymentTransaction._default_manager.create(
                    user=request.user,
                    tenant=tenant,
                    plan=plan,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature=signature,
                    amount=request.data.get('amount', 0),
                    currency=request.data.get('currency', 'INR'),
                    status='verified',
                    verified_at=timezone.now(),
                )
                return Response({'success': True, 'message': 'Payment verified, plan activated, and transaction stored.'})
            else:
                return Response({'error': 'Invalid payment signature.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RazorpayWebhookView(APIView):
    authentication_classes = []  # No auth for webhooks
    permission_classes = []

    @csrf_exempt
    def post(self, request):
        try:
            payload = request.body.decode('utf-8')
            event = json.loads(payload)
            # Example: handle payment.captured event
            if event.get('event') == 'payment.captured':
                payment_entity = event['payload']['payment']['entity']
                payment_id = payment_entity['id']
                amount = payment_entity['amount'] / 100.0
                currency = payment_entity['currency']
                # Update transaction status if exists
                PaymentTransaction._default_manager.filter(payment_id=payment_id).update(status='captured')
            return Response({'status': 'webhook received'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PaymentTransactionViewSet(viewsets.ModelViewSet):
    queryset = PaymentTransaction.objects.all().order_by('id')  # Add ordering for pagination warning
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        profile = UserProfile._default_manager.get(user=request.user)
        if not profile.role or profile.role.name != 'admin':
            return Response({'error': 'Permission denied.'}, status=403)
        return super().destroy(request, *args, **kwargs)

class PaymentReceiptPDFView(APIView):
    """Generate PDF receipt for a plan purchase payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            transaction = PaymentTransaction._default_manager.get(id=pk)
            
            # Check permissions - user can only download their own receipts or admin can download any
            if transaction.user != request.user and (not profile.role or profile.role.name != 'admin'):
                return Response({'error': 'Permission denied. You can only download your own receipts.'}, status=status.HTTP_403_FORBIDDEN)
        except PaymentTransaction.DoesNotExist:
            return Response({'error': 'Payment transaction not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from io import BytesIO
            from django.http import HttpResponse
            from django.utils import timezone

            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            # Get tenant and company info
            tenant = transaction.tenant
            company_name = getattr(tenant, 'name', '') or 'Zenith ERP'
            
            # Get company contact information from admin user profile
            company_address = ''
            company_phone = ''
            company_email = ''
            try:
                # Get admin user profile for contact info
                admin_profile = UserProfile._default_manager.filter(
                    tenant=tenant, 
                    role__name='admin'
                ).first()
                if admin_profile:
                    company_address = admin_profile.address or ''
                    company_phone = admin_profile.phone or ''
                    company_email = admin_profile.user.email if admin_profile.user else ''
            except Exception:
                pass
            
            # Draw logo on LEFT side (improved positioning and size)
            logo_drawn = False
            logo_width = 0
            logo_height_used = 0
            if tenant.logo:
                try:
                    from PIL import Image
                    import os
                    logo_path = tenant.logo.path
                    if os.path.exists(logo_path):
                        img = Image.open(logo_path)
                        # Resize logo to better size (max 35mm height for better visibility)
                        max_height = 35 * mm
                        img_width, img_height = img.size
                        scale = min(max_height / img_height, max_height / img_width)
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        from reportlab.lib.utils import ImageReader
                        logo_reader = ImageReader(img)
                        # Position on LEFT side with proper margin
                        logo_x = 25 * mm
                        logo_y = height - 25 - new_height
                        p.drawImage(logo_reader, logo_x, logo_y, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
                        logo_drawn = True
                        logo_width = new_width + 10 * mm  # Add spacing after logo
                        logo_height_used = new_height
                except Exception as e:
                    logger.warning(f"Could not load tenant logo: {e}")
            
            # Company name and info on RIGHT of logo (or left if no logo)
            p.setFillColor(colors.black)
            if logo_drawn:
                # Text aligned to RIGHT of logo
                text_x = 25 * mm + logo_width
                p.setFont('Helvetica-Bold', 18)
                company_y = height - 25
                p.drawString(text_x, company_y, company_name.upper())
                
                # Company contact info below name
                info_y = company_y - 16
                p.setFont('Helvetica', 9)
                if company_address:
                    # Truncate address if too long
                    max_addr_width = width - text_x - 25 * mm
                    if p.stringWidth(company_address, 'Helvetica', 9) > max_addr_width:
                        addr_lines = [company_address[i:i+50] for i in range(0, min(len(company_address), 100), 50)]
                        for line in addr_lines[:2]:  # Max 2 lines
                            p.drawString(text_x, info_y, line)
                            info_y -= 11
                    else:
                        p.drawString(text_x, info_y, company_address)
                        info_y -= 11
                if company_phone:
                    p.drawString(text_x, info_y, f"Phone: {company_phone}")
                    info_y -= 11
                if company_email:
                    p.drawString(text_x, info_y, f"Email: {company_email}")
                    info_y -= 11
                
                # Document title below contact info
                info_y -= 5
                p.setFont('Helvetica-Bold', 11)
                p.drawString(text_x, info_y, 'PAYMENT RECEIPT - PRODUCT SUBSCRIPTION')
            else:
                # Left-aligned if no logo
                text_x = 25 * mm
                p.setFont('Helvetica-Bold', 20)
                company_y = height - 25
                p.drawString(text_x, company_y, company_name.upper())
                
                info_y = company_y - 16
                p.setFont('Helvetica', 9)
                if company_address:
                    p.drawString(text_x, info_y, company_address[:60])
                    info_y -= 11
                if company_phone:
                    p.drawString(text_x, info_y, f"Phone: {company_phone}")
                    info_y -= 11
                if company_email:
                    p.drawString(text_x, info_y, f"Email: {company_email}")
                    info_y -= 11
                
                info_y -= 5
                p.setFont('Helvetica-Bold', 12)
                p.drawString(text_x, info_y, 'PAYMENT RECEIPT - PRODUCT SUBSCRIPTION')
            
            # Adjust starting y position based on header height
            if logo_drawn:
                header_bottom = info_y - 15  # Document title + spacing
            else:
                header_bottom = info_y - 5
            y = header_bottom - 20  # Add spacing before first section
            p.setFillColor(colors.black)

            # Receipt details section
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(20 * mm, y - 40, width - 40 * mm, 40, stroke=1, fill=0)
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 8, 'PAYMENT DETAILS')
            y -= 18
            
            receipt_number = f"PYT-{transaction.id:08X}"
            payment_date = transaction.verified_at.strftime('%d/%m/%Y') if transaction.verified_at else transaction.created_at.strftime('%d/%m/%Y')
            
            # IMPROVED: Better spacing to prevent overlapping
            label_x = 25 * mm
            value_x = 100 * mm  # Increased spacing
            label_x2 = 140 * mm  # Increased spacing
            value_x2 = 175 * mm  # Increased spacing (reduced to prevent overflow)
            
            # First row: Receipt Number and Payment Date
            p.setFont('Helvetica-Bold', 11)
            p.drawString(label_x, y, 'Receipt Number:')
            p.setFont('Helvetica', 11)
            receipt_text = receipt_number
            # Ensure receipt number doesn't exceed column boundary
            max_receipt_width = label_x2 - value_x - 10 * mm
            if p.stringWidth(receipt_text, 'Helvetica', 11) > max_receipt_width:
                receipt_text = receipt_text[:15] + '...'
            p.drawString(value_x, y, receipt_text)
            
            p.setFont('Helvetica-Bold', 11)
            p.drawString(label_x2, y, 'Payment Date:')
            p.setFont('Helvetica', 11)
            date_text = payment_date
            # Ensure date doesn't exceed page width
            max_date_x = width - 25 * mm
            if value_x2 + p.stringWidth(date_text, 'Helvetica', 11) > max_date_x:
                value_x2_date = max_date_x - p.stringWidth(date_text, 'Helvetica', 11)
            else:
                value_x2_date = value_x2
            p.drawString(value_x2_date, y, date_text)
            y -= 20  # Increased line spacing
            
            # Second row: Order ID and Payment ID
            p.setFont('Helvetica-Bold', 11)
            p.drawString(label_x, y, 'Order ID:')
            p.setFont('Helvetica', 10)
            order_text = transaction.order_id
            # Ensure order ID doesn't exceed column boundary
            if p.stringWidth(order_text, 'Helvetica', 10) > max_receipt_width:
                order_text = order_text[:20] + '...'
            p.drawString(value_x, y, order_text)
            
            p.setFont('Helvetica-Bold', 11)
            p.drawString(label_x2, y, 'Payment ID:')
            p.setFont('Helvetica', 10)
            payment_id_text = transaction.payment_id[:20] + '...' if len(transaction.payment_id) > 20 else transaction.payment_id
            # Ensure payment ID doesn't exceed page width
            if value_x2 + p.stringWidth(payment_id_text, 'Helvetica', 10) > max_date_x:
                value_x2_payment = max_date_x - p.stringWidth(payment_id_text, 'Helvetica', 10)
            else:
                value_x2_payment = value_x2
            p.drawString(value_x2_payment, y, payment_id_text)
            y -= 25  # Increased spacing after section

            # Customer information section
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(20 * mm, y - 50, width - 40 * mm, 50, stroke=1, fill=0)
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 8, 'CUSTOMER INFORMATION')
            y -= 18
            
            customer_name = transaction.user.get_full_name() or transaction.user.username
            customer_email = transaction.user.email or 'N/A'
            tenant_name = transaction.tenant.name if transaction.tenant else 'N/A'
            
            # IMPROVED: Better spacing with proper column boundaries
            label_x = 25 * mm
            value_x = 100 * mm  # Increased spacing
            label_x2 = 140 * mm  # Increased spacing
            value_x2 = 175 * mm  # Increased spacing (reduced to prevent overflow)
            max_right_x = width - 25 * mm
            
            # First row: Customer Name and Email
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Customer Name:')
            p.setFont('Helvetica', 10)
            name_text = customer_name.upper()
            # Truncate if too long
            max_name_width = label_x2 - value_x - 10 * mm
            if p.stringWidth(name_text, 'Helvetica', 10) > max_name_width:
                while p.stringWidth(name_text, 'Helvetica', 10) > max_name_width and len(name_text) > 1:
                    name_text = name_text[:-1]
                name_text = name_text.rstrip() + '...'
            p.drawString(value_x, y, name_text)
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Email:')
            p.setFont('Helvetica', 10)
            email_text = customer_email
            # Ensure email doesn't exceed page width
            if value_x2 + p.stringWidth(email_text, 'Helvetica', 10) > max_right_x:
                value_x2_email = max_right_x - p.stringWidth(email_text, 'Helvetica', 10)
            else:
                value_x2_email = value_x2
            p.drawString(value_x2_email, y, email_text)
            y -= 18  # Increased line spacing
            
            # Second row: Organization and Plan
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Organization:')
            p.setFont('Helvetica', 10)
            org_text = tenant_name
            # Ensure organization name doesn't exceed column boundary
            if p.stringWidth(org_text, 'Helvetica', 10) > max_name_width:
                while p.stringWidth(org_text, 'Helvetica', 10) > max_name_width and len(org_text) > 1:
                    org_text = org_text[:-1]
                org_text = org_text.rstrip() + '...'
            p.drawString(value_x, y, org_text)
            
            plan_name = transaction.plan.name if transaction.plan else 'N/A'
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Plan:')
            p.setFont('Helvetica', 10)
            plan_text = plan_name
            # Ensure plan name doesn't exceed page width
            if value_x2 + p.stringWidth(plan_text, 'Helvetica', 10) > max_right_x:
                value_x2_plan = max_right_x - p.stringWidth(plan_text, 'Helvetica', 10)
            else:
                value_x2_plan = value_x2
            p.drawString(value_x2_plan, y, plan_text)
            y -= 30  # Increased spacing after section

            # Payment information section
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(20 * mm, y - 90, width - 40 * mm, 90, stroke=1, fill=0)
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 8, 'SUBSCRIPTION DETAILS')
            y -= 18
            
            amount_paid = float(transaction.amount)
            currency = transaction.currency or 'INR'
            billing_cycle = transaction.plan.billing_cycle if transaction.plan else 'N/A'
            
            # IMPROVED: Better spacing to prevent overlapping
            label_x = 25 * mm
            value_x = 100 * mm  # Increased spacing
            label_x2 = 140 * mm  # Increased spacing
            value_x2 = 175 * mm  # Increased spacing (reduced to prevent overflow)
            currency_x = width - 25 * mm
            max_right_x = width - 25 * mm
            
            # First row: Plan Name and Billing Cycle
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Plan Name:')
            p.setFont('Helvetica', 10)
            plan_display_text = plan_name
            # Ensure plan name doesn't exceed column boundary
            max_plan_width = label_x2 - value_x - 10 * mm
            if p.stringWidth(plan_display_text, 'Helvetica', 10) > max_plan_width:
                while p.stringWidth(plan_display_text, 'Helvetica', 10) > max_plan_width and len(plan_display_text) > 1:
                    plan_display_text = plan_display_text[:-1]
                plan_display_text = plan_display_text.rstrip() + '...'
            p.drawString(value_x, y, plan_display_text)
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Billing Cycle:')
            p.setFont('Helvetica', 10)
            cycle_text = billing_cycle.upper()
            # Ensure billing cycle doesn't exceed page width
            if value_x2 + p.stringWidth(cycle_text, 'Helvetica', 10) > max_right_x:
                value_x2_cycle = max_right_x - p.stringWidth(cycle_text, 'Helvetica', 10)
            else:
                value_x2_cycle = value_x2
            p.drawString(value_x2_cycle, y, cycle_text)
            y -= 18  # Increased line spacing
            
            # Second row: Currency and Status
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Currency:')
            p.setFont('Helvetica', 10)
            currency_text = currency
            p.drawString(value_x, y, currency_text)
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Status:')
            p.setFont('Helvetica', 10)
            status_text = transaction.status.upper() if transaction.status else 'VERIFIED'
            # Ensure status doesn't exceed page width
            if value_x2 + p.stringWidth(status_text, 'Helvetica', 10) > max_right_x:
                value_x2_status = max_right_x - p.stringWidth(status_text, 'Helvetica', 10)
            else:
                value_x2_status = value_x2
            p.drawString(value_x2_status, y, status_text)
            y -= 25  # Increased spacing after section
            
            # Important notice about charges
            p.setFont('Helvetica-Bold', 11)
            p.drawString(25 * mm, y, 'IMPORTANT: CHARGE BREAKDOWN')
            y -= 15
            p.setFont('Helvetica', 9)
            notice_lines = [
                "• This payment is for PRODUCT SUBSCRIPTION charges only.",
                "• Training services are NOT included and require separate payment.",
                "• Customization services (PC apps, PLC programming, etc.) have different pricing.",
                "• API-based integrations and web creation services are charged separately.",
                "• All additional services require separate quotes and agreements."
            ]
            for line in notice_lines:
                p.drawString(30 * mm, y, line)
                y -= 12
            y -= 15

            # Total amount section
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1.5)
            p.rect(20 * mm, y - 35, width - 40 * mm, 35, stroke=1, fill=0)
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 14)
            p.drawString(25 * mm, y - 12, 'TOTAL AMOUNT PAID:')
            p.setFont('Helvetica-Bold', 18)
            p.drawRightString(width - 25 * mm, y - 10, f"₹{amount_paid:.2f}")
            y -= 45

            # Additional services and policies section
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(20 * mm, y - 120, width - 40 * mm, 120, stroke=1, fill=0)
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 11)
            p.drawString(25 * mm, y - 8, 'ADDITIONAL SERVICES & POLICIES')
            y -= 18
            
            p.setFont('Helvetica-Bold', 9)
            p.drawString(25 * mm, y, 'Training Services:')
            y -= 12
            p.setFont('Helvetica', 8)
            training_text = [
                "Training is a separate service with dedicated pricing. Training charges are not included",
                "in this subscription. Please contact support for training packages and pricing."
            ]
            for line in training_text:
                p.drawString(30 * mm, y, line)
                y -= 11
            
            y -= 5
            p.setFont('Helvetica-Bold', 9)
            p.drawString(25 * mm, y, 'Customization Services:')
            y -= 12
            p.setFont('Helvetica', 8)
            custom_text = [
                "Custom development services (PC applications, PLC programming, TCP/IP & Ethernet PLC",
                "connections, custom workflows) are available at additional costs. Each customization",
                "project is quoted separately based on requirements and complexity."
            ]
            for line in custom_text:
                p.drawString(30 * mm, y, line)
                y -= 11
            
            y -= 5
            p.setFont('Helvetica-Bold', 9)
            p.drawString(25 * mm, y, 'API & Web Development:')
            y -= 12
            p.setFont('Helvetica', 8)
            api_text = [
                "API-based integrations and custom web application development are separate services",
                "with different pricing structures. Contact our sales team for API integration and",
                "web development service quotes."
            ]
            for line in api_text:
                p.drawString(30 * mm, y, line)
                y -= 11
            
            y -= 25

            # Footer with policies
            p.setFont('Helvetica', 8)
            p.setFillColor(colors.black)
            footer_text = f"Generated on {timezone.now().strftime('%d-%m-%Y at %I:%M %p')} — {company_name.upper()}"
            p.drawCentredString(width / 2, 25 * mm, footer_text)
            p.setFont('Helvetica-Oblique', 7)
            policy_line1 = "For detailed pricing on training, customization, API, and web services, please contact support."
            policy_line2 = "This is a computer-generated receipt and does not require a physical signature."
            p.drawCentredString(width / 2, 18 * mm, policy_line1)
            p.drawCentredString(width / 2, 12 * mm, policy_line2)

            p.showPage()
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            receipt_filename = f"payment_receipt_{receipt_number}_{transaction.id}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{receipt_filename}"'
            return response
        except ImportError as e:
            logger.error(f"PDF generation import error: {str(e)}", exc_info=True)
            return Response({
                'error': 'PDF generation library not installed.',
                'details': 'Install required packages: pip install reportlab Pillow',
                'missing': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error generating receipt PDF: {str(e)}", exc_info=True)
            return Response({
                'error': f'Receipt PDF generation failed: {str(e)}',
                'details': 'Check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 