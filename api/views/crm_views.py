from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta

from api.models.crm import Contact, Company, ContactTag, Activity, Deal, DealStage
from api.models.user import UserProfile
from api.serializers_crm import (
    ContactSerializer, CompanySerializer, ContactTagSerializer,
    ActivitySerializer, DealSerializer, DealStageSerializer
)


class ContactTagViewSet(viewsets.ModelViewSet):
    """ViewSet for managing contact tags"""
    serializer_class = ContactTagSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return ContactTag.objects.none()
        return ContactTag.objects.filter(tenant=user_profile.tenant)
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(tenant=user_profile.tenant)


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet for managing contacts"""
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return Contact.objects.none()
        
        queryset = Contact.objects.filter(tenant=user_profile.tenant).select_related(
            'company', 'owner', 'created_by'
        ).prefetch_related('tags')
        
        # Filtering
        contact_type = self.request.query_params.get('contact_type')
        if contact_type:
            queryset = queryset.filter(contact_type=contact_type)
        
        lifecycle_stage = self.request.query_params.get('lifecycle_stage')
        if lifecycle_stage:
            queryset = queryset.filter(lifecycle_stage=lifecycle_stage)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        
        tag_id = self.request.query_params.get('tag')
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(
                tenant=user_profile.tenant,
                created_by=self.request.user
            )
    
    @action(detail=True, methods=['post'])
    def update_last_contacted(self, request, pk=None):
        """Update last contacted timestamp"""
        contact = self.get_object()
        contact.last_contacted_at = timezone.now()
        contact.save()
        return Response({'status': 'Last contacted updated'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get contact statistics"""
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        queryset = Contact.objects.filter(tenant=user_profile.tenant)
        
        stats = {
            'total': queryset.count(),
            'by_type': queryset.values('contact_type').annotate(count=Count('id')),
            'by_lifecycle': queryset.values('lifecycle_stage').annotate(count=Count('id')),
            'recent': queryset.filter(created_at__gte=timezone.now() - timedelta(days=30)).count(),
        }
        
        return Response(stats)


class CompanyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing companies"""
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return Company.objects.none()
        
        queryset = Company.objects.filter(tenant=user_profile.tenant).select_related(
            'parent_company', 'owner', 'created_by'
        ).prefetch_related('tags', 'contacts')
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(industry__icontains=search) |
                Q(email__icontains=search)
            )
        
        industry = self.request.query_params.get('industry')
        if industry:
            queryset = queryset.filter(industry=industry)
        
        return queryset
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(
                tenant=user_profile.tenant,
                created_by=self.request.user
            )
    
    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        """Get all contacts for a company"""
        company = self.get_object()
        contacts = company.contacts.all()
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get company statistics"""
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        queryset = Company.objects.filter(tenant=user_profile.tenant)
        
        stats = {
            'total': queryset.count(),
            'by_industry': queryset.values('industry').annotate(count=Count('id')),
            'recent': queryset.filter(created_at__gte=timezone.now() - timedelta(days=30)).count(),
        }
        
        return Response(stats)


class ActivityViewSet(viewsets.ModelViewSet):
    """ViewSet for managing activities"""
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return Activity.objects.none()
        
        queryset = Activity.objects.filter(tenant=user_profile.tenant).select_related(
            'contact', 'company', 'created_by', 'assigned_to'
        )
        
        # Filtering
        activity_type = self.request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-activity_date')
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(
                tenant=user_profile.tenant,
                created_by=self.request.user
            )


class DealStageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing deal stages"""
    serializer_class = DealStageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return DealStage.objects.none()
        return DealStage.objects.filter(tenant=user_profile.tenant).order_by('order')
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(tenant=user_profile.tenant)


class DealViewSet(viewsets.ModelViewSet):
    """ViewSet for managing deals"""
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if not user_profile:
            return Deal.objects.none()
        
        queryset = Deal.objects.filter(tenant=user_profile.tenant).select_related(
            'contact', 'company', 'owner', 'created_by'
        )
        
        # Filtering
        stage = self.request.query_params.get('stage')
        if stage:
            queryset = queryset.filter(stage=stage)
        
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        won = self.request.query_params.get('won')
        if won is not None:
            queryset = queryset.filter(won=won.lower() == 'true')
        
        lost = self.request.query_params.get('lost')
        if lost is not None:
            queryset = queryset.filter(lost=lost.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()
        if user_profile:
            serializer.save(
                tenant=user_profile.tenant,
                created_by=self.request.user
            )
    
    @action(detail=False, methods=['get'])
    def pipeline(self, request):
        """Get pipeline view with deals grouped by stage"""
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        stages = DealStage.objects.filter(tenant=user_profile.tenant).order_by('order')
        pipeline = []
        
        for stage in stages:
            deals = Deal.objects.filter(
                tenant=user_profile.tenant,
                stage=stage.name,
                won=False,
                lost=False
            )
            
            total_amount = deals.aggregate(total=Sum('amount'))['total'] or 0
            weighted_amount = sum([deal.weighted_amount for deal in deals])
            
            pipeline.append({
                'stage': DealStageSerializer(stage).data,
                'deals': DealSerializer(deals, many=True).data,
                'deal_count': deals.count(),
                'total_amount': float(total_amount),
                'weighted_amount': float(weighted_amount),
            })
        
        return Response(pipeline)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get deal statistics"""
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        queryset = Deal.objects.filter(tenant=user_profile.tenant)
        
        stats = {
            'total': queryset.count(),
            'open': queryset.filter(won=False, lost=False).count(),
            'won': queryset.filter(won=True).count(),
            'lost': queryset.filter(lost=True).count(),
            'total_value': float(queryset.aggregate(total=Sum('amount'))['total'] or 0),
            'weighted_value': sum([deal.weighted_amount for deal in queryset.filter(won=False, lost=False)]),
            'by_stage': queryset.values('stage').annotate(count=Count('id'), total=Sum('amount')),
        }
        
        return Response(stats)

