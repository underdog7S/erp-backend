from django.contrib import admin
from .models import RoomType, Room, Guest, Booking


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
	list_display = ('name', 'tenant', 'base_rate')
	list_filter = ('tenant',)
	search_fields = ('name',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
	list_display = ('room_number', 'tenant', 'room_type', 'status', 'floor')
	list_filter = ('tenant', 'status', 'room_type')
	search_fields = ('room_number',)


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
	list_display = ('first_name', 'last_name', 'tenant', 'phone', 'email')
	list_filter = ('tenant',)
	search_fields = ('first_name', 'last_name', 'phone', 'email')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
	list_display = ('id', 'tenant', 'room', 'guest', 'check_in', 'check_out', 'status', 'total_amount')
	list_filter = ('tenant', 'status', 'room__room_type')
	search_fields = ('id', 'room__room_number', 'guest__first_name', 'guest__last_name')

