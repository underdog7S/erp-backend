"""Adds a realistic set of demo records to the GHRC school (tenant 28).

    python seed_ghrc_demo.py            # dry run: prints the tables, changes nothing
    python seed_ghrc_demo.py --apply    # writes everything in one transaction
    python seed_ghrc_demo.py --remove   # removes only what this script added

Everything added is recognisable: students have upper_id GHRC26-NN and an email ending @demo.ghrc.example,
so --remove can take it out again without touching real records.
"""
import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.db import transaction  # noqa: E402

from api.models.user import Tenant, UserProfile  # noqa: E402
from education.models import AcademicYear, Attendance, Class, FeePayment, FeeStructure, Student  # noqa: E402

TENANT_ID = 28
YEAR_NAME = '2026-27'
DEMO_DOMAIN = '@demo.ghrc.example'

# (class name, order, tuition, age in years)
CLASSES = [('Nursery', 1, 9000, 3), ('LKG', 2, 9500, 4), ('UKG', 3, 10000, 5), ('std 1', 4, 12000, 6),
           ('std 2', 5, 12500, 7), ('std 3', 6, 13000, 8), ('std 4', 7, 14000, 9), ('std 5', 8, 15000, 10)]
EXAM_FEE, TRANSPORT_FEE = 1200, 6000

# Three students per class: (name, gender, father, mother, locality)
PEOPLE = {
    'Nursery': [('Aarav Deshmukh', 'Male', 'Rahul Deshmukh', 'Sneha Deshmukh', 'Dharampeth'),
                ('Anaya Kulkarni', 'Female', 'Amit Kulkarni', 'Pooja Kulkarni', 'Sadar'),
                ('Vihaan Wankhede', 'Male', 'Sanjay Wankhede', 'Rekha Wankhede', 'Manish Nagar')],
    'LKG': [('Diya Meshram', 'Female', 'Prakash Meshram', 'Anita Meshram', 'Khamla'),
            ('Reyansh Bhoyar', 'Male', 'Nilesh Bhoyar', 'Kavita Bhoyar', 'Bajaj Nagar'),
            ('Ira Thakre', 'Female', 'Vivek Thakre', 'Madhuri Thakre', 'Pratap Nagar')],
    'UKG': [('Kabir Sheikh', 'Male', 'Imran Sheikh', 'Farah Sheikh', 'Mominpura'),
            ('Myra Gawande', 'Female', 'Ashok Gawande', 'Sunita Gawande', 'Trimurti Nagar'),
            ('Advait Raut', 'Male', 'Mahesh Raut', 'Swati Raut', 'Wardha Road')],
    'std 1': [('Saanvi Ingole', 'Female', 'Dinesh Ingole', 'Jyoti Ingole', 'Hingna'),
              ('Arjun Patil', 'Male', 'Ganesh Patil', 'Shweta Patil', 'Sitabuldi'),
              ('Ishita Charde', 'Female', 'Yogesh Charde', 'Namrata Charde', 'Ramdaspeth')],
    'std 2': [('Yash Dhoke', 'Male', 'Rajesh Dhoke', 'Vaishali Dhoke', 'Laxmi Nagar'),
              ('Prisha Nimje', 'Female', 'Sachin Nimje', 'Archana Nimje', 'Godhni'),
              ('Rudra Bagde', 'Male', 'Anil Bagde', 'Seema Bagde', 'Narendra Nagar')],
    'std 3': [('Aditi Sonwane', 'Female', 'Pravin Sonwane', 'Mamta Sonwane', 'Besa'),
              ('Shaurya Khobragade', 'Male', 'Deepak Khobragade', 'Rupali Khobragade', 'Kamptee Road'),
              ('Navya Lokhande', 'Female', 'Suresh Lokhande', 'Priya Lokhande', 'Jaripatka')],
    'std 4': [('Atharv Bhagat', 'Male', 'Vinod Bhagat', 'Sarika Bhagat', 'Nandanvan'),
              ('Tanvi Wagh', 'Female', 'Milind Wagh', 'Shilpa Wagh', 'Mankapur'),
              ('Om Dongre', 'Male', 'Ramesh Dongre', 'Alka Dongre', 'Koradi Road')],
    'std 5': [('Riya Motghare', 'Female', 'Nitin Motghare', 'Bhagyashree Motghare', 'Ajni'),
              ('Samarth Pise', 'Male', 'Chetan Pise', 'Komal Pise', 'Telangkhedi'),
              ('Kiara Waghmare', 'Female', 'Amol Waghmare', 'Pallavi Waghmare', 'Wadi')],
}
METHODS = ['CASH', 'UPI', 'ONLINE', 'CARD', 'CHEQUE']


def build_plan():
    rnd = random.Random(2026)
    today = date.today()
    students = []
    n = 0
    for cname, _, tuition, age in CLASSES:
        for name, gender, father, mother, area in PEOPLE[cname]:
            n += 1
            first = name.split()[0].lower()
            students.append({
                'n': n, 'class': cname, 'name': name, 'gender': gender, 'father': father, 'mother': mother, 'area': area,
                'upper_id': f'GHRC26-{n:02d}', 'email': f'{first}.{n:02d}{DEMO_DOMAIN}', 'phone': f'90000{n:05d}',
                'dob': date(2026 - age, rnd.randint(1, 12), rnd.randint(1, 28)),
                'admitted': date(2026 - (age - 3 if age > 3 else 0), 6, rnd.randint(3, 20)) if age > 3 else date(2026, 4, rnd.randint(4, 12)),
                'tuition': tuition,
            })
    # payments: pattern by position so the school sees paid, part paid and unpaid families
    payments = []
    for i, s in enumerate(students):
        pattern = i % 4  # 0 fully paid, 1 half, 2 a third, 3 nothing yet
        base = date(2026, 6, 12) + timedelta(days=rnd.randint(0, 40))
        if pattern == 0:
            payments.append((s, 'TUITION', Decimal(s['tuition']), base, METHODS[i % 5]))
        elif pattern == 1:
            payments.append((s, 'TUITION', Decimal(s['tuition'] // 2), base, METHODS[(i + 1) % 5]))
        elif pattern == 2:
            payments.append((s, 'TUITION', Decimal(s['tuition'] // 3), base + timedelta(days=20), METHODS[(i + 2) % 5]))
        if i % 2 == 0:
            payments.append((s, 'EXAM', Decimal(EXAM_FEE), date(2026, 9, 1) + timedelta(days=rnd.randint(0, 6)), METHODS[(i + 3) % 5]))
    # attendance: every school day (Mon-Sat) from 24 Aug to yesterday
    days = [d for d in (date(2026, 8, 24) + timedelta(days=k) for k in range((today - timedelta(days=1) - date(2026, 8, 24)).days + 1)) if d.weekday() != 6]
    absent_rate = {s['n']: (0.22 if s['n'] in (5, 14, 21) else 0.07) for s in students}
    attendance = [(s, d, rnd.random() > absent_rate[s['n']]) for s in students for d in days]
    return students, payments, days, attendance


def show(students, payments, days, attendance):
    print('CLASSES (existing "std 1" kept; new classes added; order and next class set)')
    print(f'  {"class":8} {"tuition":>8} {"exam":>6} {"transport":>10}')
    for cname, _, tuition, _ in CLASSES:
        print(f'  {cname:8} {tuition:>8} {EXAM_FEE:>6} {TRANSPORT_FEE:>10}')
    print(f'\nSTUDENTS ({len(students)})')
    print(f'  {"id":10} {"name":20} {"class":8} {"gender":7} {"born":11} {"admitted":11} {"parent phone":12} area')
    for s in students:
        print(f'  {s["upper_id"]:10} {s["name"]:20} {s["class"]:8} {s["gender"]:7} {s["dob"]!s:11} {s["admitted"]!s:11} {s["phone"]:12} {s["area"]}')
    total = sum(p[2] for p in payments)
    print(f'\nFEE PAYMENTS ({len(payments)}, total Rs {total:,.0f}, dated Jun-Sep 2026)')
    by = {}
    for s, kind, amt, when, method in payments:
        by.setdefault(s['name'], []).append(f'{kind} {amt:,.0f} on {when:%d %b} ({method})')
    for name, rows in list(by.items())[:8]:
        print(f'  {name:20} ' + '; '.join(rows))
    print('  ...')
    present = sum(1 for a in attendance if a[2])
    print(f'\nATTENDANCE: {len(days)} school days ({days[0]:%d %b} to {days[-1]:%d %b}) x {len(students)} students = {len(attendance)} rows, '
          f'{present} present ({100 * present / len(attendance):.1f}%)')


@transaction.atomic
def apply(students, payments, attendance):
    tenant = Tenant.objects.get(id=TENANT_ID)
    admin = UserProfile.objects.filter(tenant=tenant, role__name='admin').first()
    year, _ = AcademicYear.objects.get_or_create(tenant=tenant, name=YEAR_NAME, defaults={
        'start_date': date(2026, 4, 1), 'end_date': date(2027, 3, 31), 'is_current': True})
    classes = {}
    for cname, order, tuition, _ in CLASSES:
        c, _ = Class.objects.get_or_create(tenant=tenant, name=cname, defaults={'order': order})
        if c.order != order:
            c.order = order
            c.save(update_fields=['order'])
        classes[cname] = c
    names = [c[0] for c in CLASSES]
    for a, b in zip(names, names[1:]):
        classes[a].next_class = classes[b]
        classes[a].save(update_fields=['next_class'])
    structures = {}
    for cname, _, tuition, _ in CLASSES:
        for kind, amount, due, optional in (('TUITION', tuition, date(2026, 7, 10), False), ('EXAM', EXAM_FEE, date(2026, 9, 15), False),
                                            ('TRANSPORT', TRANSPORT_FEE, date(2026, 7, 10), True)):
            fs, _ = FeeStructure.objects.get_or_create(
                tenant=tenant, class_obj=classes[cname], fee_type=kind, academic_year=YEAR_NAME,
                defaults={'amount': amount, 'due_date': due, 'is_optional': optional, 'description': f'{kind.title()} fee {YEAR_NAME}'})
            structures[(cname, kind)] = fs
    made = {}
    for s in students:
        st, _ = Student.objects.get_or_create(tenant=tenant, upper_id=s['upper_id'], defaults={
            'name': s['name'], 'email': s['email'], 'admission_date': s['admitted'], 'assigned_class': classes[s['class']],
            'phone': s['phone'], 'address': f"{s['area']}, Nagpur", 'date_of_birth': s['dob'], 'gender': s['gender'],
            'cast': 'General', 'parent_name': s['father'], 'parent_phone': s['phone'], 'father_name': s['father'],
            'mother_name': s['mother'], 'is_active': True})
        made[s['n']] = st
    for s, kind, amount, when, method in payments:
        FeePayment.objects.create(
            tenant=tenant, student=made[s['n']], fee_structure=structures[(s['class'], kind)], amount_paid=amount,
            payment_date=when, payment_method=method, collected_by=admin, academic_year=YEAR_NAME,
            notes='Demo data (seed_ghrc_demo.py)')
    existing = set(Attendance.objects.filter(tenant=tenant, student__in=list(made.values())).values_list('student_id', 'date'))
    Attendance.objects.bulk_create([
        Attendance(tenant=tenant, student=made[s['n']], date=d, present=p)
        for s, d, p in attendance if (made[s['n']].id, d) not in existing])
    print('Applied.')


@transaction.atomic
def remove():
    demo = Student.objects.filter(tenant_id=TENANT_ID, upper_id__startswith='GHRC26-', email__endswith=DEMO_DOMAIN)
    print('payments removed:', FeePayment.objects.filter(tenant_id=TENANT_ID, student__in=demo).delete()[0])
    print('attendance removed:', Attendance.objects.filter(tenant_id=TENANT_ID, student__in=demo).delete()[0])
    print('students removed:', demo.delete()[0])
    print('Classes, fee structures and the 2026-27 year were left in place (they are useful on their own).')


if __name__ == '__main__':
    if '--remove' in sys.argv:
        remove()
    else:
        plan = build_plan()
        show(*plan)
        if '--apply' in sys.argv:
            apply(plan[0], plan[1], plan[3])
        else:
            print('\nDry run only. Nothing was written.')
