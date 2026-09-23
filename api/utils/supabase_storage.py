"""
Uploads files to Supabase Storage (S3-compatible, included free with the
same Supabase project already used for the database) instead of local disk -
Render's filesystem is ephemeral and wiped on every deploy, which would
silently lose message history attachments and break outbound MMS/WhatsApp
media sends that need a stable, publicly-fetchable URL.

Uses Supabase's own Storage REST API directly (not the S3-compatible layer)
so it only needs SUPABASE_URL/SUPABASE_SERVICE_KEY, which are already set as
platform env vars - no separate S3 credentials to provision.
"""
import os
import requests
from django.utils.crypto import get_random_string

BUCKET = "communications"


def _supabase_headers():
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    return {
        'Authorization': f'Bearer {service_key}',
        'apikey': service_key,
    }


def ensure_bucket_exists():
    """Idempotent - creates the bucket if it doesn't exist yet, does nothing
    if it already does. Safe to call on every upload."""
    supabase_url = os.getenv('SUPABASE_URL')
    resp = requests.post(
        f'{supabase_url}/storage/v1/bucket',
        json={'id': BUCKET, 'name': BUCKET, 'public': True},
        headers={**_supabase_headers(), 'Content-Type': 'application/json'},
        timeout=10,
    )
    # 400 "Bucket already exists" is the expected steady-state response after
    # the first call ever - anything else is a real failure worth raising.
    if resp.status_code not in (200, 201) and 'already exists' not in resp.text.lower():
        raise RuntimeError(f'Failed to create Supabase Storage bucket: {resp.status_code} {resp.text}')


def upload_file(tenant_id, filename, content, content_type):
    """Uploads a file and returns its public URL. `content` is bytes.
    Randomizes the stored filename (keeping the extension) so URLs aren't
    guessable even though the bucket is public - a business inbox's
    attachments shouldn't be enumerable just by trying sequential paths."""
    supabase_url = os.getenv('SUPABASE_URL')
    if not supabase_url or not os.getenv('SUPABASE_SERVICE_KEY'):
        raise RuntimeError('SUPABASE_URL/SUPABASE_SERVICE_KEY are not configured.')

    ensure_bucket_exists()

    ext = os.path.splitext(filename)[1].lower()
    random_name = f'{get_random_string(24)}{ext}'
    path = f'tenant_{tenant_id}/{random_name}'

    resp = requests.post(
        f'{supabase_url}/storage/v1/object/{BUCKET}/{path}',
        data=content,
        headers={**_supabase_headers(), 'Content-Type': content_type or 'application/octet-stream'},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f'Supabase Storage upload failed: {resp.status_code} {resp.text}')

    return f'{supabase_url}/storage/v1/object/public/{BUCKET}/{path}'


def classify_attachment(content_type, filename=''):
    """Maps a MIME type (or file extension fallback) to the coarse category
    the frontend uses to decide how to render an attachment."""
    content_type = (content_type or '').lower()
    ext = os.path.splitext(filename)[1].lower()
    if content_type.startswith('image/') or ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return 'image'
    if content_type.startswith('audio/') or ext in ('.mp3', '.ogg', '.wav', '.m4a'):
        return 'audio'
    if content_type.startswith('video/') or ext in ('.mp4', '.mov', '.webm'):
        return 'video'
    return 'document'
