from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal

from education.models import (
    AcademicYear,
    Term,
    Subject,
    AssessmentType,
    Assessment,
    MarksEntry,
    Student,
    FeeStructure,
    FeeInstallmentPlan,
    FeeInstallment,
    ReportCard,
)


class Command(BaseCommand):
    help = "Seed demo data for report cards and installments for the first active student"

    def handle(self, *args, **options):
        student = Student._default_manager.filter(is_active=True).first()
        if not student:
            self.stdout.write(self.style.WARNING("No active student found. Create a student first."))
            return

        class_obj = student.assigned_class
        if not class_obj:
            self.stdout.write(self.style.WARNING("Student must be assigned to a class."))
            return

        tenant = student.tenant

        # Academic Year and Term
        ay, _ = AcademicYear._default_manager.get_or_create(
            tenant=tenant,
            name="2025-26",
            defaults={
                "start_date": "2025-04-01",
                "end_date": "2026-03-31",
                "is_current": True,
            },
        )
        term, _ = Term._default_manager.get_or_create(
            tenant=tenant,
            academic_year=ay,
            name="Term 1",
            defaults={
                "order": 1,
                "start_date": "2025-04-01",
                "end_date": "2025-09-30",
                "is_active": True,
            },
        )

        # Multiple Subjects with Marks Entries
        subjects_data = [
            {"name": "Mathematics", "code": "MATH", "marks": 85},
            {"name": "Science", "code": "SCI", "marks": 90},
            {"name": "English", "code": "ENG", "marks": 80},
            {"name": "Social Studies", "code": "SST", "marks": 75},
        ]
        
        a_type, _ = AssessmentType._default_manager.get_or_create(
            tenant=tenant, name="Unit Test"
        )
        
        for subj_data in subjects_data:
            subject, _ = Subject._default_manager.get_or_create(
                tenant=tenant,
                class_obj=class_obj,
                name=subj_data["name"],
                defaults={"code": subj_data["code"], "max_marks": 100, "has_practical": False},
            )
            assessment, _ = Assessment._default_manager.get_or_create(
                tenant=tenant,
                subject=subject,
                term=term,
                assessment_type=a_type,
                name=f"UT1-{subj_data['code']}",
                defaults={"max_marks": 100, "date": timezone.now().date()},
            )
            # Marks Entry for this subject
            MarksEntry._default_manager.get_or_create(
                tenant=tenant,
                student=student,
                assessment=assessment,
                defaults={
                    "marks_obtained": Decimal(str(subj_data["marks"])),
                    "max_marks": assessment.max_marks,
                },
            )

        # Report Card
        rc, created = ReportCard._default_manager.get_or_create(
            tenant=tenant,
            student=student,
            academic_year=ay,
            term=term,
            defaults={"class_obj": class_obj},
        )
        # Always update to ensure proper linking
        rc.class_obj = class_obj
        rc.academic_year = ay
        rc.term = term
        # Try model calc; fallback to manual to avoid type issues
        try:
            rc.calculate_totals()
        except Exception:
            # Manual simple totals
            total_obtained = Decimal("0")
            max_total = Decimal("0")
            for me in MarksEntry._default_manager.filter(tenant=tenant, student=student, assessment__term=term):
                total_obtained += Decimal(str(me.marks_obtained))
                max_total += Decimal(str(getattr(me, "max_marks", assessment.max_marks)))
            rc.total_marks = total_obtained
            rc.max_total_marks = max_total if max_total else Decimal("100")
            rc.percentage = (total_obtained / rc.max_total_marks * Decimal("100")) if rc.max_total_marks else Decimal("0")
            rc.grade = "A" if rc.percentage >= 75 else ("B" if rc.percentage >= 60 else "C")
        rc.save()

        # Fee Structure
        fee_structure = (
            FeeStructure._default_manager.filter(tenant=tenant, class_obj=class_obj).first()
        )
        if not fee_structure:
            fee_structure = FeeStructure._default_manager.create(
                tenant=tenant,
                class_obj=class_obj,
                fee_type="TUITION",
                amount=Decimal("5000.00"),
                description="Demo Tuition",
                is_optional=False,
                academic_year="2025-26",
            )

        # Installment Plan
        plan, _ = FeeInstallmentPlan._default_manager.get_or_create(
            tenant=tenant,
            fee_structure=fee_structure,
            name="2-Part Plan",
            defaults={
                "number_of_installments": 2,
                "installment_type": "EQUAL",
                "description": "Demo plan",
                "is_active": True,
            },
        )

        # Installments
        if not FeeInstallment._default_manager.filter(
            tenant=tenant, student=student, fee_structure=fee_structure
        ).exists():
            amount_per = fee_structure.amount / plan.number_of_installments
            today = timezone.now().date()
            for i in range(1, plan.number_of_installments + 1):
                inst = FeeInstallment._default_manager.create(
                    tenant=tenant,
                    student=student,
                    fee_structure=fee_structure,
                    installment_plan=plan,
                    installment_number=i,
                    due_amount=amount_per,
                    due_date=today,
                )
                inst.update_status()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded report card and installments for student: {student.name} (class: {class_obj.name})"
            )
        )


