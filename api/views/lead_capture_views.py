import re
import logging
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.crm import Contact
from api.models.lead_capture import LeadCaptureConfig
from api.models.permissions import role_required
from api.models.user import UserProfile
from api.utils.geo import geocode, haversine_km, overpass_search, CATEGORY_FILTERS, MAX_PROSPECT_RADIUS_KM

logger = logging.getLogger(__name__)

SUBMIT_LIMIT_PER_HOUR = 10
PROSPECT_WARNING = (
    "Contact these businesses by phone, in person, or by email with an unsubscribe link only. "
    "Do NOT send bulk WhatsApp or SMS to them: without their consent it breaks TRAI/DLT and WhatsApp rules, "
    "can get your (and every other client's) sending number banned, and may breach India's DPDP Act. "
    "Data comes from public OpenStreetMap listings and may be outdated."
)


def _cors(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


def _client_ip(request):
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    return (fwd.split(',')[0].strip() if fwd else request.META.get('REMOTE_ADDR')) or 'unknown'


def _clean_phone(raw):
    digits = re.sub(r'\D', '', raw or '')
    return digits if 8 <= len(digits) <= 15 else ''


def _config_or_none(key):
    return LeadCaptureConfig.objects.select_related('tenant').filter(public_key=key, is_active=True).first()


class PublicLeadFormConfigView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, key):
        cfg = _config_or_none(key)
        if not cfg:
            return _cors(Response({'error': 'Form not found'}, status=status.HTTP_404_NOT_FOUND))
        return _cors(Response({
            'business_name': cfg.business_name or cfg.tenant.name,
            'intro_message': cfg.intro_message,
            'success_message': cfg.success_message,
        }))

    def options(self, request, *args, **kwargs):
        return _cors(HttpResponse(status=204))


class PublicLeadFormSubmitView(APIView):
    """Anonymous enquiry submission. Consent is mandatory; a honeypot field and
    a per-IP hourly limit keep bots out; duplicates (same phone/email) update
    the existing contact instead of creating another."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def options(self, request, *args, **kwargs):
        return _cors(HttpResponse(status=204))

    def post(self, request, key):
        cfg = _config_or_none(key)
        if not cfg:
            return _cors(Response({'error': 'Form not found'}, status=status.HTTP_404_NOT_FOUND))

        rl_key = f"leadform:{_client_ip(request)}"
        count = cache.get(rl_key, 0)
        if count >= SUBMIT_LIMIT_PER_HOUR:
            return _cors(Response({'error': 'Too many submissions. Please try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS))
        cache.set(rl_key, count + 1, 3600)

        d = request.data
        if d.get('website_url'):  # honeypot: humans never see or fill this
            return _cors(Response({'ok': True, 'message': cfg.success_message}))

        name = (d.get('name') or '').strip()[:150]
        phone = _clean_phone(d.get('phone'))
        email = (d.get('email') or '').strip().lower()[:254]
        consent = str(d.get('consent', '')).lower() in ('true', '1', 'on', 'yes')
        if not name:
            return _cors(Response({'error': 'Please enter your name.'}, status=status.HTTP_400_BAD_REQUEST))
        if not consent:
            return _cors(Response({'error': 'Please tick the consent box so we can contact you.'}, status=status.HTTP_400_BAD_REQUEST))
        if email:
            try:
                validate_email(email)
            except DjangoValidationError:
                return _cors(Response({'error': 'Please enter a valid email.'}, status=status.HTTP_400_BAD_REQUEST))
        if not phone and not email:
            return _cors(Response({'error': 'Please give a phone number or an email.'}, status=status.HTTP_400_BAD_REQUEST))

        pincode = re.sub(r'\D', '', d.get('pincode') or '')[:6]
        city = (d.get('city') or '').strip()[:100]
        message = (d.get('message') or '').strip()[:1000]
        source = ((d.get('source') or d.get('utm_source') or 'website_form').strip()[:50]) or 'website_form'

        latlng, distance, within = None, None, None
        place = f"{pincode}, India" if len(pincode) == 6 else (f"{city}, India" if city else '')
        if place:
            latlng = geocode(place)
        if latlng and cfg.center_lat is not None:
            distance = round(haversine_km(cfg.center_lat, cfg.center_lng, latlng[0], latlng[1]), 1)
            if cfg.service_radius_km:
                within = distance <= cfg.service_radius_km

        tenant = cfg.tenant
        existing = None
        if phone:
            existing = Contact.objects.filter(tenant=tenant, phone=phone).first()
        if not existing and email:
            existing = Contact.objects.filter(tenant=tenant, email__iexact=email).first()

        stamp = timezone.now().strftime('%Y-%m-%d %H:%M')
        note = f"[{stamp}] Enquiry via lead form (consent given): {message or '(no message)'}"
        if existing:
            existing.notes = f"{existing.notes or ''}\n{note}".strip()
            existing.save(update_fields=['notes', 'updated_at'])
        else:
            first, _, last = name.partition(' ')
            Contact.objects.create(
                tenant=tenant, first_name=first[:100], last_name=last[:100], email=email or None, phone=phone or None,
                city=city or None, postal_code=pincode or None, contact_type='lead', lifecycle_stage='lead',
                latitude=latlng[0] if latlng else None, longitude=latlng[1] if latlng else None,
                distance_km=distance, within_service_area=within, lead_source=source,
                email_opt_in=bool(email), sms_opt_in=False, notes=note,
            )
        return _cors(Response({'ok': True, 'message': cfg.success_message}, status=status.HTTP_201_CREATED))


WIDGET_JS = r"""(function(){
var s=document.currentScript;if(!s)return;
var base=new URL(s.src).origin, key=s.getAttribute('data-key');
if(!key)return;
fetch(base+'/api/public/lead-form/'+key+'/config/').then(function(r){return r.ok?r.json():null}).then(function(cfg){
if(!cfg)return;
function el(t,a,c){var e=document.createElement(t);for(var k in (a||{}))e.setAttribute(k,a[k]);if(c)e.textContent=c;return e}
var btn=el('button',{type:'button',style:'position:fixed;right:20px;bottom:20px;z-index:2147483000;background:#0b7285;color:#fff;border:0;border-radius:999px;padding:14px 22px;font:600 15px system-ui;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.3)'},'Enquire now');
var ov=el('div',{style:'display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:2147483001;align-items:center;justify-content:center;font-family:system-ui'});
var box=el('form',{style:'background:#fff;color:#222;border-radius:12px;padding:20px;width:min(92vw,380px);max-height:90vh;overflow:auto'});
box.appendChild(el('h3',{style:'margin:0 0 4px;font-size:18px'},cfg.business_name));
box.appendChild(el('p',{style:'margin:0 0 12px;color:#555;font-size:14px'},cfg.intro_message));
var st='width:100%;box-sizing:border-box;padding:9px;margin:0 0 8px;border:1px solid #ccc;border-radius:6px;font-size:14px';
var f={};
[['name','Your name *','text'],['phone','Phone','tel'],['email','Email','email'],['pincode','Pincode (helps us check distance)','text']].forEach(function(x){f[x[0]]=el('input',{name:x[0],placeholder:x[1],type:x[2],style:st});box.appendChild(f[x[0]])});
f.message=el('textarea',{name:'message',placeholder:'How can we help?',rows:'3',style:st});box.appendChild(f.message);
f.website_url=el('input',{name:'website_url',tabindex:'-1',autocomplete:'off',style:'position:absolute;left:-9999px'});box.appendChild(f.website_url);
var lab=el('label',{style:'display:flex;gap:8px;font-size:12px;color:#444;margin:4px 0 10px;align-items:flex-start'});
f.consent=el('input',{type:'checkbox',name:'consent'});lab.appendChild(f.consent);
lab.appendChild(el('span',{},'I agree that '+cfg.business_name+' may contact me about my enquiry using the details I gave.'));box.appendChild(lab);
var msg=el('div',{style:'font-size:13px;margin-bottom:8px;color:#c92a2a'});box.appendChild(msg);
var go=el('button',{type:'submit',style:'background:#0b7285;color:#fff;border:0;border-radius:6px;padding:10px 16px;font:600 14px system-ui;cursor:pointer;width:100%'},'Send enquiry');box.appendChild(go);
var close=el('button',{type:'button',style:'background:none;border:0;color:#666;margin-top:8px;width:100%;cursor:pointer'},'Close');box.appendChild(close);
ov.appendChild(box);document.body.appendChild(btn);document.body.appendChild(ov);
btn.onclick=function(){ov.style.display='flex'};close.onclick=function(){ov.style.display='none'};
box.onsubmit=function(e){e.preventDefault();msg.style.color='#c92a2a';msg.textContent='';go.disabled=true;
var body=new URLSearchParams();body.set('source','website_widget');
['name','phone','email','pincode','message','website_url'].forEach(function(k){body.set(k,f[k].value)});body.set('consent',f.consent.checked?'true':'false');
fetch(base+'/api/public/lead-form/'+key+'/submit/',{method:'POST',body:body}).then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j}})}).then(function(x){
go.disabled=false;if(x.ok){box.innerHTML='';box.appendChild(el('p',{style:'font-size:15px'},x.j.message));var c=el('button',{type:'button',style:'padding:8px 14px;cursor:pointer'},'Close');c.onclick=function(){ov.style.display='none'};box.appendChild(c)}
else{msg.textContent=x.j.error||'Something went wrong. Please try again.'}}).catch(function(){go.disabled=false;msg.textContent='Network error. Please try again.'})};
});})();"""


class PublicLeadWidgetJsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, key=None):
        resp = HttpResponse(WIDGET_JS, content_type='application/javascript; charset=utf-8')
        resp['Cache-Control'] = 'public, max-age=300'
        return _cors(resp)


def _profile(request):
    return UserProfile.objects.select_related('tenant').get(user=request.user)


def _config_payload(cfg):
    frontend = getattr(settings, 'FRONTEND_URL', 'https://zenitherp.online').rstrip('/')
    return {
        'public_key': cfg.public_key, 'is_active': cfg.is_active, 'business_name': cfg.business_name,
        'intro_message': cfg.intro_message, 'success_message': cfg.success_message,
        'center_query': cfg.center_query, 'center_lat': cfg.center_lat, 'center_lng': cfg.center_lng,
        'service_radius_km': cfg.service_radius_km,
        'form_url': f"{frontend}/lead/{cfg.public_key}",
    }


class LeadCaptureConfigView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _payload(self, request, cfg):
        data = _config_payload(cfg)
        base = request.build_absolute_uri('/').rstrip('/')
        if not settings.DEBUG and base.startswith('http://'):
            base = 'https://' + base[len('http://'):]
        data['embed_snippet'] = f'<script src="{base}/api/public/lead-widget/{cfg.public_key}.js" data-key="{cfg.public_key}" async></script>'
        return data

    def get(self, request):
        cfg, _ = LeadCaptureConfig.objects.get_or_create(tenant=_profile(request).tenant)
        return Response(self._payload(request, cfg))

    @role_required('admin', 'principal')
    def put(self, request):
        cfg, _ = LeadCaptureConfig.objects.get_or_create(tenant=_profile(request).tenant)
        d = request.data
        for field in ('business_name', 'intro_message', 'success_message'):
            if field in d:
                setattr(cfg, field, str(d[field]).strip()[:300])
        if 'is_active' in d:
            cfg.is_active = str(d['is_active']).lower() in ('true', '1', 'on')
        if 'service_radius_km' in d:
            raw = d['service_radius_km']
            cfg.service_radius_km = int(raw) if str(raw).strip().isdigit() and int(raw) > 0 else None
        warning = None
        if 'center_query' in d:
            q = str(d['center_query']).strip()[:200]
            if q != cfg.center_query or cfg.center_lat is None:
                cfg.center_query = q
                ll = geocode(f"{q}, India") if q else None
                cfg.center_lat, cfg.center_lng = (ll if ll else (None, None))
                if q and not ll:
                    warning = "Couldn't find that location. Try a 6-digit pincode or a fuller address."
        cfg.save()
        out = self._payload(request, cfg)
        if warning:
            out['warning'] = warning
        return Response(out)


class CapturedLeadsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Contact.objects.filter(tenant=_profile(request).tenant).exclude(lead_source='')
        within = request.query_params.get('within')
        if within == 'in':
            qs = qs.filter(within_service_area=True)
        elif within == 'out':
            qs = qs.filter(within_service_area=False)
        elif within == 'unknown':
            qs = qs.filter(within_service_area__isnull=True)
        rows = qs.order_by('-created_at')[:200]
        return Response([{
            'id': c.id, 'name': c.full_name, 'phone': c.phone, 'email': c.email, 'city': c.city,
            'postal_code': c.postal_code, 'lead_source': c.lead_source, 'distance_km': c.distance_km,
            'within_service_area': c.within_service_area, 'created_at': c.created_at,
        } for c in rows])


class ProspectSearchView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def get(self, request):
        category = request.query_params.get('category', 'shops')
        if category not in CATEGORY_FILTERS:
            return Response({'error': 'Unknown category', 'categories': list(CATEGORY_FILTERS)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            radius = max(1.0, min(float(request.query_params.get('radius_km', 10)), MAX_PROSPECT_RADIUS_KM))
        except ValueError:
            return Response({'error': 'radius_km must be a number'}, status=status.HTTP_400_BAD_REQUEST)
        q = (request.query_params.get('q') or '').strip()
        if not q:
            cfg = LeadCaptureConfig.objects.filter(tenant=_profile(request).tenant).first()
            if cfg and cfg.center_lat is not None:
                lat, lng = cfg.center_lat, cfg.center_lng
            else:
                return Response({'error': 'Enter a pincode or place, or set your service-area center first.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            ll = geocode(f"{q}, India")
            if not ll:
                return Response({'error': "Couldn't find that place. Try a 6-digit pincode."}, status=status.HTTP_404_NOT_FOUND)
            lat, lng = ll
        try:
            results = overpass_search(lat, lng, radius, category)
        except Exception as e:
            logger.warning("Overpass search failed: %s", e)
            return Response({'error': 'The free OpenStreetMap service is busy or the area is too large. Try a smaller radius (2-5 km), a narrower category, or wait a minute.'}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'warning': PROSPECT_WARNING, 'center': {'lat': lat, 'lng': lng}, 'radius_km': radius, 'results': results})


class ProspectSaveView(APIView):
    """Saves a found business to the CRM as a lead - explicitly NOT opted in to
    SMS/WhatsApp, with a note about where the data came from."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def post(self, request):
        tenant = _profile(request).tenant
        d = request.data
        name = (d.get('name') or '').strip()[:100]
        if not name:
            return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)
        phone = _clean_phone(d.get('phone')) or None
        email = (d.get('email') or '').strip().lower()[:254] or None
        dup = Contact.objects.filter(tenant=tenant, lead_source='osm_prospect', first_name=name).first()
        if not dup and phone:
            dup = Contact.objects.filter(tenant=tenant, phone=phone).first()
        if dup:
            return Response({'ok': True, 'duplicate': True, 'id': dup.id})
        lat, lng = d.get('lat'), d.get('lng')
        cfg = LeadCaptureConfig.objects.filter(tenant=tenant).first()
        distance = within = None
        if lat is not None and lng is not None and cfg and cfg.center_lat is not None:
            distance = round(haversine_km(cfg.center_lat, cfg.center_lng, float(lat), float(lng)), 1)
            if cfg.service_radius_km:
                within = distance <= cfg.service_radius_km
        c = Contact.objects.create(
            tenant=tenant, first_name=name, last_name='', email=email, phone=phone, contact_type='lead',
            lifecycle_stage='lead', lead_source='osm_prospect', email_opt_in=False, sms_opt_in=False,
            latitude=float(lat) if lat is not None else None, longitude=float(lng) if lng is not None else None,
            distance_km=distance, within_service_area=within,
            address_line1=(d.get('address') or '')[:255] or None,
            notes="Found on public OpenStreetMap listings. Contact by phone/in person/email with unsubscribe only - no bulk WhatsApp/SMS.",
            custom_fields={'osm_id': d.get('osm_id'), 'website': d.get('website')},
            created_by=request.user,
        )
        return Response({'ok': True, 'id': c.id}, status=status.HTTP_201_CREATED)
