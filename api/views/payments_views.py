import razorpay
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
import json
from rest_framework import viewsets
from api.models.serializers import PaymentTransactionSerializer

class RazorpayOrderCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get amount and currency from request data
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'INR')
        receipt = request.data.get('receipt', None)
        if not amount:
            return Response({'error': 'Amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_data = {
                'amount': int(float(amount) * 100),  # Razorpay expects paise
                'currency': currency,
                'payment_capture': 1,
            }
            if receipt:
                order_data['receipt'] = receipt
            order = client.order.create(data=order_data)
            return Response({'order': order}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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