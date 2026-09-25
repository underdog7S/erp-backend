"""Online school-fee payments.

A fee payment is only recorded once Razorpay has confirmed the money, so an abandoned or failed checkout can never make a fee
look paid. Two paths lead here (the parent's browser after checkout, and Razorpay's webhook); whichever arrives first records the
payment and the other finds it already recorded.
"""
import hashlib
import hmac
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


def verify_checkout_signature(key_secret, order_id, payment_id, signature):
    expected = hmac.new(key_secret.encode(), f'{order_id}|{payment_id}'.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or '')


@transaction.atomic
def record_public_fee_payment(tenant, notes, payment_id, order_id, paid_paise):
    """Create the FeePayment for a captured payment. Returns (fee_payment, created)."""
    from api.models.payments import PaymentTransaction
    from education.models import FeePayment, FeeStructure, Student

    existing = PaymentTransaction.objects.filter(payment_id=payment_id).first()
    if existing:
        return FeePayment.objects.filter(pk=existing.reference_id, tenant=tenant).first(), False

    student = Student.objects.filter(pk=notes.get('student_id'), tenant=tenant).first()
    structure = FeeStructure.objects.filter(pk=notes.get('fee_structure_id'), tenant=tenant).first()
    if not student or not structure:
        raise ValueError('The student or fee in this payment no longer exists.')
    amount = (Decimal(paid_paise) / 100).quantize(Decimal('0.01'))
    if amount <= 0:
        raise ValueError('The payment amount is not valid.')

    payment = FeePayment.objects.create(
        tenant=tenant, student=student, fee_structure=structure, amount_paid=amount, payment_method='RAZORPAY',
        payment_date=timezone.now().date(), academic_year=structure.academic_year,
        notes=f"Online payment {payment_id} by {notes.get('parent_name') or 'parent'}")
    PaymentTransaction.objects.create(
        tenant=tenant, user=None, order_id=order_id or '', payment_id=payment_id, signature='', amount=amount, currency='INR',
        status='verified', sector='education', reference_id=str(payment.id),
        description=f'Online fee payment: {student.name}', verified_at=timezone.now())
    from api.notify import notify
    notify(tenant, f'Online fee received: {student.name}', f'{amount} received for {structure.get_fee_type_display()} (receipt {payment.receipt_number}).',
           roles=('admin', 'principal', 'accountant'), module='education', kind='success', path='/education?tab=fees', ref=('fee_payment', payment.id))
    total_paid = FeePayment.objects.filter(tenant=tenant, student=student, fee_structure=structure).aggregate(t=Sum('amount_paid'))['t'] or 0
    if total_paid > structure.amount:
        logger.warning('Fee over-paid online: student %s fee %s paid %s of %s', student.id, structure.id, total_paid, structure.amount)
    return payment, True
