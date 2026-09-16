import os
import sys
import django
from datetime import date, timedelta
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import UserProfile, Tenant, Role
from education.models import (
    Class, Student, Department, FeePayment, FeeStructure, Attendance, 
    ReportCard, StaffAttendance, AcademicYear, Term, Subject, Exam
)
from django.contrib.auth.models import User
from django.utils import timezone

def populate_data():
    print("=== Populating Extensive Education Data ===")
    
    # Get shadab1's tenant
    try:
        tenant = UserProfile.objects.get(user__username='shadab1').tenant
        print(f"✅ Using tenant: {tenant.name} (ID: {tenant.id})")
    except Exception as e:
        print(f"❌ Could not find tenant for shadab1: {e}")
        return

    # 1. Academic Year & Term
    ay, _ = AcademicYear.objects.get_or_create(
        tenant=tenant,
        name="2026-2027",
        defaults={
            "start_date": date(2026, 4, 1),
            "end_date": date(2027, 3, 31),
            "is_current": True
        }
    )
    
    term1, _ = Term.objects.get_or_create(
        tenant=tenant,
        academic_year=ay,
        name="First Term",
        defaults={
            "order": 1,
            "start_date": date(2026, 4, 1),
            "end_date": date(2026, 9, 30),
            "is_active": True
        }
    )

    # 2. Departments & Subjects
    depts = ['Sciences', 'Humanities', 'Commerce', 'Languages']
    created_depts = []
    for d in depts:
        obj, _ = Department.objects.get_or_create(name=d, tenant=tenant)
        created_depts.append(obj)
        
    # 3. Classes & Subjects
    class_names = ['Grade 9A', 'Grade 9B', 'Grade 10A', 'Grade 10B', 'Grade 11 Science', 'Grade 11 Commerce']
    created_classes = []
    created_subjects = []
    for c in class_names:
        cls_obj, _ = Class.objects.get_or_create(
            name=c, 
            tenant=tenant, 
            defaults={'schedule': 'Mon-Fri 8AM-3PM'}
        )
        created_classes.append(cls_obj)
        
        # Create subjects for this class
        subjects = ['Mathematics', 'Physics', 'Chemistry', 'English', 'History', 'Economics']
        for s in subjects:
            subj_obj, _ = Subject.objects.get_or_create(
                name=s, 
                tenant=tenant, 
                class_obj=cls_obj,
                defaults={'code': s[:3].upper()}
            )
            created_subjects.append(subj_obj)

    # 4. Staff Members
    roles = ['teacher', 'librarian', 'accountant']
    created_staff = []
    for i in range(15):
        username = f"staff_{tenant.id}_{i}"
        user, _ = User.objects.get_or_create(username=username, defaults={'first_name': f"Staff{i}", 'email': f"{username}@example.com"})
        user.set_password('pass123')
        user.save()
        
        role_obj, _ = Role.objects.get_or_create(name=random.choice(roles))
        profile, _ = UserProfile.objects.get_or_create(
            user=user, 
            tenant=tenant, 
            defaults={'role': role_obj, 'department': None}
        )
        created_staff.append(profile)

    # 5. Students
    first_names = ['John', 'Emma', 'Oliver', 'Ava', 'William', 'Sophia', 'James', 'Isabella', 'Benjamin', 'Mia']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    created_students = []
    for i in range(100):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        cls = random.choice(created_classes)
        
        from django.db import IntegrityError
        try:
            student, _ = Student.objects.get_or_create(
                email=f"{fname.lower()}.{lname.lower()}{i}@example.com",
                tenant=tenant,
                defaults={
                    'name': f"{fname} {lname}",
                    'admission_date': date(2026, 4, 1),
                    'assigned_class': cls
                }
            )
            created_students.append(student)
        except IntegrityError:
            continue

    # 6. Fees
    fee_structures = []
    for cls in created_classes:
        fs, _ = FeeStructure.objects.get_or_create(
            class_obj=cls,
            tenant=tenant,
            defaults={
                'amount': random.randint(20000, 50000),
                'due_date': date(2026, 5, 1)
            }
        )
        fee_structures.append(fs)
        
    for student in created_students:
        if random.random() > 0.3: # 70% paid
            fs = student.assigned_class.fee_structures.first()
            if fs:
                try:
                    payment, _ = FeePayment.objects.get_or_create(
                        student=student,
                        fee_structure=fs,
                        tenant=tenant,
                        defaults={
                            'amount_paid': fs.amount,
                            'payment_method': random.choice(['CASH', 'CARD', 'UPI'])
                        }
                    )
                    FeePayment.objects.filter(id=payment.id).update(payment_date=date(2026, 4, random.randint(1, 28)))
                except IntegrityError:
                    pass

    # 7. Historical Attendance (Last 30 days)
    today = timezone.now().date()
    for days_ago in range(30):
        d = today - timedelta(days=days_ago)
        if d.weekday() >= 5: continue # Skip weekends
        
        # Staff Attendance
        for staff in created_staff:
            try:
                StaffAttendance.objects.get_or_create(
                    staff=staff,
                    tenant=tenant,
                    date=d,
                    defaults={
                        'status': 'PRESENT' if random.random() > 0.1 else 'ABSENT',
                        'check_in_time': timezone.now().replace(hour=8, minute=random.randint(0, 30))
                    }
                )
            except: pass
            
        # Student Attendance
        for student in created_students:
            try:
                Attendance.objects.get_or_create(
                    student=student,
                    class_obj=student.assigned_class,
                    tenant=tenant,
                    date=d,
                    defaults={'present': random.random() > 0.05} # 95% attendance
                )
            except: pass

    # 8. Report Cards & Exams
    exam, _ = Exam.objects.get_or_create(
        tenant=tenant,
        name="Mid Term Examination",
        academic_year=ay,
        term=term1,
        defaults={'start_date': date(2026, 9, 1), 'end_date': date(2026, 9, 15)}
    )

    for student in created_students:
        grades_json = {s.name: random.choice(['A', 'B', 'C', 'A+']) for s in created_subjects}
        rc, created = ReportCard.objects.get_or_create(
            student=student,
            tenant=tenant,
            academic_year=ay,
            term=term1,
            class_obj=student.assigned_class,
            defaults={
                'total_marks': random.randint(300, 500),
                'max_total_marks': 500,
                'percentage': random.uniform(60.0, 99.0),
                'grade': random.choice(['A', 'B', 'C', 'A+']),
                'remarks': 'Good progress.',
                'grades': grades_json
            }
        )
    
    print(f"✅ Successfully created 100 students, 15 staff members, 30 days of attendance, fees, and report cards!")

if __name__ == '__main__':
    populate_data()
