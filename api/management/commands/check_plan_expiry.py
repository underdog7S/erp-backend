"""
Django management command to check plan expiration and send renewal notifications
Run this daily via cron: 0 9 * * * cd /path/to/backend && python manage.py check_plan_expiry
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models.user import Tenant
from api.utils.alert_utils import create_plan_expiry_alert
from api.utils.notification_utils import create_module_notification

class Command(BaseCommand):
    help = 'Check plan expiration and send renewal notifications'

    def handle(self, *args, **options):
        today = timezone.now().date()
        self.stdout.write(f'Checking plan expiration for date: {today}')
        
        # Find expiring plans (30, 7, 1 days before expiration)
        for days in [30, 7, 1]:
            expiry_date = today + timedelta(days=days)
            
            tenants = Tenant.objects.filter(
                subscription_end_date=expiry_date,
                subscription_status='active'
            )
            
            count = tenants.count()
            self.stdout.write(f'Found {count} tenant(s) expiring in {days} day(s)')
            
            for tenant in tenants:
                # Update status to expiring_soon if within 7 days
                if days <= 7:
                    tenant.subscription_status = 'expiring_soon'
                    tenant.save(update_fields=['subscription_status'])
                
                # Create alert
                create_plan_expiry_alert(tenant, days)
                
                # Create system notification for all admin users
                admin_users = tenant.userprofile_set.filter(role__name='admin')
                for admin_profile in admin_users:
                    create_module_notification(
                        user=admin_profile.user,
                        tenant=tenant,
                        module='system',
                        notification_type='warning' if days > 7 else 'alert',
                        title='Plan Expiring Soon' if days > 1 else 'Plan Expires Today!',
                        message=f'Your {tenant.plan.name if tenant.plan else "plan"} plan expires in {days} day(s). Please renew to avoid service interruption.',
                        priority='high' if days <= 7 else 'medium',
                        action_url='/admin/plans',
                        action_label='Renew Plan'
                    )
                
                self.stdout.write(f'  - Sent notifications to {admin_users.count()} admin(s) for tenant: {tenant.name}')
        
        # Check expired plans
        expired_tenants = Tenant.objects.filter(
            subscription_end_date__lt=today,
            subscription_status__in=['active', 'expiring_soon']
        )
        
        expired_count = expired_tenants.count()
        self.stdout.write(f'\nFound {expired_count} expired tenant(s)')
        
        for tenant in expired_tenants:
            # Move to grace period (30 days)
            grace_period_end = today + timedelta(days=30)
            tenant.subscription_status = 'grace_period'
            tenant.grace_period_end_date = grace_period_end
            tenant.save(update_fields=['subscription_status', 'grace_period_end_date'])
            
            # Notify admins about expiration
            admin_users = tenant.userprofile_set.filter(role__name='admin')
            for admin_profile in admin_users:
                create_module_notification(
                    user=admin_profile.user,
                    tenant=tenant,
                    module='system',
                    notification_type='error',
                    title='Plan Expired - Grace Period Active',
                    message=f'Your {tenant.plan.name if tenant.plan else "plan"} plan has expired. You are in a 30-day grace period with limited access. Renew now to restore full functionality.',
                    priority='urgent',
                    action_url='/admin/plans',
                    action_label='Renew Plan'
                )
            
            self.stdout.write(f'  - Moved tenant {tenant.name} to grace period until {grace_period_end}')
        
        # Check grace period expiration (move to fully expired)
        grace_period_expired = Tenant.objects.filter(
            grace_period_end_date__lt=today,
            subscription_status='grace_period'
        )
        
        grace_expired_count = grace_period_expired.count()
        self.stdout.write(f'\nFound {grace_expired_count} tenant(s) with expired grace period')
        
        for tenant in grace_period_expired:
            tenant.subscription_status = 'expired'
            tenant.save(update_fields=['subscription_status'])
            
            # Notify admins that grace period ended
            admin_users = tenant.userprofile_set.filter(role__name='admin')
            for admin_profile in admin_users:
                create_module_notification(
                    user=admin_profile.user,
                    tenant=tenant,
                    module='system',
                    notification_type='error',
                    title='Grace Period Ended - Plan Suspended',
                    message=f'Your grace period has ended. Your {tenant.plan.name if tenant.plan else "plan"} is now fully expired. Renew immediately to restore access.',
                    priority='urgent',
                    action_url='/admin/plans',
                    action_label='Renew Plan'
                )
            
            self.stdout.write(f'  - Moved tenant {tenant.name} to expired status')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Plan expiration check completed!'))
        self.stdout.write(f'   - Expiring soon notifications: {count}')
        self.stdout.write(f'   - Moved to grace period: {expired_count}')
        self.stdout.write(f'   - Moved to expired: {grace_expired_count}')

