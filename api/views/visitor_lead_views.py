from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from api.models.visitor_lead import VisitorLead
from api.serializers_visitor_lead import VisitorLeadSerializer


from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny

class VisitorLeadViewSet(viewsets.ModelViewSet):
    """Marketing-site leads for the vendor's own sales team - these aren't
    scoped to any tenant, so access must be restricted to internal staff
    (is_staff), not IsTenantAdmin, which would let any paying customer's
    admin list every other prospect's PII."""
    queryset = VisitorLead.objects.all()
    serializer_class = VisitorLeadSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminUser()]
    filterset_fields = (
        'form_submitted',
        'utm_source',
        'utm_campaign',
        'utm_medium',
    )
    ordering_fields = ('created_at', 'last_seen')
    ordering = ('-created_at',)

