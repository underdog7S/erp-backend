from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from django.db import models
from api.models.user import Tenant
from api.utils.storage_calculator import recalculate_tenant_storage
import threading

def recalculate_storage_async(tenant_id):
    """Run storage recalculation in a background thread to prevent blocking API responses."""
    thread = threading.Thread(target=recalculate_tenant_storage, args=(tenant_id,))
    thread.daemon = True
    thread.start()

# Dynamic signal registration for all models with a 'tenant' and a 'FileField/ImageField'
def register_storage_signals():
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            has_tenant = any(f.name == 'tenant' for f in model._meta.fields)
            has_file = any(isinstance(f, (models.FileField, models.ImageField)) for f in model._meta.fields)
            
            if has_tenant and has_file:
                # Connect post_save and post_delete signals
                @receiver(post_save, sender=model, dispatch_uid=f"storage_save_{model._meta.db_table}")
                def storage_post_save(sender, instance, **kwargs):
                    if hasattr(instance, 'tenant_id') and instance.tenant_id:
                        recalculate_storage_async(instance.tenant_id)
                        
                @receiver(post_delete, sender=model, dispatch_uid=f"storage_delete_{model._meta.db_table}")
                def storage_post_delete(sender, instance, **kwargs):
                    if hasattr(instance, 'tenant_id') and instance.tenant_id:
                        recalculate_storage_async(instance.tenant_id)

