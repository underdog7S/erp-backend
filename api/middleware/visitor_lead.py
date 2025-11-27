import uuid
from django.utils import timezone

from api.models import VisitorLead


class VisitorLeadMiddleware:
    COOKIE_NAME = 'zenith_visitor_token'
    COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Do not track API/admin requests
        if request.path.startswith('/admin/') or request.path.startswith('/api/'):
            return self.get_response(request)

        token = request.COOKIES.get(self.COOKIE_NAME)
        new_token = False
        if not token:
            token = uuid.uuid4().hex
            new_token = True

        request.visitor_token = token
        self.ensure_visit(request, token)

        response = self.get_response(request)
        if new_token:
            response.set_cookie(
                self.COOKIE_NAME,
                token,
                max_age=self.COOKIE_MAX_AGE,
                httponly=True,
                samesite='Lax',
            )
        return response

    def ensure_visit(self, request, token):
        defaults = {
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:512] or '',
            'landing_url': request.build_absolute_uri(),
            'referrer': request.META.get('HTTP_REFERER', '')[:1024] or '',
            'utm_source': request.GET.get('utm_source', '')[:128] or '',
            'utm_medium': request.GET.get('utm_medium', '')[:128] or '',
            'utm_campaign': request.GET.get('utm_campaign', '')[:128] or '',
            'utm_term': request.GET.get('utm_term', '')[:128] or '',
            'utm_content': request.GET.get('utm_content', '')[:128] or '',
            'last_seen': timezone.now(),
        }
        lead, created = VisitorLead.objects.get_or_create(
            visitor_token=token,
            defaults=defaults,
        )
        if not created:
            VisitorLead.objects.filter(pk=lead.pk).update(last_seen=timezone.now())

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

