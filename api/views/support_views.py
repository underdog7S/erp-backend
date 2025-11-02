"""
Support ticket and SLA views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.models.permissions import IsTenantMember
from api.models.support import SupportTicket, TicketResponse, TicketSLA
from django.contrib.auth.models import User
from django.db.models import Q


class TicketSLAViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Ticket SLA configurations
    Only accessible by tenant admins
    """
    permission_classes = [IsAuthenticated, IsTenantMember]
    serializer_class = None  # Will be defined below
    
    def get_queryset(self):
        """Filter SLAs by user's tenant"""
        try:
            from api.models.user import UserProfile
            profile = UserProfile.objects.get(user=self.request.user)
            return TicketSLA.objects.filter(tenant=profile.tenant)
        except:
            return TicketSLA.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        from rest_framework import serializers
        
        class TicketSLASerializer(serializers.ModelSerializer):
            class Meta:
                model = TicketSLA
                fields = [
                    'id', 'tenant', 'category', 'priority', 
                    'first_response_hours', 'resolution_hours',
                    'escalation_hours', 'escalation_to', 'is_active'
                ]
                read_only_fields = ['tenant']
        
        return TicketSLASerializer
    
    def perform_create(self, serializer):
        """Set tenant automatically"""
        from rest_framework import serializers
        try:
            from api.models.user import UserProfile
            profile = UserProfile.objects.get(user=self.request.user)
            serializer.save(tenant=profile.tenant)
        except Exception as e:
            raise serializers.ValidationError(f"Failed to set tenant: {str(e)}")


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing support tickets
    """
    permission_classes = [IsAuthenticated, IsTenantMember]
    serializer_class = None
    
    def get_queryset(self):
        """Filter tickets by user's tenant"""
        try:
            from api.models.user import UserProfile
            profile = UserProfile.objects.get(user=self.request.user)
            tenant = profile.tenant
            
            # Regular users see only their tickets, admins see all tenant tickets
            if profile.role and profile.role.name == 'admin':
                return SupportTicket.objects.filter(tenant=tenant)
            else:
                return SupportTicket.objects.filter(tenant=tenant, user=self.request.user)
        except:
            return SupportTicket.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        from rest_framework import serializers
        
        class SupportTicketSerializer(serializers.ModelSerializer):
            class Meta:
                model = SupportTicket
                fields = [
                    'id', 'ticket_number', 'tenant', 'user', 'subject', 'description',
                    'category', 'priority', 'status', 'assigned_to',
                    'created_at', 'updated_at', 'resolved_at',
                    'due_date', 'response_time', 'resolution_time',
                    'tawk_conversation_id', 'tawk_visitor_id'
                ]
                read_only_fields = ['ticket_number', 'tenant', 'user', 'created_at', 'updated_at']
        
        return SupportTicketSerializer
    
    def perform_create(self, serializer):
        """Set user and tenant automatically"""
        from rest_framework import serializers
        try:
            from api.models.user import UserProfile
            profile = UserProfile.objects.get(user=self.request.user)
            serializer.save(user=self.request.user, tenant=profile.tenant)
        except Exception as e:
            raise serializers.ValidationError(f"Failed to create ticket: {str(e)}")


class TicketResponseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ticket responses
    """
    permission_classes = [IsAuthenticated, IsTenantMember]
    serializer_class = None
    
    def get_queryset(self):
        """Filter responses by ticket's tenant"""
        try:
            from api.models.user import UserProfile
            profile = UserProfile.objects.get(user=self.request.user)
            tenant = profile.tenant
            
            # Regular users see responses to their tickets, admins see all
            if profile.role and profile.role.name == 'admin':
                return TicketResponse.objects.filter(ticket__tenant=tenant)
            else:
                return TicketResponse.objects.filter(
                    ticket__tenant=tenant,
                    ticket__user=self.request.user
                )
        except:
            return TicketResponse.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        from rest_framework import serializers
        
        class TicketResponseSerializer(serializers.ModelSerializer):
            class Meta:
                model = TicketResponse
                fields = [
                    'id', 'ticket', 'user', 'message', 'is_internal',
                    'attachment', 'created_at'
                ]
                read_only_fields = ['user', 'created_at']
        
        return TicketResponseSerializer
    
    def perform_create(self, serializer):
        """Set user automatically"""
        serializer.save(user=self.request.user)

