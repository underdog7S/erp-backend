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


class ListPaginationTests(APITestCase):
    def test_lists_are_not_silently_cut_at_ten_rows(self):
        from api.models.plan import Plan
        from pharmacy.models import Supplier
        plan = Plan.objects.create(name='Pg Plan', price=0, storage_limit_mb=100, has_pharmacy=True)
        tenant = Tenant.objects.create(name='Big Pharmacy', industry='pharmacy', plan=plan)
        self.client.force_authenticate(make_user(tenant, 'pg_admin', 'admin'))
        for i in range(25):
            Supplier.objects.create(tenant=tenant, name=f'Supplier {i}', contact_person='A', phone='1', email='s@x.co', address='x')
        r = self.client.get('/api/pharmacy/suppliers/')
        self.assertEqual(r.data['count'], 25)
        self.assertEqual(len(r.data['results']), 25)
        small = self.client.get('/api/pharmacy/suppliers/?page_size=10')
        self.assertEqual(len(small.data['results']), 10)


class RetailProcurementTests(APITestCase):
    """Purchase order -> (partial) receipt -> stock; transfers; adjustments."""

    def setUp(self):
        from datetime import date
        from api.models.plan import Plan
        from retail.models import Product, Supplier, Warehouse
        cache.clear()
        self.today = date.today()
        plan = Plan.objects.create(name='Retail Plan', price=0, storage_limit_mb=100, has_retail=True, has_inventory=True)
        self.tenant = Tenant.objects.create(name='Shop Tenant', industry='retail', plan=plan)
        self.client.force_authenticate(make_user(self.tenant, 'retail_admin', 'admin'))
        self.supplier = Supplier.objects.create(tenant=self.tenant, name='Wholesaler', contact_person='A', phone='1', address='x')
        self.main = Warehouse.objects.create(tenant=self.tenant, name='Main', address='x', contact_person='A', phone='1', is_primary=True)
        self.second = Warehouse.objects.create(tenant=self.tenant, name='Shop 2', address='y', contact_person='B', phone='2')
        self.product = Product.objects.create(tenant=self.tenant, name='Rice 5kg', sku='RICE5', cost_price=200, selling_price=260, mrp=280)

    def stock(self, warehouse):
        from retail.models import Inventory
        row = Inventory.objects.filter(tenant=self.tenant, product=self.product, warehouse=warehouse).first()
        return row.quantity_on_hand if row else 0

    def make_po(self, qty=50):
        r = self.client.post('/api/retail/purchase-orders/', {
            'supplier': self.supplier.id, 'order_date': str(self.today), 'expected_delivery': str(self.today), 'status': 'ORDERED',
            'items_input': [{'product': self.product.id, 'quantity': qty, 'unit_cost': '200'}]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def test_po_total_and_partial_then_full_receipt(self):
        po = self.make_po(50)
        self.assertEqual(po['total_amount'], '10000.00')
        line = po['items'][0]['id']
        url = f"/api/retail/purchase-orders/{po['id']}/receive/"
        first = self.client.post(url, {'warehouse': self.main.id, 'items': [{'item': line, 'quantity': 20}]}, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data['status'], 'PARTIAL_RECEIVED')
        self.assertEqual(self.stock(self.main), 20)
        over = self.client.post(url, {'warehouse': self.main.id, 'items': [{'item': line, 'quantity': 31}]}, format='json')
        self.assertEqual(over.status_code, 400)
        self.assertEqual(self.stock(self.main), 20)
        rest = self.client.post(url, {'warehouse': self.main.id, 'items': [{'item': line, 'quantity': 30}]}, format='json')
        self.assertEqual(rest.data['status'], 'RECEIVED')
        self.assertEqual(self.stock(self.main), 50)
        again = self.client.post(url, {'warehouse': self.main.id, 'items': [{'item': line, 'quantity': 1}]}, format='json')
        self.assertEqual(again.status_code, 400)

    def test_po_without_items_rejected(self):
        r = self.client.post('/api/retail/purchase-orders/', {
            'supplier': self.supplier.id, 'order_date': str(self.today), 'expected_delivery': str(self.today),
            'items_input': []}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_transfer_moves_stock_in_two_steps(self):
        po = self.make_po(40)
        self.client.post(f"/api/retail/purchase-orders/{po['id']}/receive/", {
            'warehouse': self.main.id, 'items': [{'item': po['items'][0]['id'], 'quantity': 40}]}, format='json')
        t = self.client.post('/api/retail/stock-transfers/', {
            'from_warehouse': self.main.id, 'to_warehouse': self.second.id, 'transfer_date': str(self.today),
            'items_input': [{'product': self.product.id, 'quantity': 15}]}, format='json')
        self.assertEqual(t.status_code, 201, t.data)
        self.assertEqual(t.data['status'], 'DRAFT')
        tid = t.data['id']
        self.assertEqual(self.stock(self.main), 40)
        self.assertEqual(self.client.post(f'/api/retail/stock-transfers/{tid}/complete/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/retail/stock-transfers/{tid}/dispatch/').status_code, 200)
        self.assertEqual((self.stock(self.main), self.stock(self.second)), (25, 0))
        self.assertEqual(self.client.post(f'/api/retail/stock-transfers/{tid}/complete/').status_code, 200)
        self.assertEqual((self.stock(self.main), self.stock(self.second)), (25, 15))
        self.assertEqual(self.client.post(f'/api/retail/stock-transfers/{tid}/dispatch/').status_code, 400)

    def test_transfer_cannot_send_more_than_available(self):
        t = self.client.post('/api/retail/stock-transfers/', {
            'from_warehouse': self.main.id, 'to_warehouse': self.second.id, 'transfer_date': str(self.today),
            'items_input': [{'product': self.product.id, 'quantity': 5}]}, format='json')
        r = self.client.post(f"/api/retail/stock-transfers/{t.data['id']}/dispatch/")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.stock(self.main), 0)

    def test_transfer_to_same_warehouse_rejected(self):
        r = self.client.post('/api/retail/stock-transfers/', {
            'from_warehouse': self.main.id, 'to_warehouse': self.main.id, 'transfer_date': str(self.today),
            'items_input': [{'product': self.product.id, 'quantity': 1}]}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_adjustments_add_and_remove_and_block_negative(self):
        add = self.client.post('/api/retail/stock-adjustments/', {
            'warehouse': self.main.id, 'adjustment_type': 'ADD', 'reason': 'opening stock',
            'items_input': [{'product': self.product.id, 'quantity': 10}]}, format='json')
        self.assertEqual(add.status_code, 201, add.data)
        self.assertEqual(self.stock(self.main), 10)
        rm = self.client.post('/api/retail/stock-adjustments/', {
            'warehouse': self.main.id, 'adjustment_type': 'DAMAGED', 'reason': 'water damage',
            'items_input': [{'product': self.product.id, 'quantity': 4}]}, format='json')
        self.assertEqual(rm.status_code, 201)
        self.assertEqual(self.stock(self.main), 6)
        too_many = self.client.post('/api/retail/stock-adjustments/', {
            'warehouse': self.main.id, 'adjustment_type': 'LOSS', 'reason': 'lost',
            'items_input': [{'product': self.product.id, 'quantity': 99}]}, format='json')
        self.assertEqual(too_many.status_code, 400)
        self.assertEqual(self.stock(self.main), 6)


class GstHelperTests(APITestCase):
    def test_inclusive_and_exclusive_tax(self):
        from decimal import Decimal
        from api.gst import line_tax
        self.assertEqual(line_tax(118, 18, True), (Decimal('100.00'), Decimal('18.00')))
        self.assertEqual(line_tax(100, 18, False), (Decimal('100.00'), Decimal('18.00')))
        self.assertEqual(line_tax(100, 0, True), (Decimal('100.00'), Decimal('0.00')))

    def test_cgst_sgst_always_add_back_to_the_tax(self):
        from decimal import Decimal
        from api.gst import split_cgst_sgst
        cgst, sgst = split_cgst_sgst(Decimal('9.01'))
        self.assertEqual(cgst + sgst, Decimal('9.01'))

    def test_intra_vs_inter_state(self):
        from api.gst import is_intra_state
        self.assertTrue(is_intra_state('27AAPFU0939F1ZV', '27ABCDE1234F1Z5'))
        self.assertFalse(is_intra_state('27AAPFU0939F1ZV', '29ABCDE1234F1Z5'))
        self.assertTrue(is_intra_state('27AAPFU0939F1ZV', ''))  # counter sale, buyer unknown
        self.assertFalse(is_intra_state('27AAPFU0939F1ZV', '', place_of_supply='07'))

    def test_gstin_checksum(self):
        from api.gst import is_valid_gstin
        self.assertTrue(is_valid_gstin('27AAPFU0939F1ZV'))
        self.assertFalse(is_valid_gstin('27AAPFU0939F1ZX'))
        self.assertFalse(is_valid_gstin('not-a-gstin'))


class PharmacySaleTests(APITestCase):
    """Bills must take the earliest-expiry stock, refuse expired or missing stock, and carry GST."""

    def setUp(self):
        from datetime import date, timedelta
        from api.models.plan import Plan
        from pharmacy.models import Medicine, MedicineBatch, Supplier
        cache.clear()
        today = date.today()
        plan = Plan.objects.create(name='Sale Plan', price=0, storage_limit_mb=100, has_pharmacy=True)
        self.tenant = Tenant.objects.create(name='Sale Pharmacy', industry='pharmacy', plan=plan)
        self.client.force_authenticate(make_user(self.tenant, 'sale_admin', 'admin'))
        supplier = Supplier.objects.create(tenant=self.tenant, name='S', contact_person='A', phone='1', email='s@x.co', address='x')
        self.medicine = Medicine.objects.create(tenant=self.tenant, name='Amoxicillin', manufacturer='Acme', dosage_form='CAPSULE',
                                                gst_rate=12, hsn_code='3004')

        def batch(number, days, qty):
            return MedicineBatch.objects.create(
                tenant=self.tenant, medicine=self.medicine, batch_number=number, supplier=supplier,
                manufacturing_date=today - timedelta(days=200), expiry_date=today + timedelta(days=days),
                cost_price=5, selling_price=112, mrp=112, quantity_received=qty, quantity_available=qty)
        self.expired = batch('EXPIRED', -3, 50)
        self.later = batch('LATER', 300, 50)
        self.sooner = batch('SOONER', 60, 20)

    def sell(self, qty, price=112):
        line = {'medicine': 'Amoxicillin', 'quantity': qty}
        if price is not None:
            line['price'] = price
        return self.client.post('/api/pharmacy/sales/', {'payment_method': 'CASH', 'items': [line]}, format='json')

    def test_earliest_expiry_first_and_never_expired(self):
        r = self.sell(30)
        self.assertEqual(r.status_code, 201, r.data)
        for b in (self.expired, self.later, self.sooner):
            b.refresh_from_db()
        self.assertEqual(self.sooner.quantity_available, 0)   # 20 taken first
        self.assertEqual(self.later.quantity_available, 40)   # remaining 10 from the next expiry
        self.assertEqual(self.expired.quantity_available, 50)  # never touched
        self.assertEqual(len(r.data['items']), 2)

    def test_gst_is_extracted_from_inclusive_price(self):
        r = self.sell(10, price=112)  # 1120 gross at 12% inclusive -> 120 tax
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['subtotal'], '1120.00')
        self.assertEqual(r.data['total_amount'], '1120.00')
        self.assertEqual(r.data['tax_amount'], '120.00')
        self.assertEqual((r.data['cgst_amount'], r.data['sgst_amount']), ('60.00', '60.00'))
        self.assertEqual(r.data['items'][0]['hsn_code'], '3004')

    def test_more_than_in_date_stock_is_refused_and_nothing_changes(self):
        from pharmacy.models import Sale
        r = self.sell(71)  # only 70 in date
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Sale.objects.count(), 0)
        self.sooner.refresh_from_db()
        self.assertEqual(self.sooner.quantity_available, 20)

    def test_unknown_medicine_is_a_clean_400(self):
        r = self.client.post('/api/pharmacy/sales/', {
            'payment_method': 'CASH', 'items': [{'medicine': 'Nonexistent', 'quantity': 1, 'price': 5}]}, format='json')
        self.assertEqual(r.status_code, 400)


class RetailSaleGstTests(APITestCase):
    def setUp(self):
        from api.models.plan import Plan
        from retail.models import Inventory, Product, Warehouse
        cache.clear()
        plan = Plan.objects.create(name='Retail Sale Plan', price=0, storage_limit_mb=100, has_retail=True)
        self.tenant = Tenant.objects.create(name='Sale Shop', industry='retail', plan=plan)
        self.client.force_authenticate(make_user(self.tenant, 'rsale_admin', 'admin'))
        self.wh = Warehouse.objects.create(tenant=self.tenant, name='Main', address='x', contact_person='A', phone='1', is_primary=True)
        self.tv = Product.objects.create(tenant=self.tenant, name='LED TV', sku='TV1', cost_price=1, selling_price=1, mrp=1,
                                         gst_rate=18, hsn_code='8528', price_includes_tax=False)
        self.tv.mrp = self.tv.selling_price = 1000
        self.tv.save()
        self.rice = Product.objects.create(tenant=self.tenant, name='Rice', sku='R1', cost_price=1, selling_price=105, mrp=105,
                                           gst_rate=5, hsn_code='1006')
        Inventory.objects.create(tenant=self.tenant, product=self.rice, warehouse=self.wh, quantity_on_hand=10)
        from retail.models import Customer
        self.customer = Customer.objects.create(tenant=self.tenant, name='Walk In', phone='9000000000', email='', address='x')

    def test_inclusive_and_exclusive_lines_together(self):
        r = self.client.post('/api/retail/sales/', {
            'warehouse': self.wh.id, 'customer': self.customer.id, 'payment_method': 'CASH', 'customer_name_input': 'Walk In', 'phone': '9000000000',
            'items': [{'product': 'Rice', 'quantity': 2, 'price': 105},      # 210 incl. 5% -> tax 10
                      {'product': 'LED TV', 'quantity': 1, 'price': 1000}]},  # +18% on top -> tax 180
            format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['subtotal'], '1210.00')
        self.assertEqual(r.data['tax_amount'], '190.00')
        self.assertEqual(r.data['total_amount'], '1390.00')  # 1210 + the 180 charged on top of the TV
        self.assertEqual((r.data['cgst_amount'], r.data['sgst_amount']), ('95.00', '95.00'))

    def test_unknown_product_is_a_clean_400(self):
        r = self.client.post('/api/retail/sales/', {
            'warehouse': self.wh.id, 'payment_method': 'CASH', 'items': [{'product': 'Ghost', 'quantity': 1, 'price': 5}]}, format='json')
        self.assertEqual(r.status_code, 400)


class CatalogTests(APITestCase):
    """Adding a medicine / product by hand, and seeing stock in the list."""

    def setUp(self):
        from api.models.plan import Plan
        cache.clear()
        plan = Plan.objects.create(name='Catalog Plan', price=0, storage_limit_mb=100, has_pharmacy=True, has_retail=True)
        self.tenant = Tenant.objects.create(name='Catalog Tenant', industry='pharmacy', plan=plan)
        self.client.force_authenticate(make_user(self.tenant, 'catalog_admin', 'admin'))

    def test_medicine_create_and_stock_totals(self):
        from datetime import date, timedelta
        from pharmacy.models import MedicineBatch, Supplier
        r = self.client.post('/api/pharmacy/medicines/', {
            'name': 'Cetirizine', 'manufacturer': 'Acme', 'dosage_form': 'TABLET', 'strength': '10mg',
            'hsn_code': '3004', 'gst_rate': '12', 'price_includes_tax': True}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        med_id = r.data['id']
        supplier = Supplier.objects.create(tenant=self.tenant, name='S', contact_person='A', phone='1', email='s@x.co', address='x')
        today = date.today()
        for number, days, qty in (('A', 90, 10), ('B', 30, 5), ('GONE', 10, 0)):
            MedicineBatch.objects.create(
                tenant=self.tenant, medicine_id=med_id, batch_number=number, supplier=supplier,
                manufacturing_date=today - timedelta(days=100), expiry_date=today + timedelta(days=days),
                cost_price=1, selling_price=2, mrp=3, quantity_received=qty, quantity_available=qty)
        row = self.client.get('/api/pharmacy/medicines/').data['results'][0]
        self.assertEqual(row['total_stock'], 15)
        self.assertEqual(row['nearest_expiry'], str(today + timedelta(days=30)))  # empty batch ignored
        self.assertEqual(row['gst_rate'], '12.00')

    def test_product_create_without_sku_and_stock_total(self):
        from retail.models import Warehouse
        r = self.client.post('/api/retail/products/', {
            'name': 'Notebook', 'cost_price': '20', 'selling_price': '30', 'mrp': '35',
            'gst_rate': '12', 'hsn_code': '4820', 'price_includes_tax': 'true'})  # multipart, like the form
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data['sku'].startswith('SKU-'))
        self.assertTrue(r.data['price_includes_tax'])
        wh = Warehouse.objects.create(tenant=self.tenant, name='Main', address='x', contact_person='A', phone='1')
        adj = self.client.post('/api/retail/stock-adjustments/', {
            'warehouse': wh.id, 'adjustment_type': 'ADD', 'reason': 'opening stock',
            'items_input': [{'product': r.data['id'], 'quantity': 12}]}, format='json')
        self.assertEqual(adj.status_code, 201, adj.data)
        self.assertEqual(self.client.get('/api/retail/products/').data['results'][0]['total_stock'], 12)


class SalePricingTests(PharmacySaleTests):
    """Bills default to the batch / catalogue price and can never exceed MRP."""

    def test_price_defaults_to_batch_price(self):
        r = self.sell(2, price=None)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['subtotal'], '224.00')

    def test_price_above_mrp_refused(self):
        r = self.sell(1, price=500)
        self.assertEqual(r.status_code, 400)
        self.assertIn('MRP', str(r.data))

    def test_discount_below_mrp_allowed(self):
        r = self.sell(1, price=100)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['subtotal'], '100.00')

    def test_exact_medicine_id_beats_name_match(self):
        from pharmacy.models import Medicine, MedicineBatch
        twin = Medicine.objects.create(tenant=self.tenant, name='Amoxicillin Forte', manufacturer='Acme', dosage_form='CAPSULE')
        sup = self.sooner.supplier
        from datetime import date, timedelta
        MedicineBatch.objects.create(tenant=self.tenant, medicine=twin, batch_number='F1', supplier=sup,
                                     manufacturing_date=date.today() - timedelta(days=10), expiry_date=date.today() + timedelta(days=200),
                                     cost_price=1, selling_price=50, mrp=60, quantity_received=5, quantity_available=5)
        r = self.client.post('/api/pharmacy/sales/', {
            'payment_method': 'CASH', 'items': [{'medicine': 'Amoxicillin Forte', 'medicine_id': twin.id, 'quantity': 1}]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['subtotal'], '50.00')


class RetailPosTests(RetailSaleGstTests):
    def test_walk_in_sale_defaults_price_and_customer(self):
        r = self.client.post('/api/retail/sales/', {
            'warehouse': self.wh.id, 'payment_method': 'CASH',
            'items': [{'product': 'Rice', 'product_id': self.rice.id, 'quantity': 3}]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['subtotal'], '315.00')
        self.assertEqual(r.data['customer_name'], 'Walk-in Customer')

    def test_price_above_mrp_refused(self):
        r = self.client.post('/api/retail/sales/', {
            'warehouse': self.wh.id, 'payment_method': 'CASH',
            'items': [{'product': 'Rice', 'quantity': 1, 'price': 999}]}, format='json')
        self.assertEqual(r.status_code, 400)
