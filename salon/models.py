from django.db import models
from api.models.user import Tenant


class ServiceCategory(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)

	class Meta:
		ordering = ['name', 'id']

	def __str__(self):
		return self.name


class Service(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='services')
	name = models.CharField(max_length=150)
	duration_minutes = models.PositiveIntegerField(default=30)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	image = models.ImageField(upload_to='salon/services/', blank=True, null=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['name', 'id']

	def __str__(self):
		return self.name


class Stylist(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	first_name = models.CharField(max_length=100)
	last_name = models.CharField(max_length=100, blank=True)
	phone = models.CharField(max_length=20, blank=True)
	email = models.EmailField(blank=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['first_name', 'last_name', 'id']

	def __str__(self):
		return f"{self.first_name} {self.last_name}".strip()


class Appointment(models.Model):
	STATUS_CHOICES = [
		('scheduled', 'Scheduled'),
		('in_progress', 'In Progress'),
		('completed', 'Completed'),
		('cancelled', 'Cancelled'),
	]

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='appointments')
	stylist = models.ForeignKey(Stylist, on_delete=models.PROTECT, related_name='appointments')
	customer_name = models.CharField(max_length=150)
	customer_phone = models.CharField(max_length=20, blank=True)
	start_time = models.DateTimeField()
	end_time = models.DateTimeField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
	price = models.DecimalField(max_digits=10, decimal_places=2)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-start_time', 'id']

	def __str__(self):
		return f"Appt {self.id} - {self.customer_name}"


