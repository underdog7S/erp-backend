from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from datetime import timedelta
import logging

from api.models.email_marketing import (
    EmailTemplate, ContactList, EmailCampaign, EmailActivity,
    EmailSequence, EmailSequenceStep
)
from api.models.user import UserProfile
from api.serializers_email import (
    EmailTemplateSerializer, ContactListSerializer, EmailCampaignSerializer,
    EmailActivitySerializer, EmailSequenceSerializer, EmailSequenceStepSerializer
)

logger = logging.getLogger(__name__)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing email templates"""
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return EmailTemplate.objects.none()
        return EmailTemplate.objects.filter(tenant=user_profile.tenant)
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(
                tenant=user_profile.tenant,
                created_by=self.request.user
            )


class ContactListViewSet(viewsets.ModelViewSet):
    """ViewSet for managing contact lists"""
    serializer_class = ContactListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return ContactList.objects.none()
        return ContactList.objects.filter(tenant=user_profile.tenant).prefetch_related('contacts')
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(
                tenant=user_profile.tenant,
                created_by=self.request.user
            )
    
    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        """Get all contacts in this list"""
        contact_list = self.get_object()
        contacts = contact_list.get_contacts()
        from api.serializers_crm import ContactSerializer
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)


class EmailCampaignViewSet(viewsets.ModelViewSet):
    """ViewSet for managing email campaigns"""
    serializer_class = EmailCampaignSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return EmailCampaign.objects.none()
        
        queryset = EmailCampaign.objects.filter(tenant=user_profile.tenant).select_related(
            'template', 'contact_list', 'created_by'
        ).prefetch_related('recipients')
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(
                tenant=user_profile.tenant,
                created_by=self.request.user
            )
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send email campaign"""
        campaign = self.get_object()
        user_profile = UserProfile.objects.filter(user=request.user).first()
        
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        if campaign.status != 'draft' and campaign.status != 'scheduled':
            return Response({'error': 'Campaign can only be sent from draft or scheduled status'}, status=400)
        
        # Get recipients
        if campaign.contact_list:
            recipients = campaign.contact_list.get_contacts()
        else:
            recipients = campaign.recipients.all()
        
        if not recipients:
            return Response({'error': 'No recipients found'}, status=400)
        
        # Update campaign status
        campaign.status = 'sending'
        campaign.save()
        
        # Send emails (in production, use Celery for background tasks)
        sent_count = 0
        failed_count = 0
        
        for contact in recipients:
            if not contact.email:
                continue
            
            try:
                # Replace template variables
                subject = campaign.subject
                body_html = campaign.body_html
                body_text = campaign.body_text
                
                # Simple variable replacement (can be enhanced)
                context = {
                    'first_name': contact.first_name,
                    'last_name': contact.last_name,
                    'full_name': contact.full_name,
                    'email': contact.email,
                    'phone': contact.phone or '',
                    'company_name': contact.company.name if contact.company else '',
                }
                
                # Replace variables in subject and body
                for key, value in context.items():
                    subject = subject.replace(f'{{{{{key}}}}}', str(value))
                    body_html = body_html.replace(f'{{{{{key}}}}}', str(value))
                    body_text = body_text.replace(f'{{{{{key}}}}}', str(value))
                
                # Create email
                from_email = campaign.from_email or user_profile.tenant.name
                from_name = campaign.from_name or user_profile.tenant.name
                reply_to = campaign.reply_to or from_email
                
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=body_text,
                    from_email=f"{from_name} <{from_email}>",
                    to=[contact.email],
                    reply_to=[reply_to]
                )
                email.attach_alternative(body_html, "text/html")
                email.send()
                
                # Create email activity
                EmailActivity.objects.create(
                    campaign=campaign,
                    contact=contact,
                    status='sent',
                    sent_at=timezone.now()
                )
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Error sending email to {contact.email}: {str(e)}")
                # Create failed activity
                EmailActivity.objects.create(
                    campaign=campaign,
                    contact=contact,
                    status='failed',
                    bounce_reason=str(e)
                )
                failed_count += 1
        
        # Update campaign status
        campaign.status = 'sent'
        campaign.sent_at = timezone.now()
        campaign.save()
        
        return Response({
            'status': 'Campaign sent',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_recipients': recipients.count()
        })
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Get all email activities for this campaign"""
        campaign = self.get_object()
        activities = campaign.email_activities.all().select_related('contact')
        serializer = EmailActivitySerializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get campaign statistics"""
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        campaigns = EmailCampaign.objects.filter(tenant=user_profile.tenant)
        
        stats = {
            'total_campaigns': campaigns.count(),
            'draft': campaigns.filter(status='draft').count(),
            'scheduled': campaigns.filter(status='scheduled').count(),
            'sent': campaigns.filter(status='sent').count(),
            'total_sent': sum([c.sent_count for c in campaigns]),
            'total_opened': sum([c.opened_count for c in campaigns]),
            'total_clicked': sum([c.clicked_count for c in campaigns]),
            'average_open_rate': sum([c.open_rate for c in campaigns if c.sent_count > 0]) / max(campaigns.filter(status='sent').count(), 1),
        }
        
        return Response(stats)


class EmailActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing email activities (read-only)"""
    serializer_class = EmailActivitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return EmailActivity.objects.none()
        
        queryset = EmailActivity.objects.filter(
            campaign__tenant=user_profile.tenant
        ).select_related('campaign', 'contact')
        
        campaign_id = self.request.query_params.get('campaign')
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class EmailSequenceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing email sequences"""
    serializer_class = EmailSequenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return EmailSequence.objects.none()
        return EmailSequence.objects.filter(tenant=user_profile.tenant).prefetch_related('steps')
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(
                tenant=user_profile.tenant,
                created_by=self.request.user
            )


class EmailSequenceStepViewSet(viewsets.ModelViewSet):
    """ViewSet for managing email sequence steps"""
    serializer_class = EmailSequenceStepSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return EmailSequenceStep.objects.none()
        
        queryset = EmailSequenceStep.objects.filter(
            sequence__tenant=user_profile.tenant
        ).select_related('sequence', 'template')
        
        sequence_id = self.request.query_params.get('sequence')
        if sequence_id:
            queryset = queryset.filter(sequence_id=sequence_id)
        
        return queryset.order_by('sequence', 'order')
    
    def perform_create(self, serializer):
        # Validation is handled by serializer
        serializer.save()

