from django.contrib import admin
from .models import MenuCategory, MenuItem, Table, Order, OrderItem


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'tenant')
	list_filter = ('tenant',)
	search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
	list_display = ('name', 'tenant', 'category', 'price', 'is_available')
	list_filter = ('tenant', 'category', 'is_available')
	search_fields = ('name',)


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
	list_display = ('number', 'tenant', 'seats')
	list_filter = ('tenant',)
	search_fields = ('number',)


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('id', 'tenant', 'table', 'customer_name', 'status', 'total_amount', 'created_at')
	list_filter = ('tenant', 'status')
	search_fields = ('id', 'customer_name')
	inlines = [OrderItemInline]

