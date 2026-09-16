from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from api.models.invoice import Invoice, InvoiceItem, InvoicePayment
from api.models.serializers import InvoiceSerializer, InvoiceItemSerializer, InvoicePaymentSerializer
from api.models.user import UserProfile


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile = UserProfile.objects.filter(user=self.request.user).first()
        if not profile or not profile.tenant:
            return Invoice.objects.none()
        return Invoice.objects.filter(tenant=profile.tenant)

    def perform_create(self, serializer):
        profile = UserProfile.objects.filter(user=self.request.user).first()
        if not profile or not profile.tenant:
            raise PermissionDenied('No tenant associated with this account.')
        serializer.save(tenant=profile.tenant, created_by=self.request.user)


class InvoiceItemViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile = UserProfile.objects.filter(user=self.request.user).first()
        if not profile or not profile.tenant:
            return InvoiceItem.objects.none()
        return InvoiceItem.objects.filter(invoice__tenant=profile.tenant)

    def perform_create(self, serializer):
        profile = UserProfile.objects.filter(user=self.request.user).first()
        invoice = serializer.validated_data.get('invoice')
        if not profile or not profile.tenant or not invoice or invoice.tenant_id != profile.tenant_id:
            raise PermissionDenied('Invoice does not belong to your organization.')
        serializer.save()


class InvoicePaymentViewSet(viewsets.ModelViewSet):
    serializer_class = InvoicePaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile = UserProfile.objects.filter(user=self.request.user).first()
        if not profile or not profile.tenant:
            return InvoicePayment.objects.none()
        return InvoicePayment.objects.filter(invoice__tenant=profile.tenant)

    def perform_create(self, serializer):
        profile = UserProfile.objects.filter(user=self.request.user).first()
        invoice = serializer.validated_data.get('invoice')
        if not profile or not profile.tenant or not invoice or invoice.tenant_id != profile.tenant_id:
            raise PermissionDenied('Invoice does not belong to your organization.')
        serializer.save()