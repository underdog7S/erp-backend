import os

code = """
from api.models.plan import Plan
from django.db import transaction

class SeedPlansView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        try:
            with transaction.atomic():
                Plan.objects.all().delete()
                Plan.objects.create(name="Free", description="Small teams", max_users=2, storage_limit_mb=500, price=0, billing_cycle="monthly", has_dashboard=True, has_inventory=True)
                Plan.objects.create(name="Starter", description="Growing business", max_users=15, storage_limit_mb=5120, price=2499, billing_cycle="monthly", has_dashboard=True, has_inventory=True, has_api_access=True)
                Plan.objects.create(name="Pro", description="Established orgs", max_users=50, storage_limit_mb=20480, price=6999, billing_cycle="monthly", popular=True, has_dashboard=True, has_inventory=True, has_api_access=True, has_analytics=True, has_priority_support=True)
                Plan.objects.create(name="Enterprise", description="Large scale", max_users=None, storage_limit_mb=102400, price=14999, billing_cycle="monthly", has_dashboard=True, has_inventory=True, has_api_access=True, has_analytics=True, has_white_label=True, has_priority_support=True, has_custom_reports=True)
                
                # Fix isolation for shadab1
                user = UserProfile.objects.filter(user__username='shadab1').first()
                if user:
                    user.tenant = None
                    user.user.is_superuser = True
                    user.user.is_staff = True
                    user.user.save()
                    user.save()
                    
            return Response({"message": "Database successfully seeded with plans, and shadab1 superadmin isolation fixed!"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
"""

with open('d:/ERP/backend/api/views/admin_views.py', 'a', encoding='utf-8') as f:
    f.write(code)
