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


def _pincode_place_names(pin):
    """Free India Post lookup (no key): 6-digit pincode -> ['Area, District, State', ...]."""
    try:
        r = requests.get(f"https://api.postalpincode.in/pincode/{pin}", timeout=6)
        offices = (r.json()[0].get('PostOffice') or [])[:3]
        return [f"{o['Name']}, {o['District']}, {o['State']}" for o in offices]
    except Exception as e:
        logger.warning("Pincode lookup failed for %s: %s", pin, e)
        return []


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
        try:
            import re
            pin = re.search(r'(\d{6})', key)
            result = _nominatim({'q': key})
            if not result and pin:
                result = _nominatim({'postalcode': pin.group(1), 'country': 'India'})
            if not result and pin:  # OSM has patchy postcode data: go via the post-office area name
                for name in _pincode_place_names(pin.group(1)):
                    time.sleep(1.1)
                    result = _nominatim({'q': name})
                    if result:
                        break
        except Exception as e:
            logger.warning("Geocoding failed for %r: %s", key, e)
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
