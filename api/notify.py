"""One place to raise in-app notifications.

Every module calls notify(); the rules (who is told, respecting each person's settings, no duplicates, never breaking the
business action that triggered it) live here.

Priorities are kept at low/medium and types at info/success/warning on purpose: the older delivery code sends a paid SMS for
high/urgent priority, alert or reminder notifications, which nothing here should trigger by accident.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)

ADMINS = ('admin', 'principal')


def team(tenant, roles=ADMINS):
    """Active users of this tenant with one of the given roles."""
    from api.models.user import UserProfile
    return list(User.objects.filter(
        is_active=True, userprofile__tenant=tenant, userprofile__role__name__in=roles).distinct())


def _allowed(user, module):
    """False when this person switched in-app notifications (or this module) off."""
    from api.models.notifications import NotificationPreference
    pref = NotificationPreference.objects.filter(user=user).first()
    if not pref:
        return True
    if not pref.in_app_enabled:
        return False
    mods = pref.module_preferences or {}
    return mods.get(module, True) is not False


def notify(tenant, title, message, *, roles=ADMINS, users=None, module='general', kind='info', priority='medium',
           path=None, ref=None, dedupe_days=0, exclude=None):
    """Tell people something happened. Returns how many were notified; never raises.

    roles / users   who is told (users wins when given); always limited to this tenant
    ref             (type, id) of the thing it is about, shown on the notification and used for de-duplication
    dedupe_days     skip a person who already has an unread notification about the same ref in this many days
    exclude         a user not to notify (usually whoever did the action)
    """
    try:
        from api.models.notifications import Notification
        from api.utils.notification_utils import create_notification
        if priority not in ('low', 'medium') or kind not in ('info', 'success', 'warning'):
            raise ValueError('notify() only sends low/medium priority info, success or warning notifications')
        if users is None:
            users = team(tenant, roles)
        else:
            from api.models.user import UserProfile
            ids = set(UserProfile.objects.filter(tenant=tenant, user__in=[u.id if hasattr(u, 'id') else u for u in users]).values_list('user_id', flat=True))
            users = [u for u in users if getattr(u, 'id', u) in ids]
        sent = 0
        for user in users:
            if exclude and user.id == getattr(exclude, 'id', exclude):
                continue
            if not _allowed(user, module):
                continue
            if ref and dedupe_days:
                since = timezone.now() - timedelta(days=dedupe_days)
                if Notification.objects.filter(user=user, tenant=tenant, read=False, reference_type=ref[0], reference_id=ref[1],
                                               created_at__gte=since).exists():
                    continue
            base = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
            create_notification(
                user=user, tenant=tenant, title=title[:200], message=message, notification_type=kind, module=module, priority=priority,
                action_url=(base + path) if (path and base) else None, action_label='Open' if path else None,
                reference_type=ref[0] if ref else None, reference_id=ref[1] if ref else None, expires_in_days=30)
            sent += 1
        return sent
    except Exception:  # a notification must never break the sale, booking or payment that caused it
        logger.exception('notify() failed for %r', title)
        return 0
