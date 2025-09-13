from django.db import models
from api.models.user import Tenant


class MenuCategory(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)

	def __str__(self):
		return self.name


class MenuItem(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	category = models.ForeignKey(MenuCategory, on_delete=models.PROTECT, related_name='items')
	name = models.CharField(max_length=150)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	is_available = models.BooleanField(default=True)

	def __str__(self):
		return self.name


class Table(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	number = models.CharField(max_length=20)
	seats = models.PositiveSmallIntegerField(default=2)

	class Meta:
		unique_together = ('tenant', 'number')

	def __str__(self):
		return f"Table {self.number}"


class Order(models.Model):
	STATUS_CHOICES = [
		('open', 'Open'),
		('served', 'Served'),
		('paid', 'Paid'),
		('cancelled', 'Cancelled'),
	]

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name='orders', null=True, blank=True)
	customer_name = models.CharField(max_length=150, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
	created_at = models.DateTimeField(auto_now_add=True)
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

	def __str__(self):
		return f"Order {self.id}"


class OrderItem(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField(default=1)
	price = models.DecimalField(max_digits=10, decimal_places=2)

	def line_total(self):
		return self.quantity * self.price


