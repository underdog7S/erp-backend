from django.core.management.base import BaseCommand
from api.models.user import UserProfile
from education.models import Department as EduDepartment
from django.db import transaction

# If you have healthcare and manufacturing Department and Staff models, import them:
try:
    from healthcare.models import Department as HealthDepartment, Staff as HealthStaff
except ImportError:
    HealthDepartment = None
    HealthStaff = None
try:
    from manufacturing.models import Department as ManufDepartment, Staff as ManufStaff
except ImportError:
    ManufDepartment = None
    ManufStaff = None

class Command(BaseCommand):
    help = 'Assign a default department to all UserProfiles (education), healthcare staff, and manufacturing staff missing one.'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Education
            default_edu_dept, _ = EduDepartment._default_manager.get_or_create(name='Default Education Department', tenant_id=1)
            edu_profiles = UserProfile._default_manager.filter(department__isnull=True)
            count = 0
            for profile in edu_profiles:
                profile.department = default_edu_dept
                profile.save()
                count += 1
            self.stdout.write(self.style.SUCCESS(f'Assigned default education department to {count} UserProfiles.'))

            # Healthcare
            if HealthDepartment and HealthStaff:
                default_health_dept, _ = HealthDepartment._default_manager.get_or_create(name='Default Healthcare Department', tenant_id=1)
                health_staff = HealthStaff._default_manager.filter(department__isnull=True)
                count = 0
                for staff in health_staff:
                    staff.department = default_health_dept
                    staff.save()
                    count += 1
                self.stdout.write(self.style.SUCCESS(f'Assigned default healthcare department to {count} Staff.'))
            else:
                self.stdout.write(self.style.WARNING('Healthcare Staff or Department model not found.'))

            # Manufacturing
            if ManufDepartment and ManufStaff:
                default_manuf_dept, _ = ManufDepartment._default_manager.get_or_create(name='Default Manufacturing Department', tenant_id=1)
                manuf_staff = ManufStaff._default_manager.filter(department__isnull=True)
                count = 0
                for staff in manuf_staff:
                    staff.department = default_manuf_dept
                    staff.save()
                    count += 1
                self.stdout.write(self.style.SUCCESS(f'Assigned default manufacturing department to {count} Staff.'))
            else:
                self.stdout.write(self.style.WARNING('Manufacturing Staff or Department model not found.'))

        self.stdout.write(self.style.SUCCESS('Department assignment complete.')) 