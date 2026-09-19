from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from api.models.user import Tenant, UserProfile
from api.models.custom_service import CustomServiceRequest

class AdminDashboardStatsView(APIView):
    """Returns analytics data for the Django SuperAdmin Dashboard"""
    from rest_framework.authentication import SessionAuthentication, BasicAuthentication
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # 1. High-level Stats
        total_tenants = Tenant.objects.count()
        total_users = UserProfile.objects.count()
        total_service_requests = CustomServiceRequest.objects.count()
        
        # 2. Tenants by Industry (Donut Chart)
        industry_data = Tenant.objects.values('industry').annotate(count=Count('id')).order_by('-count')
        industry_labels = [item['industry'].title() if item['industry'] else 'General' for item in industry_data]
        industry_counts = [item['count'] for item in industry_data]

        # 3. Tenants by SaaS Plan (Bar Chart)
        plan_data = Tenant.objects.values('plan__name').annotate(count=Count('id'))
        plan_labels = [item['plan__name'] if item['plan__name'] else 'Unassigned' for item in plan_data]
        plan_counts = [item['count'] for item in plan_data]

        # 4. Signups over last 30 days (Line Chart)
        signups = Tenant.objects.filter(created_at__gte=thirty_days_ago) \
            .annotate(date=TruncDate('created_at')) \
            .values('date') \
            .annotate(count=Count('id')) \
            .order_by('date')
            
        signup_labels = []
        signup_counts = []
        
        for i in range(30, -1, -1):
            date = (now - timedelta(days=i)).date()
            signup_labels.append(date.strftime('%b %d'))
            count = next((s['count'] for s in signups if s['date'] == date), 0)
            signup_counts.append(count)
            
        # 5. Recent Activity Feed
        recent_tenants = Tenant.objects.order_by('-created_at')[:5]
        recent_activity = [
            {
                "time": t.created_at.strftime('%b %d, %H:%M'),
                "message": f"New tenant registered: {t.name} ({t.industry or 'General'})"
            } for t in recent_tenants
        ]

        return Response({
            'total_tenants': total_tenants,
            'total_users': total_users,
            'total_requests': total_service_requests,
            'industry_labels': industry_labels,
            'industry_counts': industry_counts,
            'plan_labels': plan_labels,
            'plan_counts': plan_counts,
            'signup_labels': signup_labels,
            'signup_counts': signup_counts,
            'recent_activity': recent_activity
        })
