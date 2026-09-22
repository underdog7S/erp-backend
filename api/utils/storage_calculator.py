from django.apps import apps
from django.db import models
from django.db.models import Sum
from api.models.user import Tenant
from django.core.files.storage import default_storage

def recalculate_tenant_storage(tenant_id):
    """
    Recalculates the exact storage used by a tenant in Megabytes.
    It dynamically scans all models in the project that belong to a tenant
    and contain a FileField or ImageField, summing up their physical sizes.
    """
    try:
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return 0

    total_bytes = 0
    
    # Iterate through all installed models in the Django project
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            # Check if this model belongs to a tenant
            has_tenant = any(f.name == 'tenant' for f in model._meta.fields)
            if not has_tenant:
                continue
                
            # Find all file/image fields on this model
            file_fields = [f.name for f in model._meta.fields if isinstance(f, (models.FileField, models.ImageField))]
            
            if not file_fields:
                continue
                
            # Fetch all instances for this tenant
            instances = model.objects.filter(tenant=tenant)
            
            for instance in instances:
                for field_name in file_fields:
                    file_field = getattr(instance, field_name)
                    if file_field and file_field.name:
                        try:
                            # Use default_storage to get the accurate file size
                            # This works for both Local Filesystem and AWS S3
                            if default_storage.exists(file_field.name):
                                total_bytes += default_storage.size(file_field.name)
                        except Exception as e:
                            # Catch cases where file might be deleted from disk but DB record exists
                            pass
                            
    # Add files manually uploaded to the generic tenant directory (if any)
    # This accounts for files uploaded via FileUploadView that aren't tied to a specific model field
    try:
        tenant_dir = f"tenant_{tenant.id}/"
        directories, files = default_storage.listdir(tenant_dir)
        for file in files:
            file_path = f"{tenant_dir}{file}"
            try:
                if default_storage.exists(file_path):
                    total_bytes += default_storage.size(file_path)
            except Exception:
                pass
    except Exception:
        # Directory might not exist or storage backend doesn't support listdir
        pass

    # Convert to MB
    total_mb = total_bytes / (1024 * 1024)
    
    # Update the tenant record
    tenant.storage_used_mb = round(total_mb, 2)
    tenant.save(update_fields=['storage_used_mb'])
    
    return tenant.storage_used_mb

def recalculate_all_tenants_storage():
    """
    Iterates through all tenants and updates their storage usage.
    This can be hooked up to a Celery periodic task (e.g., nightly).
    """
    results = {}
    for tenant in Tenant.objects.all():
        used_mb = recalculate_tenant_storage(tenant.id)
        results[tenant.name] = used_mb
    return results
