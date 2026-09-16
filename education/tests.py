from django.test import TestCase
from education.models import FeePayment, Student, Class, AcademicYear
from api.models.user import Tenant

class FeePaymentTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="EduTest", industry="education")
        self.academic_year = AcademicYear.objects.create(tenant=self.tenant, name="2026-2027", start_date="2026-06-01", end_date="2027-05-31")
        self.test_class = Class.objects.create(tenant=self.tenant, name="Grade 10")
        self.student = Student.objects.create(tenant=self.tenant, first_name="John", last_name="Doe", enrollment_number="E123", class_enrolled=self.test_class)
        
    def test_fee_payment_auto_generates_receipt_number(self):
        # Create a payment WITHOUT a receipt number
        payment = FeePayment.objects.create(
            tenant=self.tenant,
            student=self.student,
            amount_paid=500.00,
            payment_date="2026-06-15",
            payment_method="cash",
            status="completed"
        )
        
        # Verify the save() method override correctly populated receipt_number
        self.assertIsNotNone(payment.receipt_number)
        self.assertTrue(payment.receipt_number.startswith("RCPT-"))
