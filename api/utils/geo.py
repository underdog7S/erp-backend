"""Free geo helpers: haversine distance, Nominatim geocoding (cached) and
Overpass business search. Both are public OpenStreetMap services with no
key/registration, but they have fair-use policies - so lookups are cached,
rate-limited and always send an identifying User-Agent."""
import math
import threading
import time
import logging
import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

USER_AGENT = "ZenVerseCRM/1.0 (lead-capture; contact: shadabsheikh314@gmail.com)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]  # two tries at 12s max each: must stay under gunicorn's ~30s request limit
MAX_PROSPECT_RADIUS_KM = 30

_geocode_lock = threading.Lock()
_last_geocode_at = [0.0]


def haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _nominatim(params):
    r = requests.get(NOMINATIM_URL, params=dict(params, format='json', limit=1, countrycodes='in'),
                     headers={'User-Agent': USER_AGENT}, timeout=6)
    _last_geocode_at[0] = time.time()
    r.raise_for_status()
    data = r.json()
    return (float(data[0]['lat']), float(data[0]['lon'])) if data else None


def _zippo(pin):
    r = requests.get(f"https://api.zippopotam.us/in/{pin}", timeout=6)
    return r.json().get('places', []) if r.status_code == 200 else []


def _pincode_place_names(pin):
    """Free keyless India pincode lookups -> ['Area, State', ...] (tries two services)."""
    try:
        r = requests.get(f"https://api.postalpincode.in/pincode/{pin}", timeout=5)
        offices = (r.json()[0].get('PostOffice') or [])[:3]
        if offices:
            return [f"{o['Name']}, {o['District']}, {o['State']}" for o in offices]
    except Exception as e:
        logger.warning("postalpincode lookup failed for %s: %s", pin, e)
    try:
        return [f"{pl['place name']}, {pl['state']}" for pl in _zippo(pin)[:3]]
    except Exception as e:
        logger.warning("zippopotam lookup failed for %s: %s", pin, e)
        return []


def _photon(q):
    """Free, keyless OSM-based geocoder (komoot) - separate rate limits from Nominatim."""
    r = requests.get("https://photon.komoot.io/api/", params={'q': q, 'limit': 1, 'bbox': '68,6,98,36'},
                     headers={'User-Agent': USER_AGENT}, timeout=6)
    r.raise_for_status()
    feats = r.json().get('features') or []
    if not feats:
        return None
    lng, lat = feats[0]['geometry']['coordinates']
    return (float(lat), float(lng))


def _via_post_office(pin):
    for name in _pincode_place_names(pin):
        res = _photon(name)
        if res:
            return res
    # last resort: centre of the pincode's listed places (rough, but right city)
    places = _zippo(pin)
    if places:
        lats = sorted(float(x['latitude']) for x in places)
        lngs = sorted(float(x['longitude']) for x in places)
        return (lats[len(lats) // 2], lngs[len(lngs) // 2])
    return None


def geocode(query):
    """Returns (lat, lng) or None. Cached in the DB, misses included."""
    from api.models.lead_capture import GeocodeCache
    key = ' '.join((query or '').lower().split())[:200]
    if not key:
        return None
    cached = GeocodeCache.objects.filter(query=key).first()
    if cached:
        return (cached.lat, cached.lng) if cached.lat is not None else None

    result = None
    with _geocode_lock:  # Nominatim policy: max 1 request/second
        wait = 1.1 - (time.time() - _last_geocode_at[0])
        if wait > 0:
            time.sleep(wait)
        import re
        pin = re.search(r'(\d{6})', key)
        attempts = [lambda: _nominatim({'q': key})]
        if pin:  # a bare pincode confuses name-based geocoders, so go via the post-office area name
            attempts.append(lambda: _nominatim({'postalcode': pin.group(1), 'country': 'India'}))
            attempts.append(lambda: _via_post_office(pin.group(1)))
        else:
            attempts.append(lambda: _photon(key))
        failures = 0
        for attempt in attempts:  # shared cloud IPs often get 429 from Nominatim: fall through to other free sources
            try:
                result = attempt()
            except Exception as e:
                failures += 1
                logger.warning("Geocoding step failed for %r: %s", key, e)
                continue
            if result:
                break
        if not result and failures:
            return None  # transient failure: don't cache as a miss
    GeocodeCache.objects.get_or_create(query=key, defaults={'lat': result[0] if result else None, 'lng': result[1] if result else None})
    return result


CATEGORY_FILTERS = {
    'shops': ['["shop"]'],
    'restaurants': ['["amenity"~"restaurant|cafe|fast_food"]'],
    'schools_colleges': ['["amenity"~"school|college|university|kindergarten"]'],
    'clinics_pharmacies': ['["amenity"~"clinic|hospital|pharmacy|dentist|doctors"]'],
    'hotels': ['["tourism"~"hotel|guest_house|hostel"]'],
    'salons': ['["shop"~"hairdresser|beauty"]'],
    'offices': ['["office"]'],
    'manufacturers': ['["craft"]', '["industrial"]', '["man_made"="works"]'],
}


def overpass_search(lat, lng, radius_km, category):
    """Businesses near a point from OpenStreetMap. Only entries with a name and
    at least one public phone/email/website are returned."""
    radius_km = min(float(radius_km), MAX_PROSPECT_RADIUS_KM)
    filters = CATEGORY_FILTERS.get(category)
    if not filters:
        raise ValueError("Unknown category")
    cache_key = f"overpass:{category}:{round(lat, 3)}:{round(lng, 3)}:{round(radius_km)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    around = f"(around:{int(radius_km * 1000)},{lat},{lng})"
    # Ask only for entries that list contact info (much smaller result), skip relations
    body = "".join(f'nw{f}{around};' for f in filters)
    query = f"[out:json][timeout:10];({body});out center tags 80;"
    last_error = None
    for url in OVERPASS_URLS:  # free public servers are often busy; try the next mirror
        try:
            r = requests.post(url, data={'data': query}, headers={'User-Agent': USER_AGENT}, timeout=12)
            r.raise_for_status()
            break
        except Exception as e:
            last_error = e
            logger.warning("Overpass %s failed: %s", url, e)
    else:
        raise last_error

    out = []
    for el in r.json().get('elements', []):
        tags = el.get('tags', {})
        name = tags.get('name')
        phone = tags.get('phone') or tags.get('contact:phone') or tags.get('contact:mobile')
        email = tags.get('email') or tags.get('contact:email')
        website = tags.get('website') or tags.get('contact:website')
        if not name or not (phone or email or website):
            continue
        plat = el.get('lat') or (el.get('center') or {}).get('lat')
        plng = el.get('lon') or (el.get('center') or {}).get('lon')
        addr = ', '.join(x for x in [tags.get('addr:housenumber'), tags.get('addr:street'), tags.get('addr:suburb'),
                                      tags.get('addr:city'), tags.get('addr:postcode')] if x)
        out.append({
            'osm_id': f"{el.get('type')}/{el.get('id')}", 'name': name, 'phone': phone, 'email': email,
            'website': website, 'address': addr, 'lat': plat, 'lng': plng,
            'distance_km': round(haversine_km(lat, lng, plat, plng), 1) if plat is not None and plng is not None else None,
        })
    out.sort(key=lambda x: (x['distance_km'] is None, x['distance_km']))
    cache.set(cache_key, out, 3600)
    return out
