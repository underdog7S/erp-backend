from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum, Avg, Max, Min
from django.utils import timezone
from datetime import timedelta, datetime
from api.models.user import UserProfile
from api.models.crm import Contact, Company, Activity, Deal, ContactTag
from api.models.email_marketing import EmailCampaign, EmailActivity

class CRMAnalyticsView(APIView):
    """Comprehensive CRM analytics dashboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        tenant = user_profile.tenant
        
        # Date range (default to last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Contact Analytics
        contacts = Contact.objects.filter(tenant=tenant)
        total_contacts = contacts.count()
        contacts_by_type = contacts.values('contact_type').annotate(count=Count('id'))
        contacts_by_lifecycle = contacts.values('lifecycle_stage').annotate(count=Count('id'))
        new_contacts = contacts.filter(created_at__gte=start_date).count()
        
        # Company Analytics
        companies = Company.objects.filter(tenant=tenant)
        total_companies = companies.count()
        companies_by_industry = companies.values('industry').annotate(count=Count('id'))
        
        # Activity Analytics
        activities = Activity.objects.filter(tenant=tenant, activity_date__gte=start_date)
        activities_by_type = activities.values('activity_type').annotate(count=Count('id'))
        activities_by_status = activities.values('status').annotate(count=Count('id'))
        total_activities = activities.count()
        
        # Deal Analytics
        deals = Deal.objects.filter(tenant=tenant)
        total_deals = deals.count()
        open_deals = deals.filter(won=False, lost=False)
        won_deals = deals.filter(won=True)
        lost_deals = deals.filter(lost=True)
        
        deal_value = deals.aggregate(
            total=Sum('amount'),
            average=Avg('amount'),
            max=Max('amount'),
            min=Min('amount')
        )
        
        weighted_value = sum([deal.weighted_amount for deal in open_deals])
        
        deals_by_stage = deals.values('stage').annotate(
            count=Count('id'),
            total_value=Sum('amount')
        )
        
        # Email Campaign Analytics
        campaigns = EmailCampaign.objects.filter(tenant=tenant)
        total_campaigns = campaigns.count()
        sent_campaigns = campaigns.filter(status='sent')
        total_emails_sent = sum([c.sent_count for c in sent_campaigns])
        total_emails_opened = sum([c.opened_count for c in sent_campaigns])
        total_emails_clicked = sum([c.clicked_count for c in sent_campaigns])
        
        avg_open_rate = sum([c.open_rate for c in sent_campaigns if c.sent_count > 0]) / max(sent_campaigns.count(), 1) if sent_campaigns.count() > 0 else 0
        avg_click_rate = sum([c.click_rate for c in sent_campaigns if c.sent_count > 0]) / max(sent_campaigns.count(), 1) if sent_campaigns.count() > 0 else 0
        
        # Recent Activity
        recent_activities = activities.order_by('-activity_date')[:10]
        from api.serializers_crm import ActivitySerializer
        recent_activities_data = ActivitySerializer(recent_activities, many=True).data
        
        # Top Contacts (by activity count)
        top_contacts = contacts.annotate(
            activity_count=Count('activities')
        ).order_by('-activity_count')[:10]
        from api.serializers_crm import ContactSerializer
        top_contacts_data = ContactSerializer(top_contacts, many=True).data
        
        # Conversion Funnel
        leads = contacts.filter(lifecycle_stage='lead').count()
        customers = contacts.filter(lifecycle_stage='customer').count()
        opportunities = contacts.filter(lifecycle_stage='opportunity').count()
        vips = contacts.filter(lifecycle_stage='vip').count()
        
        # Time-based trends (last 7 days)
        last_7_days = [timezone.now() - timedelta(days=x) for x in range(7, -1, -1)]
        contacts_trend = []
        activities_trend = []
        deals_trend = []
        
        for day in last_7_days:
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            contacts_trend.append({
                'date': day_start.date().isoformat(),
                'count': contacts.filter(created_at__gte=day_start, created_at__lt=day_end).count()
            })
            
            activities_trend.append({
                'date': day_start.date().isoformat(),
                'count': Activity.objects.filter(
                    tenant=tenant,
                    activity_date__gte=day_start,
                    activity_date__lt=day_end
                ).count()
            })
            
            deals_trend.append({
                'date': day_start.date().isoformat(),
                'count': deals.filter(created_at__gte=day_start, created_at__lt=day_end).count()
            })
        
        return Response({
            'overview': {
                'total_contacts': total_contacts,
                'total_companies': total_companies,
                'total_deals': total_deals,
                'total_campaigns': total_campaigns,
                'new_contacts_this_period': new_contacts,
            },
            'contacts': {
                'total': total_contacts,
                'by_type': list(contacts_by_type),
                'by_lifecycle': list(contacts_by_lifecycle),
                'new_this_period': new_contacts,
                'conversion_funnel': {
                    'leads': leads,
                    'opportunities': opportunities,
                    'customers': customers,
                    'vips': vips,
                }
            },
            'companies': {
                'total': total_companies,
                'by_industry': list(companies_by_industry),
            },
            'activities': {
                'total_this_period': total_activities,
                'by_type': list(activities_by_type),
                'by_status': list(activities_by_status),
            },
            'deals': {
                'total': total_deals,
                'open': open_deals.count(),
                'won': won_deals.count(),
                'lost': lost_deals.count(),
                'total_value': float(deal_value['total'] or 0),
                'average_value': float(deal_value['average'] or 0),
                'max_value': float(deal_value['max'] or 0),
                'min_value': float(deal_value['min'] or 0),
                'weighted_value': float(weighted_value),
                'win_rate': (won_deals.count() / max(total_deals, 1)) * 100,
                'by_stage': list(deals_by_stage),
            },
            'email_marketing': {
                'total_campaigns': total_campaigns,
                'sent_campaigns': sent_campaigns.count(),
                'total_emails_sent': total_emails_sent,
                'total_emails_opened': total_emails_opened,
                'total_emails_clicked': total_emails_clicked,
                'average_open_rate': round(avg_open_rate, 2),
                'average_click_rate': round(avg_click_rate, 2),
            },
            'trends': {
                'contacts': contacts_trend,
                'activities': activities_trend,
                'deals': deals_trend,
            },
            'top_contacts': top_contacts_data,
            'recent_activities': recent_activities_data,
        })


class ContactAnalyticsView(APIView):
    """Detailed contact analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        tenant = user_profile.tenant
        contacts = Contact.objects.filter(tenant=tenant)
        
        # Contact sources (if tracked in custom_fields)
        # This is a placeholder - can be enhanced based on actual data
        
        # Contact engagement score (based on activities)
        contacts_with_engagement = contacts.annotate(
            activity_count=Count('activities'),
            deal_count=Count('deals')
        )
        
        # Most engaged contacts
        most_engaged = contacts_with_engagement.order_by('-activity_count')[:10]
        from api.serializers_crm import ContactSerializer
        most_engaged_data = ContactSerializer(most_engaged, many=True).data
        
        return Response({
            'most_engaged_contacts': most_engaged_data,
            'engagement_stats': {
                'average_activities_per_contact': contacts_with_engagement.aggregate(
                    avg=Avg('activity_count')
                )['avg'] or 0,
                'contacts_with_activities': contacts_with_engagement.filter(activity_count__gt=0).count(),
                'contacts_with_deals': contacts_with_engagement.filter(deal_count__gt=0).count(),
            }
        })


class DealPipelineAnalyticsView(APIView):
    """Deal pipeline analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        tenant = user_profile.tenant
        deals = Deal.objects.filter(tenant=tenant, won=False, lost=False)
        
        # Pipeline health
        total_value = deals.aggregate(total=Sum('amount'))['total'] or 0
        weighted_value = sum([deal.weighted_amount for deal in deals])
        
        # Average deal size by stage
        deals_by_stage = deals.values('stage').annotate(
            count=Count('id'),
            avg_value=Avg('amount'),
            total_value=Sum('amount'),
            weighted_value=Sum('amount') * Avg('probability') / 100
        )
        
        # Deal velocity (average days in each stage)
        # This would require tracking stage changes - simplified for now
        
        return Response({
            'pipeline_health': {
                'total_deals': deals.count(),
                'total_value': float(total_value),
                'weighted_value': float(weighted_value),
                'average_deal_size': float(total_value / max(deals.count(), 1)),
            },
            'by_stage': list(deals_by_stage),
        })


class EmailMarketingAnalyticsView(APIView):
    """Email marketing analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile:
            return Response({'error': 'User profile not found'}, status=400)
        
        tenant = user_profile.tenant
        campaigns = EmailCampaign.objects.filter(tenant=tenant, status='sent')
        
        # Campaign performance
        campaign_performance = []
        for campaign in campaigns:
            campaign_performance.append({
                'id': campaign.id,
                'name': campaign.name,
                'sent_count': campaign.sent_count,
                'opened_count': campaign.opened_count,
                'clicked_count': campaign.clicked_count,
                'open_rate': campaign.open_rate,
                'click_rate': campaign.click_rate,
                'sent_at': campaign.sent_at.isoformat() if campaign.sent_at else None,
            })
        
        # Overall stats
        total_sent = sum([c.sent_count for c in campaigns])
        total_opened = sum([c.opened_count for c in campaigns])
        total_clicked = sum([c.clicked_count for c in campaigns])
        
        return Response({
            'total_campaigns': campaigns.count(),
            'total_emails_sent': total_sent,
            'total_emails_opened': total_opened,
            'total_emails_clicked': total_clicked,
            'overall_open_rate': (total_opened / max(total_sent, 1)) * 100,
            'overall_click_rate': (total_clicked / max(total_sent, 1)) * 100,
            'campaign_performance': campaign_performance,
        })

