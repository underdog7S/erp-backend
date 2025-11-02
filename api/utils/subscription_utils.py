"""
Subscription utility functions for managing user limits and plan changes
"""
from django.db.models import Count
from api.models.user import UserProfile, Tenant
from api.utils.notification_utils import create_module_notification
from django.utils import timezone

def handle_user_limit_exceeded(tenant):
    """
    Handle users exceeding plan limit when plan changes or expires
    Returns dict with suspended count and message
    """
    if not tenant.plan or not tenant.plan.max_users:
        return {'suspended_count': 0, 'message': 'Plan has no user limit'}
    
    current_count = UserProfile.objects.filter(tenant=tenant).count()
    max_users = tenant.plan.max_users
    
    if current_count <= max_users:
        return {'suspended_count': 0, 'message': 'User count within limit'}
    
    # Calculate excess users
    excess = current_count - max_users
    
    # Suspend excess users (last added first, excluding admins)
    excess_users = UserProfile.objects.filter(
        tenant=tenant
    ).exclude(role__name='admin').order_by('-id')[:excess]
    
    suspended_ids = []
    for user_profile in excess_users:
        # Suspend user account
        user_profile.user.is_active = False
        user_profile.user.save(update_fields=['is_active'])
        suspended_ids.append(user_profile.user.id)
        
        # Notify user
        create_module_notification(
            user=user_profile.user,
            tenant=tenant,
            module='system',
            notification_type='warning',
            title='Account Suspended',
            message=f'Your account has been temporarily suspended due to plan user limits ({current_count}/{max_users}). Please contact your administrator to upgrade the plan.',
            priority='high'
        )
    
    # Notify all admins
    admin_users = UserProfile.objects.filter(tenant=tenant, role__name='admin')
    for admin_profile in admin_users:
        create_module_notification(
            user=admin_profile.user,
            tenant=tenant,
            module='system',
            notification_type='alert',
            title='User Limit Exceeded',
            message=f'{excess} user(s) have been suspended due to plan limits ({current_count}/{max_users}). Upgrade your plan to restore access.',
            priority='high',
            action_url='/admin/users',
            action_label='Manage Users'
        )
    
    return {
        'suspended_count': len(suspended_ids),
        'suspended_user_ids': suspended_ids,
        'message': f'{excess} user(s) have been suspended due to plan limits.'
    }

def reactivate_suspended_users(tenant):
    """
    Reactivate suspended users when plan is upgraded
    """
    # Find all inactive users for this tenant
    suspended_users = UserProfile.objects.filter(
        tenant=tenant,
        user__is_active=False
    )
    
    count = suspended_users.count()
    
    for user_profile in suspended_users:
        user_profile.user.is_active = True
        user_profile.user.save(update_fields=['is_active'])
        
        # Notify user
        create_module_notification(
            user=user_profile.user,
            tenant=tenant,
            module='system',
            notification_type='success',
            title='Account Reactivated',
            message='Your account has been reactivated. You can now access the system.',
            priority='medium'
        )
    
    return {
        'reactivated_count': count,
        'message': f'{count} user(s) have been reactivated.'
    }

def validate_user_limit_before_adding(tenant):
    """
    Check if adding a new user would exceed plan limit
    Returns (can_add, message)
    """
    if not tenant.plan:
        return (True, None)
    
    if not tenant.plan.max_users:
        return (True, None)  # Unlimited users
    
    current_count = UserProfile.objects.filter(tenant=tenant).count()
    max_users = tenant.plan.max_users
    
    if current_count >= max_users:
        return (False, f'User limit reached for your plan ({current_count}/{max_users}). Upgrade your plan to add more users.')
    
    return (True, None)

