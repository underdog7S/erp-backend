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
	gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='GST percentage, e.g. 5. 0 means no tax is calculated')
	price_includes_tax = models.BooleanField(default=True, help_text='The listed price already contains GST')

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
	
	ORDER_TYPE_CHOICES = [
		('dine_in', 'Dine In'),
		('takeaway', 'Takeaway'),
		('delivery', 'Delivery'),
		('cloud_kitchen', 'Cloud Kitchen'),
	]

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name='orders', null=True, blank=True)
	customer_name = models.CharField(max_length=150, blank=True)
	customer_phone = models.CharField(max_length=20, blank=True)  # For cloud kitchen/delivery
	customer_email = models.EmailField(blank=True)  # For cloud kitchen/delivery
	delivery_address = models.TextField(blank=True)  # For delivery/cloud kitchen orders
	order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='dine_in')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
	created_at = models.DateTimeField(auto_now_add=True)
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	external_order_id = models.CharField(max_length=100, blank=True, null=True)  # For external API orders
	notes = models.TextField(blank=True)  # Special instructions

	def __str__(self):
		return f"Order {self.id}"


class OrderItem(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField(default=1)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
	tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

	def line_total(self):
		return self.quantity * self.price


class ExternalAPIIntegration(models.Model):
	"""Model to store external API integration settings for menu sync"""
	API_TYPE_CHOICES = [
		('zomato', 'Zomato'),
		('swiggy', 'Swiggy'),
		('uber_eats', 'Uber Eats'),
		('custom', 'Custom API'),
	]
	
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	name = models.CharField(max_length=100)  # Integration name
	api_type = models.CharField(max_length=50, choices=API_TYPE_CHOICES)
	api_url = models.URLField()  # Base API URL
	api_key = models.CharField(max_length=255, blank=True)  # API key/token
	api_secret = models.CharField(max_length=255, blank=True)  # API secret (if needed)
	menu_endpoint = models.CharField(max_length=200, default='/menu')  # Menu endpoint path
	order_endpoint = models.CharField(max_length=200, default='/orders', blank=True)  # Order webhook endpoint
	webhook_url = models.URLField(blank=True)  # Webhook URL for order updates
	webhook_secret = models.CharField(max_length=255, blank=True)  # Webhook secret for verification
	is_active = models.BooleanField(default=True)
	auto_sync = models.BooleanField(default=False)  # Auto sync menu periodically
	sync_interval_minutes = models.PositiveIntegerField(default=60)  # Sync interval
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	# Additional settings as JSON
	settings = models.JSONField(default=dict, blank=True)  # Store API-specific settings
	
	class Meta:
		unique_together = ('tenant', 'name')
	
	def __str__(self):
		return f"{self.name} - {self.tenant.name}"


class MenuSyncLog(models.Model):
	"""Log for menu synchronization from external APIs"""
	STATUS_CHOICES = [
		('success', 'Success'),
		('failed', 'Failed'),
		('partial', 'Partial'),
	]
	
	integration = models.ForeignKey(ExternalAPIIntegration, on_delete=models.CASCADE, related_name='sync_logs')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES)
	items_synced = models.PositiveIntegerField(default=0)
	items_created = models.PositiveIntegerField(default=0)
	items_updated = models.PositiveIntegerField(default=0)
	items_failed = models.PositiveIntegerField(default=0)
	error_message = models.TextField(blank=True)
	synced_at = models.DateTimeField(auto_now_add=True)
	
	def __str__(self):
		return f"Sync {self.id} - {self.integration.name} - {self.status}"

# ==========================================
# ENTERPRISE RESTAURANT MODULES
# ==========================================

class KDSTicket(models.Model):
    TICKET_STATUS = [
        ('queued', 'Queued'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='kds_tickets')
    order = models.ForeignKey('restaurant.Order', on_delete=models.CASCADE, related_name='kds_tickets', null=True)
    table_number = models.CharField(max_length=20, blank=True, null=True)
    items = models.JSONField(help_text='List of items with modifiers')
    status = models.CharField(max_length=20, choices=TICKET_STATUS, default='queued')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'KDS Ticket {self.id} - {self.status}'

class RecipeBOM(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='recipes')
    menu_item = models.OneToOneField(MenuItem, on_delete=models.CASCADE, related_name='recipe')
    ingredients = models.JSONField(help_text='List of ingredients with quantities (e.g., [{"item": "Flour", "qty": 200, "unit": "g"}])')
    instructions = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Recipe for {self.menu_item.name}'


