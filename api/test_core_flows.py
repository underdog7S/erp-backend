"""Regression tests for flows that were previously only checked by ad-hoc scripts.

Run against a throwaway SQLite database (never the production Postgres):
    DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: python manage.py test api.test_core_flows
"""
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

import api.views.lead_capture_views as lead_views
from api.models.crm import Contact
from api.models.lead_capture import LeadCaptureConfig
from api.models.user import Role, Tenant, UserProfile


def make_user(tenant, username, role_name, password='A-long-test-Passw0rd!', email=''):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = User.objects.create_user(username=username, password=password, email=email)
    UserProfile.objects.create(user=user, tenant=tenant, role=role)
    return user


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.tenant = Tenant.objects.create(name='Login Tenant', industry='education')
        make_user(self.tenant, 'teamuser', 'staff', email='real@example.com')

    def test_login_by_username(self):
        r = self.client.post('/api/login/', {'username': 'teamuser', 'password': 'A-long-test-Passw0rd!'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def test_login_by_email(self):
        r = self.client.post('/api/login/', {'username': 'REAL@example.com', 'password': 'A-long-test-Passw0rd!'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def test_wrong_password_and_unknown_email_fail_the_same_way(self):
        bad = self.client.post('/api/login/', {'username': 'real@example.com', 'password': 'nope'}, format='json')
        unknown = self.client.post('/api/login/', {'username': 'ghost@example.com', 'password': 'nope'}, format='json')
        self.assertEqual(bad.status_code, 401)
        self.assertEqual(unknown.status_code, 401)

    def test_login_is_throttled(self):
        codes = [self.client.post('/api/login/', {'username': 'x', 'password': 'y'}, format='json').status_code for _ in range(12)]
        self.assertEqual(codes[-1], 429)
        self.assertNotIn(429, codes[:10])


class ChangePasswordTests(APITestCase):
    def setUp(self):
        cache.clear()
        tenant = Tenant.objects.create(name='Pw Tenant', industry='retail')
        self.user = make_user(tenant, 'pwuser', 'staff')
        self.client.force_authenticate(self.user)

    def test_wrong_old_password(self):
        r = self.client.post('/api/users/change-password/', {'old_password': 'bad', 'new_password': 'Another-Long-Passw0rd!'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_weak_new_password_rejected(self):
        r = self.client.post('/api/users/change-password/', {'old_password': 'A-long-test-Passw0rd!', 'new_password': 'short'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('12', r.data['error'])

    def test_success(self):
        r = self.client.post('/api/users/change-password/', {'old_password': 'A-long-test-Passw0rd!', 'new_password': 'Another-Long-Passw0rd!'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Another-Long-Passw0rd!'))


class HealthTests(APITestCase):
    def test_healthz(self):
        self.assertEqual(self.client.get('/healthz/').status_code, 200)


PLACES = {
    '600001, india': (13.0827, 80.2707),  # Chennai centre
    '600040, india': (13.0850, 80.2101),  # ~6 km away
    '110001, india': (28.6328, 77.2197),  # Delhi, far away
}


class LeadCaptureTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.tenant = Tenant.objects.create(name='Lead Tenant', industry='education')
        self.admin = make_user(self.tenant, 'lead_admin', 'admin')
        self.staff = make_user(self.tenant, 'lead_staff', 'staff')
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)
        patcher = mock.patch.object(lead_views, 'geocode', lambda q: PLACES.get(q.lower()))
        patcher.start()
        self.addCleanup(patcher.stop)
        r = self.admin_client.put('/api/lead-capture/config/', {
            'business_name': 'Test College', 'center_query': '600001', 'service_radius_km': 100}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.key = r.data['public_key']
        self.base = {'name': 'Asha Kumar', 'phone': '+91 98765 43210', 'email': 'asha@example.com',
                     'pincode': '600040', 'message': 'B.Com fees?', 'consent': 'true'}
        self.public = APIClient()

    def submit(self, **overrides):
        return self.public.post(f'/api/public/lead-form/{self.key}/submit/', dict(self.base, **overrides))

    def test_in_area_lead_is_flagged_with_distance(self):
        r = self.submit()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r['Access-Control-Allow-Origin'], '*')
        c = Contact.objects.get(tenant=self.tenant, phone='919876543210')
        self.assertTrue(c.within_service_area)
        self.assertTrue(5 < c.distance_km < 10)
        self.assertEqual(c.lead_source, 'website_form')
        self.assertFalse(c.sms_opt_in)

    def test_out_of_area_and_unknown_location(self):
        self.submit(name='Far Away', phone='9000000001', email='', pincode='110001')
        self.submit(name='No Loc', phone='9000000002', email='', pincode='')
        self.assertIs(Contact.objects.get(phone='9000000001').within_service_area, False)
        self.assertIsNone(Contact.objects.get(phone='9000000002').within_service_area)
        out = self.admin_client.get('/api/lead-capture/leads/?within=out').data
        self.assertEqual([x['name'] for x in out], ['Far Away'])

    def test_validation(self):
        self.assertEqual(self.submit(consent='false').status_code, 400)
        self.assertEqual(self.submit(name='').status_code, 400)
        self.assertEqual(self.submit(phone='', email='').status_code, 400)

    def test_honeypot_creates_nothing(self):
        r = self.submit(website_url='spam.example')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Contact.objects.filter(tenant=self.tenant).count(), 0)

    def test_duplicate_phone_merges(self):
        self.submit()
        self.submit(message='second visit')
        self.assertEqual(Contact.objects.filter(tenant=self.tenant, phone='919876543210').count(), 1)
        self.assertIn('second visit', Contact.objects.get(phone='919876543210').notes)

    def test_rate_limit(self):
        for i in range(10):
            self.submit(phone=f'90000001{i:02d}', email='')
        self.assertEqual(self.submit(phone='9000000199', email='').status_code, 429)

    def test_unknown_key_404(self):
        self.assertEqual(self.public.get('/api/public/lead-form/nope/config/').status_code, 404)

    def test_widget_js(self):
        js = self.public.get(f'/api/public/lead-widget/{self.key}.js')
        self.assertEqual(js.status_code, 200)
        self.assertIn(b'Enquire now', js.content)
        self.assertEqual(js['Access-Control-Allow-Origin'], '*')

    def test_staff_cannot_change_config_or_use_prospect_finder(self):
        staff = APIClient()
        staff.force_authenticate(self.staff)
        self.assertEqual(staff.put('/api/lead-capture/config/', {'service_radius_km': 5}, format='json').status_code, 403)
        self.assertEqual(staff.get('/api/lead-capture/prospects/?category=shops&q=600001').status_code, 403)
        self.assertEqual(staff.get('/api/lead-capture/leads/').status_code, 200)

    def test_prospect_search_and_save(self):
        found = [{'osm_id': 'node/1', 'name': 'Sharma Traders', 'phone': '+91 44 2345 6789', 'email': None,
                  'website': 'x.in', 'address': 'MG Road', 'lat': 13.09, 'lng': 80.28, 'distance_km': 1.2}]
        with mock.patch.object(lead_views, 'overpass_search', lambda *a, **k: found):
            r = self.admin_client.get('/api/lead-capture/prospects/?category=shops&q=600001&radius_km=500')
            self.assertEqual(r.status_code, 200)
            self.assertIn('bulk WhatsApp', r.data['warning'])
            self.assertEqual(r.data['radius_km'], 30)
            self.assertEqual(self.admin_client.get('/api/lead-capture/prospects/?category=bogus&q=600001').status_code, 400)
        saved = self.admin_client.post('/api/lead-capture/prospects/save/', found[0], format='json')
        self.assertEqual(saved.status_code, 201)
        contact = Contact.objects.get(id=saved.data['id'])
        self.assertEqual(contact.lead_source, 'osm_prospect')
        self.assertFalse(contact.sms_opt_in)
        self.assertFalse(contact.email_opt_in)
        self.assertTrue(self.admin_client.post('/api/lead-capture/prospects/save/', found[0], format='json').data['duplicate'])

    def test_contacts_api_filters_by_source_and_area(self):
        self.submit()
        self.submit(name='Far Away', phone='9000000001', email='', pincode='110001')
        r = self.admin_client.get('/api/crm/contacts/?lead_source=website_form&within_service_area=false')
        names = [c['full_name'] for c in r.data['results']]
        self.assertEqual(names, ['Far Away'])
