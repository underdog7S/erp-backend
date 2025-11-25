"""
Support ticket and SLA views
"""
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.models.permissions import IsTenantMember
from api.models.support import SupportTicket, TicketResponse, TicketSLA
from django.contrib.auth.models import User
from django.db.models import Q


class TicketSLASerializer(serializers.ModelSerializer):
    """Serializer for TicketSLA"""
    class Meta:
        model = TicketSLA
        fields = [
            'id', 'tenant', 'category', 'priority', 
            'first_response_hours', 'resolution_hours',
            'escalation_hours', 'escalation_to', 'is_active'
        ]
        read_only_fields = ['tenant']


class TicketSLAViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Ticket SLA configurations
    Only accessible by tenant admins
    """
    permission_classes = [IsAuthenticated, IsTenantMember]
    serializer_class = TicketSLASerializer
    
    def get_queryset(self):
        """Filter SLAs by user's tenant"""
        try:
            from api.models.user import UserProfile
            profile = UserProfile.objects.get(user=self.request.user)
            tenant = profile.tenant
            if tenant:
                return TicketSLA.objects.filter(tenant=tenant)
            return TicketSLA.objects.none()
        except UserProfile.DoesNotExist:
            return TicketSLA.objects.none()
        except Exception as e:
            # Log error but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting TicketSLA queryset: {str(e)}")
            return TicketSLA.objects.none()
    
    def perform_create(self, serializer):
        """Set tenant automatically"""
        from rest_framework import serializers as drf_serializers
        try:
            from api.models.user import UserProfile
            profile = UserProfile.objects.get(user=self.request.user)
            if not profile.tenant:
                raise drf_serializers.ValidationError("User profile has no tenant assigned")
            serializer.save(tenant=profile.tenant)
        except UserProfile.DoesNotExist:
            raise drf_serializers.ValidationError("User profile not found")
        except Exception as e:
            raise drf_serializers.ValidationError(f"Failed to set tenant: {str(e)}")


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
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get ticket statistics"""
        from api.models.user import UserProfile
        from django.db.models import Count, Avg
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            
            tickets = SupportTicket.objects.filter(tenant=tenant)
            
            # Overall stats
            total = tickets.count()
            by_status = tickets.values('status').annotate(count=Count('id'))
            by_priority = tickets.values('priority').annotate(count=Count('id'))
            by_category = tickets.values('category').annotate(count=Count('id'))
            
            # Time-based stats
            last_30_days = timezone.now() - timedelta(days=30)
            recent = tickets.filter(created_at__gte=last_30_days).count()
            resolved_recent = tickets.filter(status='RESOLVED', resolved_at__gte=last_30_days).count()
            
            # SLA stats
            overdue = tickets.filter(due_date__lt=timezone.now(), status__in=['OPEN', 'IN_PROGRESS']).count()
            
            # Average resolution time
            resolved_tickets = tickets.filter(status='RESOLVED', resolution_time__isnull=False)
            avg_resolution_hours = resolved_tickets.aggregate(avg=Avg('resolution_time'))['avg']
            if avg_resolution_hours:
                avg_resolution_hours = avg_resolution_hours.total_seconds() / 3600
            
            return Response({
                'total': total,
                'by_status': list(by_status),
                'by_priority': list(by_priority),
                'by_category': list(by_category),
                'recent_30_days': recent,
                'resolved_30_days': resolved_recent,
                'overdue': overdue,
                'average_resolution_hours': round(avg_resolution_hours, 2) if avg_resolution_hours else None,
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found'}, status=400)


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

