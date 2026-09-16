#!/usr/bin/env python
import os
import sys
import django
from django.utils import timezone
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import UserProfile, Tenant, Role
from education.models import Class, Student, Department, FeePayment, FeeStructure, Attendance, ReportCard, StaffAttendance
from django.contrib.auth.models import User

def create_sample_education_data():
    print("=== Creating Sample Education Data ===")
    
    # Get education tenant
    try:
        tenant = UserProfile.objects.get(user__username='shadab1').tenant
        if not tenant:
            print("❌ No education tenant found. Please create an education tenant first.")
            return
        
        print(f"✅ Using tenant: {tenant.name}")
        
        # Create departments
        departments = [
            'Computer Science',
            'Mathematics', 
            'Physics',
            'Chemistry'
        ]
        
        print("🏢 Creating departments...")
        created_departments = []
        for dept_name in departments:
            department, created = Department.objects.get_or_create(
                name=dept_name,
                tenant=tenant
            )
            if created:
                print(f"✅ Created department: {department.name}")
            else:
                print(f"ℹ️  Already exists: {department.name}")
            created_departments.append(department)
        
        # Create classes
        classes = [
            {
                'name': 'Class 10A',
                'schedule': 'Monday to Friday, 8:00 AM - 2:00 PM'
            },
            {
                'name': 'Class 10B',
                'schedule': 'Monday to Friday, 8:00 AM - 2:00 PM'
            },
            {
                'name': 'Class 11A',
                'schedule': 'Monday to Friday, 8:00 AM - 2:00 PM'
            },
            {
                'name': 'Class 11B',
                'schedule': 'Monday to Friday, 8:00 AM - 2:00 PM'
            }
        ]
        
        print("📚 Creating classes...")
        created_classes = []
        for class_data in classes:
            class_obj, created = Class.objects.get_or_create(
                name=class_data['name'],
                tenant=tenant,
                defaults=class_data
            )
            if created:
                print(f"✅ Created class: {class_obj.name}")
            else:
                print(f"ℹ️  Already exists: {class_obj.name}")
            created_classes.append(class_obj)
        
        # Create students
        students = [
            {
                'name': 'Alice Johnson',
                'email': 'alice.johnson@school.com',
                'admission_date': date(2024, 6, 1)
            },
            {
                'name': 'Bob Smith',
                'email': 'bob.smith@school.com',
                'admission_date': date(2024, 6, 1)
            },
            {
                'name': 'Carol Davis',
                'email': 'carol.davis@school.com',
                'admission_date': date(2024, 6, 1)
            },
            {
                'name': 'David Wilson',
                'email': 'david.wilson@school.com',
                'admission_date': date(2024, 6, 1)
            },
            {
                'name': 'Eva Brown',
                'email': 'eva.brown@school.com',
                'admission_date': date(2024, 6, 1)
            }
        ]
        
        print("👥 Creating students...")
        created_students = []
        for i, student_data in enumerate(students):
            student, created = Student.objects.get_or_create(
                email=student_data['email'],
                tenant=tenant,
                defaults=student_data
            )
            if created:
                print(f"✅ Created student: {student.name}")
            else:
                print(f"ℹ️  Already exists: {student.name}")
            created_students.append(student)
        
        # Create fee structures
        print("💰 Creating fee structures...")
        for class_obj in created_classes:
            fee_structure = FeeStructure.objects.create(
                tenant=tenant,
                class_obj=class_obj,
                fee_type='TUITION',
                amount=5000 + (class_obj.id * 500),  # Different amounts
                description=f'Tuition fee for {class_obj.name}',
                due_date=timezone.now().date() + timedelta(days=30),
                academic_year='2024-25'
            )
            print(f"✅ Created fee structure: {class_obj.name} - ₹{fee_structure.amount}")
        
        # Create fee payments
        print("💰 Creating fee payments...")
        for i, student in enumerate(created_students):
            if student.assigned_class:
                fee_structure = FeeStructure.objects.filter(class_obj=student.assigned_class).first()
                if fee_structure:
                    payment_amount = fee_structure.amount * 0.8 if i < 3 else fee_structure.amount  # Some partial payments
                    fee_payment = FeePayment.objects.create(
                        student=student,
                        tenant=tenant,
                        fee_structure=fee_structure,
                        amount_paid=payment_amount,
                        payment_method='CASH',
                        receipt_number=f'RCPT{i+1:03d}',
                        notes=f'Payment for {student.name}'
                    )
                    print(f"✅ Created fee payment: {student.name} - ₹{payment_amount}")
        
        # Create attendance records
        print("📊 Creating attendance records...")
        today = timezone.now().date()
        
        # Student attendance
        for student in created_students:
            present = student.id % 2 == 0  # Alternate present/absent
            attendance = Attendance.objects.create(
                student=student,
                tenant=tenant,
                date=today,
                present=present
            )
            status = 'PRESENT' if present else 'ABSENT'
            print(f"✅ Created student attendance: {student.name} - {status}")
        
        # Staff attendance (using UserProfile)
        staff_users = UserProfile.objects.filter(tenant=tenant, role__name__in=['teacher', 'principal', 'staff'])
        for staff_user in staff_users:
            present = staff_user.id % 2 == 0  # Alternate present/absent
            staff_attendance = StaffAttendance.objects.create(
                staff=staff_user,
                tenant=tenant,
                date=today,
                check_in_time=timezone.now() if present else None
            )
            status = 'PRESENT' if present else 'ABSENT'
            print(f"✅ Created staff attendance: {staff_user.user.username} - {status}")
        
        # Create report cards
        print("📋 Creating report cards...")
        for student in created_students:
            grades = {
                'Mathematics': 'A' if student.id % 2 == 0 else 'B',
                'Science': 'A' if student.id % 2 == 0 else 'B',
                'English': 'A' if student.id % 2 == 0 else 'B',
                'History': 'A' if student.id % 2 == 0 else 'B'
            }
            report_card = ReportCard.objects.create(
                student=student,
                tenant=tenant,
                term='First Term',
                grades=str(grades)
            )
            print(f"✅ Created report card: {student.name} - Grades: {grades}")
        
        print("\n=== Sample Education Data Summary ===")
        print(f"🏢 Departments: {Department.objects.filter(tenant=tenant).count()}")
        print(f"📚 Classes: {Class.objects.filter(tenant=tenant).count()}")
        print(f"👥 Students: {Student.objects.filter(tenant=tenant).count()}")
        print(f"💰 Fee Structures: {FeeStructure.objects.filter(tenant=tenant).count()}")
        print(f"💰 Fee Payments: {FeePayment.objects.filter(tenant=tenant).count()}")
        print(f"📊 Attendance Records: {Attendance.objects.filter(tenant=tenant).count()}")
        print(f"📊 Staff Attendance Records: {StaffAttendance.objects.filter(tenant=tenant).count()}")
        print(f"📋 Report Cards: {ReportCard.objects.filter(tenant=tenant).count()}")
        
        print("\n✅ Sample education data created successfully!")
        print("🎯 You can now refresh the Education Dashboard to see the data.")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_sample_education_data() 