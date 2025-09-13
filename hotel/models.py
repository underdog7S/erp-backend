from django.db import models
from api.models.user import Tenant


class RoomType(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	base_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

	def __str__(self):
		return f"{self.name}"


class Room(models.Model):
	STATUS_CHOICES = [
		('available', 'Available'),
		('occupied', 'Occupied'),
		('maintenance', 'Maintenance'),
	]

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	room_number = models.CharField(max_length=20)
	room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name='rooms')
	floor = models.IntegerField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

	class Meta:
		unique_together = ('tenant', 'room_number')

	def __str__(self):
		return f"Room {self.room_number}"


class Guest(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	first_name = models.CharField(max_length=100)
	last_name = models.CharField(max_length=100, blank=True)
	phone = models.CharField(max_length=20, blank=True)
	email = models.EmailField(blank=True)

	def __str__(self):
		return f"{self.first_name} {self.last_name}".strip()


class Booking(models.Model):
	STATUS_CHOICES = [
		('reserved', 'Reserved'),
		('checked_in', 'Checked In'),
		('checked_out', 'Checked Out'),
		('cancelled', 'Cancelled'),
	]

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='bookings')
	guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name='bookings')
	check_in = models.DateTimeField()
	check_out = models.DateTimeField()
	num_guests = models.PositiveSmallIntegerField(default=1)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reserved')
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Booking {self.id} - Room {self.room.room_number}"


