from rest_framework import serializers
from api.models.invoice import Invoice, InvoiceItem, InvoicePayment
from api.models.user import UserProfile
from api.models.payments import PaymentTransaction

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'
        # status/amount_paid/paid_at/subtotal/tax_amount/total_amount are
        # derived by Invoice.calculate_totals()/InvoicePayment.save() and must
        # not be settable directly by a client (would otherwise let a caller
        # mark any invoice PAID without an actual InvoicePayment).
        read_only_fields = [
            'tenant', 'status', 'amount_paid', 'paid_at',
            'subtotal', 'tax_amount', 'total_amount', 'created_by',
        ]

class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = '__all__'
        read_only_fields = ['subtotal', 'discount_amount', 'total']

class InvoicePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoicePayment
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = '__all__'
        read_only_fields = ['status', 'verified_at', 'user', 'tenant'] 