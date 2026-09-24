"""Kitchen display endpoints: list the live tickets and move them along queued -> preparing -> ready -> completed."""
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models.permissions import HasFeaturePermissionFactory
from restaurant.models import KDSTicket

NEXT = {'queued': ('preparing', 'completed'), 'preparing': ('ready', 'completed'), 'ready': ('completed',)}


def _row(t):
    return {
        'id': t.id, 'order': t.order_id, 'table_number': t.table_number, 'items': t.items, 'status': t.status,
        'created_at': t.created_at, 'minutes_waiting': int((timezone.now() - t.created_at).total_seconds() // 60),
        'order_type': t.order.order_type if t.order_id else None,
        'notes': t.order.notes if t.order_id else '',
    }


class KDSTicketListView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

    def get(self, request):
        tickets = KDSTicket.objects.filter(
            tenant=request.user.userprofile.tenant, status__in=['queued', 'preparing', 'ready']
        ).select_related('order').order_by('created_at')
        return Response([_row(t) for t in tickets])


class KDSTicketStatusView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

    def post(self, request, pk):
        ticket = KDSTicket.objects.filter(pk=pk, tenant=request.user.userprofile.tenant).first()
        if not ticket:
            return Response({'error': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)
        new = request.data.get('status')
        if new not in NEXT.get(ticket.status, ()):
            return Response({'error': f'A {ticket.status} ticket cannot become {new}.'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = new
        if new == 'completed':
            ticket.completed_at = timezone.now()
        ticket.save(update_fields=['status', 'completed_at'])
        return Response(_row(ticket))
