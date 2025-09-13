from django.contrib import admin
from .models import ServiceCategory, Service, Stylist, Appointment


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'tenant')
	list_filter = ('tenant',)
	search_fields = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
	list_display = ('name', 'tenant', 'category', 'duration_minutes', 'price', 'is_active')
	list_filter = ('tenant', 'category', 'is_active')
	search_fields = ('name',)


@admin.register(Stylist)
class StylistAdmin(admin.ModelAdmin):
	list_display = ('first_name', 'last_name', 'tenant', 'phone', 'email', 'is_active')
	list_filter = ('tenant', 'is_active')
	search_fields = ('first_name', 'last_name', 'phone', 'email')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
	list_display = ('id', 'tenant', 'customer_name', 'service', 'stylist', 'start_time', 'end_time', 'status', 'price')
	list_filter = ('tenant', 'status', 'service__category')
	search_fields = ('id', 'customer_name')

