from django.core.management.base import BaseCommand
from api.utils.storage_calculator import recalculate_all_tenants_storage, recalculate_tenant_storage
from api.models.user import Tenant

class Command(BaseCommand):
    help = 'Recalculates the exact storage (MB) used by all tenants based on physical file sizes.'

    def add_arguments(self, parser):
        parser.add_argument('--tenant_id', type=int, help='Calculate storage for a specific tenant ID')

    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id)
                self.stdout.write(f"Calculating storage for Tenant: {tenant.name}...")
                used_mb = recalculate_tenant_storage(tenant_id)
                self.stdout.write(self.style.SUCCESS(f"Done! {tenant.name} is using {used_mb} MB."))
            except Tenant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Tenant {tenant_id} does not exist."))
        else:
            self.stdout.write("Calculating storage for all tenants (this may take a while depending on file counts)...")
            results = recalculate_all_tenants_storage()
            for name, used_mb in results.items():
                self.stdout.write(self.style.SUCCESS(f"- {name}: {used_mb} MB"))
            
            self.stdout.write(self.style.SUCCESS("All tenants successfully updated!"))
