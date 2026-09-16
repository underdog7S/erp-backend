import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.test import RequestFactory
from api.views.education_views import ReportCardPDFView, FeePaymentReceiptPDFView
from django.contrib.auth import get_user_model
from education.models import ReportCard, FeePayment

User = get_user_model()
user = User.objects.get(username='shadab1')

from rest_framework.test import APIRequestFactory, force_authenticate
rf = APIRequestFactory()

# Test Report Card PDF
rc = ReportCard.objects.filter(tenant=user.userprofile.tenant).first()
if rc:
    print(f"Testing ReportCardPDFView with ID {rc.id}")
    request = rf.get(f'/education/reportcards/{rc.id}/pdf/')
    force_authenticate(request, user=user)
    view = ReportCardPDFView.as_view()
    try:
        response = view(request, pk=rc.id)
        print(f"ReportCardPDFView -> Status: {response.status_code}")
        if response.status_code == 500:
            print(response.data)
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("No ReportCard found.")

# Test Fee Payment Receipt PDF
fp = FeePayment.objects.filter(tenant=user.userprofile.tenant).first()
if not fp:
    from education.models import Student, FeeStructure
    student = Student.objects.filter(tenant=user.userprofile.tenant).first()
    fs = FeeStructure.objects.filter(tenant=user.userprofile.tenant).first()
    if student and fs:
        fp = FeePayment.objects.create(
            tenant=user.userprofile.tenant,
            student=student,
            fee_structure=fs,
            amount_paid=1000.00,
            payment_method='CASH'
        )

if fp:
    print(f"Testing FeePaymentReceiptPDFView with ID {fp.id}")
    request = rf.get(f'/education/fee-payments/{fp.id}/receipt/')
    force_authenticate(request, user=user)
    view = FeePaymentReceiptPDFView.as_view()
    try:
        response = view(request, pk=fp.id)
        print(f"FeePaymentReceiptPDFView -> Status: {response.status_code}")
        if response.status_code == 500:
            print(response.data)
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("Could not create mock FeePayment. Missing student or fee structure.")
