from django.contrib import admin
from .models import ServiceCategory, Service, Stylist, Appointment
from api.admin_site import secure_admin_site


class ServiceCategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'tenant')
	list_filter = ('tenant',)
	search_fields = ('name',)


class ServiceAdmin(admin.ModelAdmin):
	list_display = ('name', 'tenant', 'category', 'duration_minutes', 'price', 'is_active')
	list_filter = ('tenant', 'category', 'is_active')
	search_fields = ('name',)


class StylistAdmin(admin.ModelAdmin):
	list_display = ('first_name', 'last_name', 'tenant', 'phone', 'email', 'is_active')
	list_filter = ('tenant', 'is_active')
	search_fields = ('first_name', 'last_name', 'phone', 'email')


class AppointmentAdmin(admin.ModelAdmin):
	list_display = ('id', 'tenant', 'customer_name', 'service', 'stylist', 'start_time', 'end_time', 'status', 'price')
	list_filter = ('tenant', 'status', 'service__category')
	search_fields = ('id', 'customer_name')

# Register with secure_admin_site
secure_admin_site.register(ServiceCategory, ServiceCategoryAdmin)
secure_admin_site.register(Service, ServiceAdmin)
secure_admin_site.register(Stylist, StylistAdmin)
secure_admin_site.register(Appointment, AppointmentAdmin)

