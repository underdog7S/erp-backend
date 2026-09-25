"""Turn a pending team invitation into a working account (used when someone signs in with Google)."""
from django.db import transaction
from django.utils import timezone

from api.models.user import UserInvitation, UserProfile


def accept_pending_invitation(user):
    """If `user`'s email has a valid pending invitation, give them a profile in the inviting team and return it."""
    email = (user.email or '').strip().lower()
    if not email:
        return None
    invitation = (UserInvitation.objects.filter(email=email, accepted_at__isnull=True)
                  .select_related('tenant', 'role').order_by('-id').first())
    if not invitation or not invitation.is_valid():
        return None
    from api.utils.subscription_utils import validate_user_limit_before_adding
    allowed, _ = validate_user_limit_before_adding(invitation.tenant)
    if not allowed:
        return None  # the team is full: the person falls through to normal sign-up handling
    with transaction.atomic():
        profile = UserProfile.objects.create(user=user, tenant=invitation.tenant, role=invitation.role)
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['accepted_at'])
    return profile
