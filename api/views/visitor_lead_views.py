from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from api.models.visitor_lead import VisitorLead
from api.serializers_visitor_lead import VisitorLeadSerializer


class VisitorLeadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VisitorLead.objects.all()
    serializer_class = VisitorLeadSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None
    filterset_fields = (
        'form_submitted',
        'utm_source',
        'utm_campaign',
        'utm_medium',
    )
    ordering_fields = ('created_at', 'last_seen')
    ordering = ('-created_at',)

