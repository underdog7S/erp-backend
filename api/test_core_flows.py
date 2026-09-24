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


class PharmacyStockFlowTests(APITestCase):
    """Purchase order -> receive -> batch stock -> adjustment -> expiry buckets."""

    def setUp(self):
        from datetime import date, timedelta
        from api.models.plan import Plan
        from pharmacy.models import Medicine, Supplier
        cache.clear()
        self.today = date.today()
        self.timedelta = timedelta
        plan = Plan.objects.create(name='Test Plan', price=0, storage_limit_mb=100, has_pharmacy=True, has_inventory=True)
        self.tenant = Tenant.objects.create(name='Pharma Tenant', industry='pharmacy', plan=plan)
        self.user = make_user(self.tenant, 'pharma_admin', 'admin')
        self.client.force_authenticate(self.user)
        self.supplier = Supplier.objects.create(tenant=self.tenant, name='MediSupply', contact_person='A', phone='1', email='s@x.co', address='x')
        self.medicine = Medicine.objects.create(tenant=self.tenant, name='Paracetamol', manufacturer='Acme', dosage_form='TABLET', expiry_alert_days=30)

    def create_po(self):
        r = self.client.post('/api/pharmacy/purchase-orders/', {
            'supplier': self.supplier.id, 'order_date': str(self.today),
            'expected_delivery': str(self.today + self.timedelta(days=3)),
            'items_input': [{'medicine': self.medicine.id, 'quantity': 100, 'unit_cost': '2.50'}],
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def receive_body(self, po, batch='B1', expiry=None):
        return {'items': [{
            'item': po['items'][0]['id'], 'batch_number': batch,
            'manufacturing_date': str(self.today - self.timedelta(days=30)),
            'expiry_date': str(expiry or self.today + self.timedelta(days=365)),
            'selling_price': '4', 'mrp': '5'}]}

    def test_po_with_items_computes_total(self):
        po = self.create_po()
        self.assertEqual(len(po['items']), 1)
        self.assertEqual(po['total_amount'], '250.00')

    def test_po_without_items_rejected(self):
        r = self.client.post('/api/pharmacy/purchase-orders/', {
            'supplier': self.supplier.id, 'order_date': str(self.today), 'expected_delivery': str(self.today)}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_receive_creates_batch_once(self):
        from pharmacy.models import MedicineBatch
        po = self.create_po()
        r = self.client.post(f"/api/pharmacy/purchase-orders/{po['id']}/receive/", self.receive_body(po), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        batch = MedicineBatch.objects.get(tenant=self.tenant, batch_number='B1')
        self.assertEqual(batch.quantity_available, 100)
        self.assertEqual(str(batch.cost_price), '2.50')
        again = self.client.post(f"/api/pharmacy/purchase-orders/{po['id']}/receive/", self.receive_body(po, 'B2'), format='json')
        self.assertEqual(again.status_code, 400)
        self.assertEqual(MedicineBatch.objects.filter(tenant=self.tenant).count(), 1)

    def test_receive_missing_dates_creates_nothing(self):
        from pharmacy.models import MedicineBatch
        po = self.create_po()
        body = self.receive_body(po)
        body['items'][0]['expiry_date'] = ''
        r = self.client.post(f"/api/pharmacy/purchase-orders/{po['id']}/receive/", body, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(MedicineBatch.objects.count(), 0)

    def test_stock_adjustment_moves_stock_and_blocks_negative(self):
        from pharmacy.models import MedicineBatch
        po = self.create_po()
        self.client.post(f"/api/pharmacy/purchase-orders/{po['id']}/receive/", self.receive_body(po), format='json')
        batch = MedicineBatch.objects.get(batch_number='B1')
        ok = self.client.post('/api/pharmacy/stock-adjustments/', {
            'medicine_batch': batch.id, 'adjustment_type': 'DAMAGED', 'quantity': 30, 'reason': 'broken'}, format='json')
        self.assertEqual(ok.status_code, 201, ok.data)
        batch.refresh_from_db()
        self.assertEqual(batch.quantity_available, 70)
        too_many = self.client.post('/api/pharmacy/stock-adjustments/', {
            'medicine_batch': batch.id, 'adjustment_type': 'REMOVE', 'quantity': 500, 'reason': 'x'}, format='json')
        self.assertEqual(too_many.status_code, 400)
        batch.refresh_from_db()
        self.assertEqual(batch.quantity_available, 70)

    def test_expiry_buckets(self):
        po1, po2, po3 = self.create_po(), self.create_po(), self.create_po()
        for po, name, expiry in [(po1, 'OLD', self.today - self.timedelta(days=5)),
                                 (po2, 'SOON', self.today + self.timedelta(days=10)),
                                 (po3, 'FINE', self.today + self.timedelta(days=400))]:
            self.client.post(f"/api/pharmacy/purchase-orders/{po['id']}/receive/", self.receive_body(po, name, expiry), format='json')

        def names(kind):
            r = self.client.get(f'/api/pharmacy/batches/?expiry={kind}')
            rows = r.data['results'] if isinstance(r.data, dict) else r.data
            return [b['batch_number'] for b in rows]
        self.assertEqual(names('expired'), ['OLD'])
        self.assertEqual(names('soon'), ['SOON'])
        self.assertEqual(names('ok'), ['FINE'])
