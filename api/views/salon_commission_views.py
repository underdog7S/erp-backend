"""Stylist commissions: booked when an appointment is completed, then marked paid out."""
from decimal import Decimal
from django.db.models import Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models.permissions import HasFeaturePermissionFactory
from salon.models import StylistCommission


def book_commission(appt):
    """Create the commission for a completed appointment (once)."""
    pct = Decimal(str(appt.stylist.commission_percent or 0))
    if pct <= 0 or StylistCommission.objects.filter(appointment=appt).exists():
        return None
    return StylistCommission.objects.create(
        tenant=appt.tenant, stylist=appt.stylist, appointment=appt,
        commission_percentage=pct, commission_amount=(appt.price * pct / 100).quantize(Decimal('0.01')))


def _row(c):
    return {
        'id': c.id, 'stylist': c.stylist_id, 'stylist_name': str(c.stylist), 'service_name': c.appointment.service.name,
        'customer_name': c.appointment.customer_name, 'date': c.appointment.start_time,
        'service_price': c.appointment.price, 'percentage': c.commission_percentage,
        'amount': c.commission_amount, 'is_paid': c.is_paid,
    }


class CommissionListView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]

    def get(self, request):
        qs = StylistCommission.objects.filter(tenant=request.user.userprofile.tenant).select_related(
            'stylist', 'appointment', 'appointment__service').order_by('-created_at')
        paid = request.query_params.get('is_paid')
        if paid in ('true', 'false'):
            qs = qs.filter(is_paid=(paid == 'true'))
        if request.query_params.get('stylist'):
            qs = qs.filter(stylist_id=request.query_params['stylist'])
        totals = {
            'unpaid': qs.filter(is_paid=False).aggregate(t=Sum('commission_amount'))['t'] or 0,
            'paid': qs.filter(is_paid=True).aggregate(t=Sum('commission_amount'))['t'] or 0,
        }
        return Response({'totals': totals, 'results': [_row(c) for c in qs[:500]]})


class CommissionPayView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]

    def post(self, request, pk):
        c = StylistCommission.objects.filter(pk=pk, tenant=request.user.userprofile.tenant).first()
        if not c:
            return Response({'error': 'Commission not found.'}, status=status.HTTP_404_NOT_FOUND)
        c.is_paid = True
        c.save(update_fields=['is_paid'])
        return Response({'ok': True})
