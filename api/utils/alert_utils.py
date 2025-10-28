"""
Utility functions for alert management
"""
from api.models.alerts import Alert
from api.models.user import UserProfile, Tenant
from django.utils import timezone
from typing import List, Optional


def create_alert(tenant: Tenant, message: str, alert_type: str = 'general') -> Alert:
    """
    Create a new alert for a tenant
    
    Args:
        tenant: The tenant to create the alert for
        message: The alert message
        alert_type: Type of alert (usage, plan, general)
    
    Returns:
        Alert: The created alert instance
    """
    return Alert.objects.create(
        tenant=tenant,
        message=message,
        type=alert_type
    )


def create_usage_alert(tenant: Tenant, usage_type: str, current_value: float, limit_value: float, unit: str = '') -> Alert:
    """
    Create a usage-based alert
    
    Args:
        tenant: The tenant
        usage_type: Type of usage (storage, users, etc.)
        current_value: Current usage value
        limit_value: Limit value
        unit: Unit of measurement
    
    Returns:
        Alert: The created alert instance
    """
    percentage = (current_value / limit_value) * 100 if limit_value > 0 else 0
    
    if percentage >= 100:
        message = f"{usage_type.title()} limit exceeded! Current: {current_value:.1f}{unit}, Limit: {limit_value:.1f}{unit} ({percentage:.1f}%)"
    elif percentage >= 90:
        message = f"{usage_type.title()} usage is at {percentage:.1f}% ({current_value:.1f}{unit}/{limit_value:.1f}{unit}). Consider upgrading your plan."
    else:
        message = f"{usage_type.title()} usage is at {percentage:.1f}% ({current_value:.1f}{unit}/{limit_value:.1f}{unit})"
    
    return create_alert(tenant, message, 'usage')


def create_plan_expiry_alert(tenant: Tenant, days_remaining: int) -> Alert:
    """
    Create a plan expiry alert
    
    Args:
        tenant: The tenant
        days_remaining: Days until plan expires
    
    Returns:
        Alert: The created alert instance
    """
    if days_remaining <= 0:
        message = f"Your plan has expired! Please renew to continue using the service."
    elif days_remaining <= 7:
        message = f"Your plan expires in {days_remaining} day{'s' if days_remaining != 1 else ''}. Please renew soon."
    elif days_remaining <= 30:
        message = f"Your plan expires in {days_remaining} days. Consider renewing to avoid service interruption."
    else:
        message = f"Your plan expires in {days_remaining} days."
    
    return create_alert(tenant, message, 'plan')


def bulk_create_alerts(tenant: Tenant, alerts_data: List[dict]) -> List[Alert]:
    """
    Create multiple alerts in bulk
    
    Args:
        tenant: The tenant
        alerts_data: List of alert data dictionaries
    
    Returns:
        List[Alert]: List of created alert instances
    """
    alerts = []
    for alert_data in alerts_data:
        alert = Alert.objects.create(
            tenant=tenant,
            message=alert_data.get('message', ''),
            type=alert_data.get('type', 'general')
        )
        alerts.append(alert)
    
    return alerts


def cleanup_old_alerts(tenant: Tenant, days_old: int = 30) -> int:
    """
    Clean up old alerts for a tenant
    
    Args:
        tenant: The tenant
        days_old: Number of days old alerts to delete
    
    Returns:
        int: Number of alerts deleted
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=days_old)
    deleted_count, _ = Alert.objects.filter(
        tenant=tenant,
        created_at__lt=cutoff_date,
        read=True  # Only delete read alerts
    ).delete()
    
    return deleted_count


def get_alert_summary(tenant: Tenant) -> dict:
    """
    Get alert summary statistics for a tenant
    
    Args:
        tenant: The tenant
    
    Returns:
        dict: Alert summary statistics
    """
    total_alerts = Alert.objects.filter(tenant=tenant).count()
    unread_alerts = Alert.objects.filter(tenant=tenant, read=False).count()
    
    # Alerts by type
    alerts_by_type = {}
    for alert_type, _ in Alert.ALERT_TYPES:
        count = Alert.objects.filter(tenant=tenant, type=alert_type).count()
        alerts_by_type[alert_type] = count
    
    # Recent alerts (last 7 days)
    week_ago = timezone.now() - timezone.timedelta(days=7)
    recent_alerts = Alert.objects.filter(
        tenant=tenant,
        created_at__gte=week_ago
    ).count()
    
    return {
        'total_alerts': total_alerts,
        'unread_alerts': unread_alerts,
        'read_alerts': total_alerts - unread_alerts,
        'alerts_by_type': alerts_by_type,
        'recent_alerts': recent_alerts
    }


def mark_alerts_read(tenant: Tenant, alert_ids: List[int]) -> int:
    """
    Mark multiple alerts as read
    
    Args:
        tenant: The tenant
        alert_ids: List of alert IDs to mark as read
    
    Returns:
        int: Number of alerts updated
    """
    updated_count = Alert.objects.filter(
        id__in=alert_ids,
        tenant=tenant
    ).update(read=True)
    
    return updated_count


def mark_alerts_unread(tenant: Tenant, alert_ids: List[int]) -> int:
    """
    Mark multiple alerts as unread
    
    Args:
        tenant: The tenant
        alert_ids: List of alert IDs to mark as unread
    
    Returns:
        int: Number of alerts updated
    """
    updated_count = Alert.objects.filter(
        id__in=alert_ids,
        tenant=tenant
    ).update(read=False)
    
    return updated_count


def delete_alerts(tenant: Tenant, alert_ids: List[int]) -> int:
    """
    Delete multiple alerts
    
    Args:
        tenant: The tenant
        alert_ids: List of alert IDs to delete
    
    Returns:
        int: Number of alerts deleted
    """
    deleted_count, _ = Alert.objects.filter(
        id__in=alert_ids,
        tenant=tenant
    ).delete()
    
    return deleted_count
