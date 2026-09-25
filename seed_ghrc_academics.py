"""Second stage of the GHRC demo data: subjects, terms, exams, marks and Term 1 report cards.

    python seed_ghrc_academics.py            # dry run
    python seed_ghrc_academics.py --apply    # write (run seed_ghrc_demo.py --apply first: it adds the students)
    python seed_ghrc_academics.py --remove   # remove the marks and report cards this added
"""
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

import seed_ghrc_demo as base
from api.models.user import Tenant, UserProfile
from education.models import (AcademicYear, Assessment, AssessmentType, Class, MarksEntry, ReportCard, Student, Subject, Term)

TENANT_ID, YEAR_NAME = base.TENANT_ID, base.YEAR_NAME
PRE = ['English', 'Hindi', 'Mathematics', 'Rhymes & Activity']
LOWER = ['English', 'Hindi', 'Marathi', 'Mathematics', 'EVS']
UPPER = ['English', 'Hindi', 'Marathi', 'Mathematics', 'Science', 'Social Studies', 'Computer']
SUBJECTS = {'Nursery': PRE, 'LKG': PRE, 'UKG': PRE, 'std 1': LOWER, 'std 2': LOWER, 'std 3': UPPER[:6], 'std 4': UPPER, 'std 5': UPPER}
GRADES = [(90, 'A+'), (80, 'A'), (70, 'B+'), (60, 'B'), (50, 'C'), (40, 'D'), (0, 'E')]
PRE_CLASSES = ('Nursery', 'LKG', 'UKG')


def grade_for(pct):
    return next(g for cut, g in GRADES if pct >= cut)


def plan_marks(students):
    """{student n: [(subject, 'UT'|'MID', marks, max)]}. Each student has a steady ability plus some noise per subject."""
    rnd = random.Random(7)
    out = {}
    for s in students:
        ability = rnd.uniform(0.52, 0.94)
        rows = []
        for subj in SUBJECTS[s['class']]:
            top = 50 if s['class'] in PRE_CLASSES else 100
            for kind, share in (('UT', 0.25), ('MID', 0.75)):
                mx = Decimal(str(round(top * share, 2)))
                frac = min(1.0, max(0.25, ability + rnd.uniform(-0.12, 0.10)))
                marks = (mx * Decimal(str(round(frac, 3)))).quantize(Decimal('0.5'))
                rows.append((subj, kind, min(marks, mx), mx))
        out[s['n']] = rows
    return out


def show(students, marks):
    print('SUBJECTS per class (100 marks each; pre-primary 50). Term 1 exams: Unit Test (25%) in August, Mid-Term (75%) in September')
    for cname, _, _, _ in base.CLASSES:
        print(f'  {cname:8} {", ".join(SUBJECTS[cname])}')
    print(f'\nMARKS: {sum(len(v) for v in marks.values())} entries for {len(students)} students. Sample (subject total / out of):')
    for s in students[9:12]:
        got = {}
        for subj, kind, m, mx in marks[s['n']]:
            g = got.setdefault(subj, [0, 0])
            g[0] += m
            g[1] += mx
        print(f'  {s["name"]:16} ' + ', '.join(f'{k} {v[0]}/{v[1]}' for k, v in got.items()))
    print('\nREPORT CARDS: one Term 1 card per student with total, percentage, grade, rank in class, attendance and remarks')


@transaction.atomic
def apply(students, marks, attendance):
    tenant = Tenant.objects.get(id=TENANT_ID)
    admin = UserProfile.objects.filter(tenant=tenant, role__name='admin').first()
    year = AcademicYear.objects.get(tenant=tenant, name=YEAR_NAME)
    term1, _ = Term.objects.get_or_create(tenant=tenant, academic_year=year, name='Term 1', defaults={
        'order': 1, 'start_date': date(2026, 4, 1), 'end_date': date(2026, 9, 30), 'is_active': True})
    Term.objects.get_or_create(tenant=tenant, academic_year=year, name='Term 2', defaults={
        'order': 2, 'start_date': date(2026, 10, 1), 'end_date': date(2027, 3, 31), 'is_active': False})
    types = {}
    for code, name, mx, weight, order in (('UT', 'Unit Test', 25, 25, 1), ('MID', 'Mid-Term Exam', 75, 75, 2)):
        types[code], _ = AssessmentType.objects.get_or_create(tenant=tenant, name=name, defaults={
            'code': code, 'max_marks': mx, 'weightage': weight, 'order': order})
    classes = {c.name: c for c in Class.objects.filter(tenant=tenant)}
    assessments = {}
    for cname, _, _, _ in base.CLASSES:
        top = 50 if cname in PRE_CLASSES else 100
        for order, sname in enumerate(SUBJECTS[cname], 1):
            subj, _ = Subject.objects.get_or_create(tenant=tenant, class_obj=classes[cname], name=sname, defaults={
                'code': sname[:3].upper(), 'max_marks': top, 'order': order})
            for kind, share, when, label in (('UT', 0.25, date(2026, 8, 10) + timedelta(days=order - 1), 'Unit Test 1'),
                                             ('MID', 0.75, date(2026, 9, 14) + timedelta(days=order - 1), 'Mid-Term Exam')):
                mx = Decimal(str(round(top * share, 2)))
                assessments[(cname, sname, kind)], _ = Assessment.objects.get_or_create(
                    tenant=tenant, subject=subj, term=term1, assessment_type=types[kind],
                    defaults={'name': f'{sname} {label}', 'date': when, 'max_marks': mx,
                              'passing_marks': (mx * Decimal('0.35')).quantize(Decimal('0.5'))})
    made = {s['n']: Student.objects.get(tenant=tenant, upper_id=s['upper_id']) for s in students}
    for s in students:
        for subj, kind, m, mx in marks[s['n']]:
            MarksEntry.objects.get_or_create(tenant=tenant, student=made[s['n']], assessment=assessments[(s['class'], subj, kind)],
                                             defaults={'marks_obtained': m, 'max_marks': mx, 'entered_by': admin})
    days_total = len({d for _, d, _ in attendance})
    present = {}
    for s, d, p in attendance:
        present[s['n']] = present.get(s['n'], 0) + (1 if p else 0)
    for cname, _, _, _ in base.CLASSES:
        rows = []
        for s in [x for x in students if x['class'] == cname]:
            got = sum(m for _, _, m, _ in marks[s['n']])
            mx = sum(x for _, _, _, x in marks[s['n']])
            rows.append((s, got, mx, (got / mx * 100).quantize(Decimal('0.01'))))
        rows.sort(key=lambda r: -r[3])
        for rank, (s, got, mx, pct) in enumerate(rows, 1):
            days_p = present[s['n']]
            remark = ('Excellent work. Keep it up.' if pct >= 85 else 'Good progress; can do even better.' if pct >= 70
                      else 'Satisfactory. Needs regular practice at home.' if pct >= 55 else 'Needs extra attention and support.')
            ReportCard.objects.get_or_create(tenant=tenant, student=made[s['n']], academic_year=year, term=term1, defaults={
                'class_obj': classes[cname], 'total_marks': got, 'max_total_marks': mx, 'percentage': pct, 'grade': grade_for(pct),
                'rank_in_class': rank, 'days_present': days_p, 'days_absent': days_total - days_p,
                'attendance_percentage': (Decimal(days_p) / days_total * 100).quantize(Decimal('0.01')),
                'teacher_remarks': remark, 'principal_remarks': 'Promoted with good wishes.' if pct >= 40 else 'Extra coaching advised.',
                'conduct_grade': 'A' if pct >= 60 else 'B', 'issued_date': date(2026, 9, 26)})
    print('Academics applied.')


@transaction.atomic
def remove():
    demo = Student.objects.filter(tenant_id=TENANT_ID, upper_id__startswith='GHRC26-', email__endswith=base.DEMO_DOMAIN)
    print('report cards removed:', ReportCard.objects.filter(tenant_id=TENANT_ID, student__in=demo).delete()[0])
    print('marks removed:', MarksEntry.objects.filter(tenant_id=TENANT_ID, student__in=demo).delete()[0])
    print('Subjects, terms and exams were left in place.')


if __name__ == '__main__':
    if '--remove' in sys.argv:
        remove()
    else:
        students, payments, days, attendance = base.build_plan()
        marks = plan_marks(students)
        show(students, marks)
        if '--apply' in sys.argv:
            apply(students, marks, attendance)
        else:
            print('\nDry run only. Nothing was written.')
