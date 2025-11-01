from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import random

from api.models.user import Tenant, UserProfile, Role
from education.models import (
    Class, Student, FeeStructure, FeePayment, FeeInstallmentPlan, FeeInstallment,
    Attendance, AcademicYear, Term, Subject, Unit, AssessmentType, Assessment, MarksEntry,
    ReportCard, StaffAttendance, Department
)


class Command(BaseCommand):
    help = 'Create comprehensive demo data for education module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='Nahid12',
            help='Username to add demo data for (default: Nahid12)'
        )
        parser.add_argument(
            '--create-demo-user',
            action='store_true',
            help='Create a new demo user account instead of using existing'
        )

    def handle(self, *args, **options):
        username = options.get('username', 'Nahid12')
        create_demo = options.get('create_demo_user', False)

        # Get or create user
        if create_demo:
            # Create new demo user
            demo_user, created = User.objects.get_or_create(
                username='demo_education',
                defaults={
                    'email': 'demo@zenitherp.online',
                    'first_name': 'Demo',
                    'last_name': 'Education User',
                }
            )
            if created:
                demo_user.set_password('Demo123456!')
                demo_user.save()
                self.stdout.write(self.style.SUCCESS(f'✅ Created demo user: demo_education / Demo123456!'))
            else:
                demo_user.set_password('Demo123456!')
                demo_user.save()
                self.stdout.write(self.style.SUCCESS(f'✅ Using existing demo user: demo_education / Demo123456!'))
            
            user = demo_user
            username = 'demo_education'
        else:
            try:
                user = User.objects.get(username=username)
                self.stdout.write(self.style.SUCCESS(f'✅ Found user: {username}'))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ User "{username}" not found. Use --create-demo-user to create one.'))
                return

        # Get or create user profile and tenant
        try:
            profile = UserProfile._default_manager.get(user=user)
            tenant = profile.tenant
            self.stdout.write(self.style.SUCCESS(f'✅ Found tenant: {tenant.name}'))
        except UserProfile.DoesNotExist:
            # Create profile for demo user
            if create_demo:
                # Get or create default tenant
                tenant, _ = Tenant.objects.get_or_create(
                    name='Demo School',
                    defaults={'industry': 'education'}
                )
                # Get or create admin role
                admin_role, _ = Role.objects.get_or_create(
                    name='admin',
                    defaults={'description': 'Administrator'}
                )
                # Create profile
                profile = UserProfile._default_manager.create(
                    user=user,
                    tenant=tenant,
                    role=admin_role
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Created profile for demo user'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ User profile not found for {username}. Please create a profile first.'))
                return

        self.stdout.write(self.style.WARNING('\n🔄 Creating demo data...\n'))

        # 1. Create Classes
        self.stdout.write('📚 Creating classes...')
        classes_data = [
            {'name': 'STD 1', 'schedule': 'Monday to Friday, 9:00 AM - 3:00 PM'},
            {'name': 'STD 2', 'schedule': 'Monday to Friday, 9:00 AM - 3:00 PM'},
            {'name': 'STD 3', 'schedule': 'Monday to Friday, 9:00 AM - 3:00 PM'},
            {'name': 'STD 4', 'schedule': 'Monday to Friday, 9:00 AM - 3:00 PM'},
            {'name': 'STD 5', 'schedule': 'Monday to Friday, 9:00 AM - 3:00 PM'},
            {'name': 'STD 6', 'schedule': 'Monday to Friday, 9:00 AM - 3:30 PM'},
            {'name': 'STD 7', 'schedule': 'Monday to Friday, 9:00 AM - 3:30 PM'},
            {'name': 'STD 8', 'schedule': 'Monday to Friday, 9:00 AM - 3:30 PM'},
        ]
        classes = []
        for class_data in classes_data:
            class_obj, created = Class._default_manager.get_or_create(
                tenant=tenant,
                name=class_data['name'],
                defaults={'schedule': class_data['schedule']}
            )
            classes.append(class_obj)
            if created:
                self.stdout.write(f'  ✅ Created class: {class_obj.name}')

        # 2. Create Academic Year and Terms
        self.stdout.write('\n📅 Creating academic years and terms...')
        current_year = datetime.now().year
        academic_year, created = AcademicYear._default_manager.get_or_create(
            tenant=tenant,
            name=f'{current_year}-{current_year + 1}',
            defaults={
                'start_date': datetime(current_year, 4, 1).date(),
                'end_date': datetime(current_year + 1, 3, 31).date(),
                'is_current': True
            }
        )
        if created:
            self.stdout.write(f'  ✅ Created academic year: {academic_year.name}')

        terms_data = [
            {'name': 'Term 1', 'order': 1, 'start': datetime(current_year, 4, 1), 'end': datetime(current_year, 9, 30)},
            {'name': 'Term 2', 'order': 2, 'start': datetime(current_year, 10, 1), 'end': datetime(current_year + 1, 3, 31)},
        ]
        terms = []
        for term_data in terms_data:
            term, created = Term._default_manager.get_or_create(
                tenant=tenant,
                academic_year=academic_year,
                name=term_data['name'],
                defaults={
                    'order': term_data['order'],
                    'start_date': term_data['start'].date(),
                    'end_date': term_data['end'].date(),
                    'is_active': term_data['order'] == 1
                }
            )
            terms.append(term)
            if created:
                self.stdout.write(f'  ✅ Created term: {term.name}')

        # 3. Create Subjects for each class
        self.stdout.write('\n📖 Creating subjects...')
        subjects_data = [
            {'name': 'Mathematics', 'code': 'MATH'},
            {'name': 'Science', 'code': 'SCI'},
            {'name': 'English', 'code': 'ENG'},
            {'name': 'Hindi', 'code': 'HIN'},
            {'name': 'Social Studies', 'code': 'SST'},
            {'name': 'Computer Science', 'code': 'CS'},
        ]
        subjects = {}
        for class_obj in classes[:5]:  # For first 5 classes
            for subj_data in subjects_data:
                subject, created = Subject._default_manager.get_or_create(
                    tenant=tenant,
                    class_obj=class_obj,
                    name=subj_data['name'],
                    defaults={
                        'code': subj_data['code'],
                        'max_marks': 100,
                        'has_practical': subj_data['name'] in ['Science', 'Computer Science']
                    }
                )
                if class_obj.name not in subjects:
                    subjects[class_obj.name] = []
                subjects[class_obj.name].append(subject)
                if created:
                    self.stdout.write(f'  ✅ Created subject: {subject.name} for {class_obj.name}')

        # 4. Create Students
        self.stdout.write('\n👥 Creating students...')
        student_names = [
            'Aarav Sharma', 'Priya Patel', 'Rahul Singh', 'Ananya Reddy', 'Karan Mehta',
            'Sneha Kumar', 'Vikram Agarwal', 'Divya Nair', 'Arjun Joshi', 'Kavya Iyer',
            'Raj Malhotra', 'Sanya Desai', 'Aditya Gupta', 'Maya Choudhary', 'Rohan Kapoor',
            'Neha Verma', 'Siddharth Rao', 'Ishita Shah', 'Krishna Tiwari', 'Pooja Agarwal',
        ]
        students = []
        for i, name in enumerate(student_names):
            class_idx = i % len(classes[:5])  # Distribute across first 5 classes
            assigned_class = classes[class_idx]
            
            first_name, last_name = name.split(' ', 1)
            email = f"{first_name.lower()}.{last_name.lower()}@demo.com"
            
            student, created = Student._default_manager.get_or_create(
                tenant=tenant,
                email=email,
                defaults={
                    'name': name,
                    'assigned_class': assigned_class,
                    'admission_date': datetime(current_year, 4, 1).date() - timedelta(days=random.randint(0, 180)),
                    'date_of_birth': datetime(current_year - 7, random.randint(1, 12), random.randint(1, 28)).date(),
                    'gender': random.choice(['Male', 'Female']),
                    'cast': random.choice(['General', 'OBC', 'SC', 'ST']),
                    'phone': f'9{random.randint(100000000, 999999999)}',
                    'parent_name': f'Parent of {first_name}',
                    'parent_phone': f'9{random.randint(100000000, 999999999)}',
                    'address': f'{random.randint(1, 999)} Demo Street, Demo City',
                    'is_active': True
                }
            )
            students.append(student)
            if created:
                self.stdout.write(f'  ✅ Created student: {student.name} ({student.assigned_class.name})')

        # 5. Create Fee Structures
        self.stdout.write('\n💰 Creating fee structures...')
        fee_types = [
            {'type': 'TUITION', 'amount': 10000},
            {'type': 'EXAM', 'amount': 2000},
            {'type': 'LIBRARY', 'amount': 500},
            {'type': 'TRANSPORT', 'amount': 3000, 'optional': True},
        ]
        fee_structures = []
        for class_obj in classes[:5]:
            for fee_data in fee_types:
                fee_structure, created = FeeStructure._default_manager.get_or_create(
                    tenant=tenant,
                    class_obj=class_obj,
                    fee_type=fee_data['type'],
                    academic_year=academic_year.name,
                    defaults={
                        'amount': Decimal(fee_data['amount']),
                        'description': f'{fee_data["type"]} for {class_obj.name}',
                        'is_optional': fee_data.get('optional', False),
                        'due_date': datetime(current_year, 6, 30).date(),
                        'installments_enabled': fee_data['type'] == 'TUITION'
                    }
                )
                fee_structures.append(fee_structure)
                if created:
                    self.stdout.write(f'  ✅ Created fee structure: {fee_structure.fee_type} for {class_obj.name}')

        # 6. Create Fee Payments
        self.stdout.write('\n💳 Creating fee payments...')
        payment_methods = ['CASH', 'ONLINE', 'CHEQUE', 'CARD', 'UPI']
        for student in students[:15]:  # Payments for first 15 students
            class_obj = student.assigned_class
            tuition_fee = next((fs for fs in fee_structures if fs.class_obj == class_obj and fs.fee_type == 'TUITION'), None)
            
            if tuition_fee:
                # Create 1-3 payments per student
                num_payments = random.randint(1, 3)
                for i in range(num_payments):
                    amount_paid = Decimal(random.randint(2000, int(tuition_fee.amount)))
                    receipt_num = f'RCP-{student.id:04d}{random.randint(1000, 9999)}'
                    
                    payment, created = FeePayment._default_manager.get_or_create(
                        tenant=tenant,
                        student=student,
                        fee_structure=tuition_fee,
                        receipt_number=receipt_num,
                        defaults={
                            'amount_paid': amount_paid,
                            'payment_date': datetime.now().date() - timedelta(days=random.randint(0, 90)),
                            'payment_method': random.choice(payment_methods),
                            'notes': f'Payment #{i+1} for {tuition_fee.fee_type}',
                            'discount_amount': Decimal(random.randint(0, 500)) if random.random() > 0.7 else Decimal(0),
                            'collected_by': profile if hasattr(profile, 'user') else None
                        }
                    )
                    if created:
                        self.stdout.write(f'  ✅ Created payment: ₹{amount_paid} for {student.name}')

        # 7. Create Assessment Types and Assessments
        self.stdout.write('\n📝 Creating assessments...')
        assessment_types_data = [
            {'name': 'Unit Test'},
            {'name': 'Mid-Term Exam'},
            {'name': 'Final Exam'},
        ]
        assessment_types = []
        for at_data in assessment_types_data:
            at, created = AssessmentType._default_manager.get_or_create(
                tenant=tenant,
                name=at_data['name']
            )
            assessment_types.append(at)

        # Create assessments for Term 1
        current_term = terms[0]
        for class_name, class_subjects in subjects.items():
            for subject in class_subjects[:4]:  # First 4 subjects
                assessment_type = random.choice(assessment_types)
                assessment, created = Assessment._default_manager.get_or_create(
                    tenant=tenant,
                    subject=subject,
                    term=current_term,
                    assessment_type=assessment_type,
                    name=f'{assessment_type.name} - {subject.name}',
                    defaults={
                        'max_marks': 100,
                        'date': datetime.now().date() - timedelta(days=random.randint(10, 60))
                    }
                )
                if created:
                    self.stdout.write(f'  ✅ Created assessment: {assessment.name}')

        # 8. Create Marks Entries
        self.stdout.write('\n📊 Creating marks entries...')
        assessments = Assessment._default_manager.filter(tenant=tenant, term=current_term)
        for assessment in assessments:
            subject_students = [s for s in students if s.assigned_class == assessment.subject.class_obj]
            for student in subject_students[:10]:  # Marks for first 10 students
                marks_obtained = Decimal(random.randint(60, 95))
                marks_entry, created = MarksEntry._default_manager.get_or_create(
                    tenant=tenant,
                    student=student,
                    assessment=assessment,
                    defaults={
                        'marks_obtained': marks_obtained,
                        'max_marks': assessment.max_marks
                    }
                )
                if created:
                    self.stdout.write(f'  ✅ Created marks: {student.name} - {marks_obtained}/{assessment.max_marks}')

        # 9. Create Report Cards
        self.stdout.write('\n🎓 Creating report cards...')
        for student in students[:10]:
            report_card, created = ReportCard._default_manager.get_or_create(
                tenant=tenant,
                student=student,
                academic_year=academic_year,
                term=current_term,
                defaults={
                    'class_obj': student.assigned_class,
                    'teacher_remarks': f'{student.name} has shown excellent progress this term.',
                    'principal_remarks': f'Keep up the good work, {student.name.split()[0]}!',
                    'conduct_grade': random.choice(['A+', 'A', 'B+', 'B']),
                    'days_present': random.randint(80, 95),
                    'days_absent': random.randint(5, 20),
                    'issued_date': datetime.now().date()
                }
            )
            if created:
                # Calculate totals
                marks_entries = MarksEntry._default_manager.filter(
                    tenant=tenant,
                    student=student,
                    assessment__term=current_term
                )
                total_marks = sum(float(me.marks_obtained) for me in marks_entries)
                max_total = sum(float(me.max_marks) for me in marks_entries)
                percentage = (total_marks / max_total * 100) if max_total > 0 else 0
                
                report_card.total_marks = Decimal(str(total_marks))
                report_card.max_total_marks = Decimal(str(max_total))
                report_card.percentage = Decimal(str(percentage))
                
                # Determine grade
                if percentage >= 90:
                    report_card.grade = 'A+'
                elif percentage >= 80:
                    report_card.grade = 'A'
                elif percentage >= 70:
                    report_card.grade = 'B+'
                elif percentage >= 60:
                    report_card.grade = 'B'
                else:
                    report_card.grade = 'C'
                
                report_card.attendance_percentage = Decimal(
                    str((report_card.days_present / (report_card.days_present + report_card.days_absent) * 100))
                )
                report_card.save()
                
                self.stdout.write(f'  ✅ Created report card: {student.name} ({report_card.grade})')

        # 10. Create Attendance Records
        self.stdout.write('\n📋 Creating attendance records...')
        attendance_count = 0
        for student in students[:15]:
            for day in range(30):  # Last 30 days
                date = datetime.now().date() - timedelta(days=day)
                if date.weekday() < 5:  # Monday to Friday
                    is_present = random.choice([True, True, True, False])  # 75% present rate
                    att, created = Attendance._default_manager.get_or_create(
                        tenant=tenant,
                        student=student,
                        date=date,
                        defaults={'present': is_present}
                    )
                    if created:
                        attendance_count += 1
        self.stdout.write(f'  ✅ Created {attendance_count} attendance records')

        # 11. Create Staff/Teachers
        self.stdout.write('\n👨‍🏫 Creating staff/teachers...')
        staff_names = [
            'Rajesh Kumar (Principal)', 'Sunita Sharma (Math)', 'Amit Patel (Science)',
            'Deepika Singh (English)', 'Vikram Mehta (Hindi)'
        ]
        teacher_role, _ = Role.objects.get_or_create(name='teacher', defaults={'description': 'Teacher'})
        principal_role, _ = Role.objects.get_or_create(name='principal', defaults={'description': 'Principal'})
        
        for staff_name in staff_names:
            name_parts = staff_name.split(' (')
            name = name_parts[0]
            role_name = name_parts[1].replace(')', '') if len(name_parts) > 1 else 'teacher'
            username = name.lower().replace(' ', '')
            
            staff_user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@demo.com',
                    'first_name': name.split()[0],
                    'last_name': ' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
                }
            )
            if created:
                staff_user.set_password('Demo123!')
                staff_user.save()
            
            staff_role = principal_role if 'Principal' in staff_name else teacher_role
            staff_profile, created = UserProfile._default_manager.get_or_create(
                user=staff_user,
                defaults={
                    'tenant': tenant,
                    'role': staff_role,
                    'phone': f'9{random.randint(100000000, 999999999)}'
                }
            )
            if created:
                self.stdout.write(f'  ✅ Created staff: {name} ({staff_role.name})')

        # 12. Create Staff Attendance
        self.stdout.write('\n⏰ Creating staff attendance...')
        staff_profiles = UserProfile._default_manager.filter(tenant=tenant, role__name__in=['teacher', 'principal'])
        for staff in staff_profiles[:5]:
            for day in range(20):  # Last 20 days
                date = datetime.now().date() - timedelta(days=day)
                if date.weekday() < 5:  # Monday to Friday
                    check_in = datetime.combine(date, datetime.min.time().replace(hour=9, minute=0))
                    check_out = datetime.combine(date, datetime.min.time().replace(hour=17, minute=0))
                    
                    StaffAttendance._default_manager.get_or_create(
                        tenant=tenant,
                        staff=staff,
                        date=date,
                        defaults={
                            'check_in_time': check_in,
                            'check_out_time': check_out
                        }
                    )

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data creation complete!'))
        self.stdout.write(self.style.SUCCESS(f'\n📊 Summary:'))
        self.stdout.write(f'  • Classes: {len(classes)}')
        self.stdout.write(f'  • Students: {len(students)}')
        self.stdout.write(f'  • Fee Structures: {len(fee_structures)}')
        self.stdout.write(f'  • Fee Payments: {FeePayment._default_manager.filter(tenant=tenant).count()}')
        self.stdout.write(f'  • Report Cards: {ReportCard._default_manager.filter(tenant=tenant).count()}')
        self.stdout.write(f'  • Assessments: {Assessment._default_manager.filter(tenant=tenant).count()}')
        self.stdout.write(f'  • Marks Entries: {MarksEntry._default_manager.filter(tenant=tenant).count()}')
        
        if create_demo:
            self.stdout.write(self.style.WARNING(f'\n🔑 Login Credentials:'))
            self.stdout.write(f'  Username: demo_education')
            self.stdout.write(f'  Password: Demo123456!')
        else:
            self.stdout.write(self.style.WARNING(f'\n✅ Demo data added for user: {username}'))

