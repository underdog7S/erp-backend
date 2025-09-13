from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import User
from api.models.plan import Plan
from api.models.user import UserProfile, Role, Tenant
from education.models import FeeStructure, Student, Class

class ERPTestBase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test School", industry="education")
        self.admin_role = Role.objects.create(name="admin")
        self.accountant_role = Role.objects.create(name="accountant")
        self.teacher_role = Role.objects.create(name="teacher")
        self.student_role = Role.objects.create(name="student")
        self.admin_user = User.objects.create_user(username="admin", password="adminpass")
        self.accountant_user = User.objects.create_user(username="accountant", password="accpass")
        self.teacher_user = User.objects.create_user(username="teacher", password="teachpass")
        self.student_user = User.objects.create_user(username="student", password="studpass")
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, tenant=self.tenant, role=self.admin_role)
        self.accountant_profile = UserProfile.objects.create(user=self.accountant_user, tenant=self.tenant, role=self.accountant_role)
        self.teacher_profile = UserProfile.objects.create(user=self.teacher_user, tenant=self.tenant, role=self.teacher_role)
        self.student_profile = UserProfile.objects.create(user=self.student_user, tenant=self.tenant, role=self.student_role)
        self.class1 = Class.objects.create(name="Class 1", tenant=self.tenant)
        self.student1 = Student.objects.create(name="Student 1", tenant=self.tenant, assigned_class=self.class1)
        self.fee_structure = FeeStructure.objects.create(name="Tuition", tenant=self.tenant, amount=1000)

class EducationModuleTests(ERPTestBase):
    def test_admin_can_view_students(self):
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        response = client.get(reverse('student-list'))  # Adjust to your URL name
        self.assertEqual(response.status_code, 200)

    def test_accountant_can_view_fee_structures(self):
        client = APIClient()
        client.force_authenticate(user=self.accountant_user)
        response = client.get(reverse('fee-structure-list'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_cannot_delete_fee_structure(self):
        client = APIClient()
        client.force_authenticate(user=self.teacher_user)
        response = client.delete(reverse('fee-structure-list') + f'{self.fee_structure.id}/')
        self.assertIn(response.status_code, [403, 404])

    def test_student_cannot_view_fee_structures(self):
        client = APIClient()
        client.force_authenticate(user=self.student_user)
        response = client.get(reverse('fee-structure-list'))
        self.assertEqual(response.status_code, 403)
