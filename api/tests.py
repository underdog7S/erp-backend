from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import User
from api.models.user import UserProfile, Role, Tenant
from education.models import FeePayment, Department
from api.models.payments import PaymentTransaction

class UserManagementTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test School", industry="education")
        self.admin_role = Role.objects.create(name="admin")
        self.accountant_role = Role.objects.create(name="accountant")
        self.teacher_role = Role.objects.create(name="teacher")
        self.admin_user = User.objects.create_user(username="admin", password="adminpass")
        self.accountant_user = User.objects.create_user(username="accountant", password="accpass")
        self.teacher_user = User.objects.create_user(username="teacher", password="teachpass")
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, tenant=self.tenant, role=self.admin_role)
        self.accountant_profile = UserProfile.objects.create(user=self.accountant_user, tenant=self.tenant, role=self.accountant_role)
        self.teacher_profile = UserProfile.objects.create(user=self.teacher_user, tenant=self.tenant, role=self.teacher_role)
        self.user_to_edit = User.objects.create_user(username="editme", password="editpass")
        self.user_profile_to_edit = UserProfile.objects.create(user=self.user_to_edit, tenant=self.tenant, role=self.teacher_role)

    def test_admin_can_edit_user(self):
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        data = {"email": "edited@example.com"}
        response = client.put(reverse('userprofile-detail', args=[self.user_to_edit.id]), data)
        self.assertIn(response.status_code, [200, 204])

    def test_accountant_cannot_edit_user(self):
        client = APIClient()
        client.force_authenticate(user=self.accountant_user)
        data = {"email": "fail@example.com"}
        response = client.put(reverse('userprofile-detail', args=[self.user_to_edit.id]), data)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_delete_user(self):
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        response = client.delete(reverse('userprofile-detail', args=[self.user_to_edit.id]))
        self.assertIn(response.status_code, [200, 204])

    def test_teacher_cannot_delete_user(self):
        client = APIClient()
        client.force_authenticate(user=self.teacher_user)
        response = client.delete(reverse('userprofile-detail', args=[self.user_to_edit.id]))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_assign_role(self):
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        data = {"role": "accountant"}
        response = client.patch(reverse('userprofile-detail', args=[self.user_to_edit.id]), data)
        self.assertIn(response.status_code, [200, 204])

    def test_accountant_cannot_assign_role(self):
        client = APIClient()
        client.force_authenticate(user=self.accountant_user)
        data = {"role": "admin"}
        response = client.patch(reverse('userprofile-detail', args=[self.user_to_edit.id]), data)
        self.assertEqual(response.status_code, 403)

class PaymentTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test School", industry="education")
        self.admin_role = Role.objects.create(name="admin")
        self.accountant_role = Role.objects.create(name="accountant")
        self.admin_user = User.objects.create_user(username="admin", password="adminpass")
        self.accountant_user = User.objects.create_user(username="accountant", password="accpass")
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, tenant=self.tenant, role=self.admin_role)
        self.accountant_profile = UserProfile.objects.create(user=self.accountant_user, tenant=self.tenant, role=self.accountant_role)
        self.payment = PaymentTransaction.objects.create(user=self.admin_user, tenant=self.tenant, plan=None, order_id="ORD1", payment_id="PAY1", signature="sig1", amount=100, currency="INR", status="created")

    def test_admin_can_view_payments(self):
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        response = client.get(reverse('paymenttransaction-list'))
        self.assertEqual(response.status_code, 200)

    def test_accountant_can_add_payment(self):
        client = APIClient()
        client.force_authenticate(user=self.accountant_user)
        data = {"user": self.accountant_user.id, "tenant": self.tenant.id, "order_id": "ORD2", "payment_id": "PAY2", "signature": "sig2", "amount": 200, "currency": "INR", "status": "created"}
        response = client.post(reverse('paymenttransaction-list'), data)
        self.assertIn(response.status_code, [201, 200])

    def test_accountant_cannot_delete_payment(self):
        client = APIClient()
        client.force_authenticate(user=self.accountant_user)
        response = client.delete(reverse('paymenttransaction-detail', args=[self.payment.id]))
        self.assertEqual(response.status_code, 403)

class DepartmentTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test School", industry="education")
        self.admin_role = Role.objects.create(name="admin")
        self.accountant_role = Role.objects.create(name="accountant")
        self.admin_user = User.objects.create_user(username="admin", password="adminpass")
        self.accountant_user = User.objects.create_user(username="accountant", password="accpass")
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, tenant=self.tenant, role=self.admin_role)
        self.accountant_profile = UserProfile.objects.create(user=self.accountant_user, tenant=self.tenant, role=self.accountant_role)
        self.department = Department.objects.create(name="Science", tenant=self.tenant)

    def test_admin_can_view_departments(self):
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        response = client.get(reverse('education-departments'))
        self.assertEqual(response.status_code, 200)

    def test_accountant_cannot_create_department(self):
        client = APIClient()
        client.force_authenticate(user=self.accountant_user)
        data = {"name": "Math", "tenant": self.tenant.id}
        response = client.post(reverse('education-departments'), data)
        self.assertEqual(response.status_code, 403) 