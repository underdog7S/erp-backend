"""Daily digest notifications. Schedule once a day (Render cron: `python manage.py run_daily_notifications`).

Each digest is one notification per tenant per day, so re-running the command never duplicates it.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.utils import timezone

from api.models.user import Tenant
from api.notify import notify


def pharmacy_expiry(tenant, today):
    from pharmacy.models import MedicineBatch
    batches = MedicineBatch.objects.filter(tenant=tenant, quantity_available__gt=0).select_related('medicine')
    expired = sum(1 for b in batches if b.expiry_date < today)
    soon = sum(1 for b in batches if today <= b.expiry_date <= today + timedelta(days=b.medicine.expiry_alert_days))
    if expired or soon:
        notify(tenant, 'Medicine expiry check', f'{expired} batch(es) expired and still in stock, {soon} expiring soon.',
               module='pharmacy', kind='warning', path='/pharmacy?tab=expiry', ref=('expiry_digest', int(today.strftime('%Y%m%d'))), dedupe_days=1)
        return 1
    return 0


def overdue_fees(tenant, today):
    from education.models import FeePayment, FeeStructure, Student
    overdue_students = set()
    for fs in FeeStructure.objects.filter(tenant=tenant, due_date__lt=today, is_optional=False).select_related('class_obj'):
        paid = dict(FeePayment.objects.filter(tenant=tenant, fee_structure=fs).values_list('student_id').annotate(t=Sum('amount_paid')))
        for sid in Student.objects.filter(tenant=tenant, assigned_class=fs.class_obj, is_active=True).values_list('id', flat=True):
            if (paid.get(sid) or 0) < fs.amount:
                overdue_students.add(sid)
    if overdue_students:
        notify(tenant, 'Fees overdue', f'{len(overdue_students)} student(s) have a fee past its due date.', roles=('admin', 'principal', 'accountant'),
               module='education', kind='warning', path='/education?tab=fees', ref=('overdue_digest', int(today.strftime('%Y%m%d'))), dedupe_days=1)
        return 1
    return 0


def tomorrow(tenant, today):
    day = today + timedelta(days=1)
    sent = 0
    from salon.models import Appointment
    n = Appointment.objects.filter(tenant=tenant, status='scheduled', start_time__date=day).count()
    if n:
        notify(tenant, 'Appointments tomorrow', f'{n} appointment(s) are booked for tomorrow.', module='salon', path='/salon?tab=appointments',
               ref=('salon_tomorrow', int(day.strftime('%Y%m%d'))), dedupe_days=1)
        sent += 1
    from hotel.models import Booking
    n = Booking.objects.filter(tenant=tenant, status='reserved', check_in__date=day).count()
    if n:
        notify(tenant, 'Check-ins tomorrow', f'{n} guest(s) arrive tomorrow.', module='hotel', path='/hotel?tab=reservations',
               ref=('hotel_tomorrow', int(day.strftime('%Y%m%d'))), dedupe_days=1)
        sent += 1
    return sent


class Command(BaseCommand):
    help = 'Send the daily digest notifications (medicine expiry, overdue fees, tomorrow\'s appointments and check-ins).'

    def handle(self, *args, **options):
        today = timezone.localdate()
        total = 0
        for tenant in Tenant.objects.all():
            for job in (pharmacy_expiry, overdue_fees, tomorrow):
                try:
                    total += job(tenant, today)
                except Exception as exc:  # one tenant's bad data must not stop the rest
                    self.stderr.write(f'{job.__name__} failed for {tenant.name}: {exc}')
        self.stdout.write(f'Daily notifications sent: {total}')
