from rest_framework import serializers

from api.models.visitor_lead import VisitorLead


class VisitorLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorLead
        fields = [
            'id',
            'visitor_token',
            'ip_address',
            'user_agent',
            'landing_url',
            'referrer',
            'utm_source',
            'utm_medium',
            'utm_campaign',
            'utm_term',
            'utm_content',
            'form_submitted',
            'submitted_name',
            'submitted_email',
            'submitted_phone',
            'notes',
            'created_at',
            'last_seen',
        ]

