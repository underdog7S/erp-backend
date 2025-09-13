from rest_framework import viewsets, permissions
from api.models.invoice import Invoice, InvoiceItem, InvoicePayment
from api.models.serializers import InvoiceSerializer, InvoiceItemSerializer, InvoicePaymentSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

class InvoiceItemViewSet(viewsets.ModelViewSet):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [permissions.IsAuthenticated]

class InvoicePaymentViewSet(viewsets.ModelViewSet):
    queryset = InvoicePayment.objects.all()
    serializer_class = InvoicePaymentSerializer
    permission_classes = [permissions.IsAuthenticated] 