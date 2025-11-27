from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from api.models.permissions import HasFeaturePermissionFactory
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from datetime import datetime, timedelta
from api.models.user import Tenant, UserProfile
from restaurant.models import MenuCategory, MenuItem, Table, Order, OrderItem, ExternalAPIIntegration, MenuSyncLog
from api.serializers import (
	MenuCategorySerializer, MenuItemSerializer, TableSerializer, OrderSerializer, OrderItemSerializer,
	ExternalAPIIntegrationSerializer, MenuSyncLogSerializer,
	PublicMenuItemSerializer, PublicMenuCategorySerializer, PublicOrderCreateSerializer
)
import requests
import logging
from decimal import Decimal
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from io import BytesIO

logger = logging.getLogger(__name__)


class MenuCategoryListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = MenuCategorySerializer
	
	def get_queryset(self):
		queryset = MenuCategory.objects.filter(tenant=self.request.user.userprofile.tenant)
		search = self.request.query_params.get('search')
		if search:
			queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class MenuCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = MenuCategorySerializer
	
	def get_queryset(self):
		return MenuCategory.objects.filter(tenant=self.request.user.userprofile.tenant)


class MenuItemListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = MenuItemSerializer
	
	def get_queryset(self):
		queryset = MenuItem.objects.filter(tenant=self.request.user.userprofile.tenant)
		category = self.request.query_params.get('category')
		available = self.request.query_params.get('available')
		if category:
			queryset = queryset.filter(category_id=category)
		if available is not None:
			if available.lower() == 'true':
				queryset = queryset.filter(is_available=True)
			elif available.lower() == 'false':
				queryset = queryset.filter(is_available=False)
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class MenuItemDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = MenuItemSerializer
	
	def get_queryset(self):
		return MenuItem.objects.filter(tenant=self.request.user.userprofile.tenant)


class TableListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = TableSerializer
	
	def get_queryset(self):
		return Table.objects.filter(tenant=self.request.user.userprofile.tenant)
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class TableDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = TableSerializer
	
	def get_queryset(self):
		return Table.objects.filter(tenant=self.request.user.userprofile.tenant)


class OrderListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = OrderSerializer
	
	def get_queryset(self):
		queryset = Order.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
			'table', 'tenant'
		).prefetch_related('items', 'items__menu_item', 'items__menu_item__category')
		status_param = self.request.query_params.get('status')
		search = self.request.query_params.get('search')
		date_from = self.request.query_params.get('date_from')
		date_to = self.request.query_params.get('date_to')
		table_id = self.request.query_params.get('table')
		
		if status_param:
			queryset = queryset.filter(status=status_param)
		if search:
			queryset = queryset.filter(
				Q(customer_name__icontains=search) |
				Q(table__number__icontains=search)
			)
		if table_id:
			queryset = queryset.filter(table_id=table_id)
		if date_from:
			try:
				date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
				queryset = queryset.filter(created_at__date__gte=date_from_obj)
			except:
				pass
		if date_to:
			try:
				date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
				queryset = queryset.filter(created_at__date__lte=date_to_obj)
			except:
				pass
		return queryset
	
	def get_serializer_context(self):
		context = super().get_serializer_context()
		context['items'] = self.request.data.get('items', [])
		return context
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = OrderSerializer
	
	def get_queryset(self):
		return Order.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
			'table', 'tenant'
		).prefetch_related('items', 'items__menu_item', 'items__menu_item__category')


class OrderItemListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = OrderItemSerializer
	
	def get_queryset(self):
		return OrderItem.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
			'order', 'menu_item', 'menu_item__category'
		)
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class OrderItemDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = OrderItemSerializer
	
	def get_queryset(self):
		return OrderItem.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
			'order', 'menu_item', 'menu_item__category'
		)


class OrderServeView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

	def post(self, request, pk):
		try:
			order = Order.objects.select_related('table', 'tenant').get(id=pk, tenant=request.user.userprofile.tenant)
			order.status = 'served'
			order.save()
			return Response({'message': 'Order marked as served', 'status': order.status})
		except Order.DoesNotExist:
			return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


class OrderMarkPaidView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

	def post(self, request, pk):
		try:
			order = Order.objects.select_related('table', 'tenant').get(id=pk, tenant=request.user.userprofile.tenant)
			order.status = 'paid'
			order.save()
			return Response({'message': 'Order marked as paid', 'status': order.status})
		except Order.DoesNotExist:
			return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


class RestaurantOrderInvoiceView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

	def get(self, request, pk):
		try:
			profile = UserProfile._default_manager.get(user=request.user)
			tenant = profile.tenant
			order = Order.objects.select_related('table').prefetch_related('items', 'items__menu_item').get(id=pk, tenant=tenant)
		except UserProfile.DoesNotExist:
			return Response({'error': 'User profile not found.'}, status=status.HTTP_403_FORBIDDEN)
		except Order.DoesNotExist:
			return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

		buffer = BytesIO()
		p = canvas.Canvas(buffer, pagesize=A4)
		width, height = A4
		margin = 25 * mm

		p.setFont('Helvetica-Bold', 18)
		p.drawString(margin, height - margin, 'Zenith Restaurant Invoice')
		p.setFont('Helvetica', 10)
		p.drawRightString(width - margin, height - margin + 4, f"Order #: RST-{order.id:06d}")

		y = height - margin - 30
		p.setFont('Helvetica-Bold', 12)
		p.drawString(margin, y, 'Customer & Table')
		y -= 14
		p.setFont('Helvetica', 10)
		p.drawString(margin, y, f"Customer: {order.customer_name or 'Walk-in'}")
		y -= 12
		p.drawString(margin, y, f"Table: {order.table.number if order.table else 'N/A'}")
		y -= 12
		p.drawString(margin, y, f"Status: {order.status or 'open'}")
		y -= 12
		p.drawString(margin, y, f"Created: {order.created_at.strftime('%d-%m-%Y %I:%M %p') if order.created_at else 'N/A'}")
		y -= 18

		p.setFont('Helvetica-Bold', 12)
		p.drawString(margin, y, 'Order Items')
		y -= 14
		p.setFont('Helvetica-Bold', 10)
		p.drawString(margin, y, 'Item')
		p.drawString(margin + 230, y, 'Qty')
		p.drawRightString(width - margin - 60, y, 'Price')
		p.drawRightString(width - margin, y, 'Amount')
		y -= 12
		p.setLineWidth(0.5)
		p.line(margin, y, width - margin, y)
		y -= 8

		p.setFont('Helvetica', 10)
		subtotal = Decimal('0.00')
		for item in order.items.all():
			if y < margin + 60:
				p.showPage()
				y = height - margin - 20
			name = item.menu_item.name if item.menu_item else item.menu_item_name or 'Item'
			quantity = item.quantity or 0
			price = Decimal(item.price or 0)
			line_total = price * quantity
			subtotal += line_total

			p.drawString(margin, y, name[:40])
			p.drawString(margin + 230, y, str(quantity))
			p.drawRightString(width - margin - 60, y, f"₹{price:.2f}")
			p.drawRightString(width - margin, y, f"₹{line_total:.2f}")
			y -= 12

		p.setFont('Helvetica', 11)
		p.drawString(margin, y - 10, f"Subtotal: ₹{subtotal:.2f}")
		gst = subtotal * Decimal('0.18')
		p.drawString(margin, y - 24, f"GST (18%): ₹{gst:.2f}")
		total = subtotal + gst
		p.setFont('Helvetica-Bold', 12)
		p.drawString(margin, y - 40, f"Total: ₹{total:.2f}")
		y -= 60

		p.setFont('Helvetica', 9)
		p.drawString(margin, y, 'Thank you for dining with Zenith Restaurant. Contact us for corrections.')
		p.drawRightString(width - margin, y, f"Generated: {timezone.now().strftime('%d-%m-%Y %I:%M %p')}")

		p.showPage()
		p.save()
		buffer.seek(0)

		response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename="restaurant_invoice_{order.id}.pdf"'
		return response


class RestaurantAnalyticsView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant'), HasFeaturePermissionFactory('analytics')]

	def get(self, request):
		tenant = request.user.userprofile.tenant
		today = timezone.now().date()
		thirty_days_ago = today - timedelta(days=30)
		seven_days_ago = today - timedelta(days=7)
		
		# Menu statistics
		total_items = MenuItem.objects.filter(tenant=tenant).count()
		available_items = MenuItem.objects.filter(tenant=tenant, is_available=True).count()
		unavailable_items = total_items - available_items
		total_categories = MenuCategory.objects.filter(tenant=tenant).count()
		
		# Table statistics
		total_tables = Table.objects.filter(tenant=tenant).count()
		occupied_tables = Order.objects.filter(tenant=tenant, status__in=['open', 'served']).values('table').distinct().count()
		utilization_rate = round((occupied_tables / total_tables * 100) if total_tables > 0 else 0, 2)
		
		# Order statistics
		total_orders = Order.objects.filter(tenant=tenant).count()
		open_orders = Order.objects.filter(tenant=tenant, status='open').count()
		served_orders = Order.objects.filter(tenant=tenant, status='served').count()
		paid_orders = Order.objects.filter(tenant=tenant, status='paid').count()
		cancelled_orders = Order.objects.filter(tenant=tenant, status='cancelled').count()
		recent_orders = Order.objects.filter(tenant=tenant, created_at__date__gte=thirty_days_ago).count()
		
		# Order type analytics (NEW)
		order_type_stats = Order.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago
		).values('order_type').annotate(
			count=Count('id'),
			revenue=Sum('total_amount', filter=Q(status='paid'))
		)
		order_type_breakdown = {ot['order_type']: {
			'count': ot['count'],
			'revenue': float(ot['revenue'] or 0)
		} for ot in order_type_stats}
		
		# Revenue statistics
		revenue_stats = Order.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago,
			status='paid'
		).aggregate(
			total_revenue=Sum('total_amount'),
			avg_order_value=Avg('total_amount'),
			order_count=Count('id')
		)
		
		# Today's revenue
		today_revenue = Order.objects.filter(
			tenant=tenant,
			created_at__date=today,
			status='paid'
		).aggregate(total=Sum('total_amount'))
		
		# Weekly revenue comparison (NEW)
		this_week_revenue = Order.objects.filter(
			tenant=tenant,
			created_at__date__gte=seven_days_ago,
			status='paid'
		).aggregate(total=Sum('total_amount'))
		last_week_revenue = Order.objects.filter(
			tenant=tenant,
			created_at__date__gte=seven_days_ago - timedelta(days=7),
			created_at__date__lt=seven_days_ago,
			status='paid'
		).aggregate(total=Sum('total_amount'))
		week_growth = ((float(this_week_revenue['total'] or 0) - float(last_week_revenue['total'] or 0)) / float(last_week_revenue['total'] or 1) * 100) if last_week_revenue['total'] else 0
		
		# Daily revenue trend (last 7 days) (NEW)
		daily_revenue = []
		for i in range(7):
			date = today - timedelta(days=i)
			day_revenue = Order.objects.filter(
				tenant=tenant,
				created_at__date=date,
				status='paid'
			).aggregate(total=Sum('total_amount'))
			daily_revenue.append({
				'date': date.strftime('%Y-%m-%d'),
				'day': date.strftime('%a'),
				'revenue': float(day_revenue['total'] or 0),
				'orders': Order.objects.filter(tenant=tenant, created_at__date=date, status='paid').count()
			})
		daily_revenue.reverse()
		
		# Peak hours analysis (NEW)
		from django.db.models.functions import ExtractHour
		peak_hours = Order.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago,
			status='paid'
		).annotate(
			hour=ExtractHour('created_at')
		).values('hour').annotate(
			order_count=Count('id'),
			revenue=Sum('total_amount')
		).order_by('-order_count')[:5]
		
		# Popular items (top 10) - calculate line_total as quantity * price
		popular_items = OrderItem.objects.filter(
			tenant=tenant,
			order__created_at__date__gte=thirty_days_ago
		).annotate(
			line_total=F('quantity') * F('price')
		).values(
			'menu_item__name',
			'menu_item__id'
		).annotate(
			total_quantity=Sum('quantity'),
			total_revenue=Sum('line_total'),
			order_count=Count('order', distinct=True)
		).order_by('-total_quantity')[:10]
		
		# Customer analytics (NEW)
		unique_customers = Order.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago
		).exclude(customer_phone='').values('customer_phone').distinct().count()
		
		repeat_customers = Order.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago
		).exclude(customer_phone='').values('customer_phone').annotate(
			order_count=Count('id')
		).filter(order_count__gt=1).count()
		
		# Average order processing time (NEW) - for completed orders
		completed_orders = Order.objects.filter(
			tenant=tenant,
			status='paid',
			created_at__date__gte=thirty_days_ago
		).exclude(updated_at__isnull=True)
		
		avg_processing_time = None
		if completed_orders.exists():
			processing_times = []
			for order in completed_orders[:100]:  # Sample first 100
				if order.updated_at and order.created_at:
					delta = order.updated_at - order.created_at
					processing_times.append(delta.total_seconds() / 60)  # in minutes
			if processing_times:
				avg_processing_time = round(sum(processing_times) / len(processing_times), 2)
		
		# Cancellation rate (NEW)
		cancellation_rate = (cancelled_orders / total_orders * 100) if total_orders > 0 else 0
		
		# Category performance (NEW)
		category_performance = OrderItem.objects.filter(
			tenant=tenant,
			order__created_at__date__gte=thirty_days_ago
		).values(
			'menu_item__category__name'
		).annotate(
			total_revenue=Sum(F('quantity') * F('price')),
			total_quantity=Sum('quantity'),
			order_count=Count('order', distinct=True)
		).order_by('-total_revenue')[:5]
		
		return Response({
			'menu': {
				'total_items': total_items,
				'available_items': available_items,
				'unavailable_items': unavailable_items,
				'total_categories': total_categories
			},
			'tables': {
				'total': total_tables,
				'occupied': occupied_tables,
				'utilization_rate': utilization_rate
			},
			'orders': {
				'total': total_orders,
				'open': open_orders,
				'served': served_orders,
				'paid': paid_orders,
				'cancelled': cancelled_orders,
				'recent_30_days': recent_orders,
				'cancellation_rate': round(cancellation_rate, 2)
			},
			'order_types': order_type_breakdown,  # NEW
			'revenue': {
				'total_30_days': float(revenue_stats['total_revenue'] or 0),
				'today': float(today_revenue['total'] or 0),
				'this_week': float(this_week_revenue['total'] or 0),  # NEW
				'last_week': float(last_week_revenue['total'] or 0),  # NEW
				'week_growth_percent': round(week_growth, 2),  # NEW
				'average_order_value': float(revenue_stats['avg_order_value'] or 0),
				'order_count': revenue_stats['order_count'] or 0
			},
			'daily_trends': daily_revenue,  # NEW
			'peak_hours': list(peak_hours),  # NEW
			'popular_items': list(popular_items),
			'top_items': list(popular_items),  # Alias for compatibility
			'category_performance': list(category_performance),  # NEW
			'customers': {  # NEW
				'unique_customers_30_days': unique_customers,
				'repeat_customers': repeat_customers,
				'retention_rate': round((repeat_customers / unique_customers * 100) if unique_customers > 0 else 0, 2)
			},
			'performance': {  # NEW
				'avg_processing_time_minutes': avg_processing_time,
				'cancellation_rate': round(cancellation_rate, 2)
			}
		})


class OrderBulkDeleteView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

	def post(self, request):
		order_ids = request.data.get('ids', [])
		if not order_ids:
			return Response({'error': 'No order IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
		
		tenant = request.user.userprofile.tenant
		deleted_count = Order.objects.filter(id__in=order_ids, tenant=tenant).delete()[0]
		return Response({'message': f'{deleted_count} order(s) deleted successfully'})


class OrderBulkStatusUpdateView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

	def post(self, request):
		order_ids = request.data.get('ids', [])
		new_status = request.data.get('status')
		
		if not order_ids:
			return Response({'error': 'No order IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
		if not new_status:
			return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
		if new_status not in ['open', 'served', 'paid', 'cancelled']:
			return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
		
		tenant = request.user.userprofile.tenant
		updated_count = Order.objects.filter(id__in=order_ids, tenant=tenant).update(status=new_status)
		return Response({'message': f'{updated_count} order(s) updated successfully'})


# ==================== External API Integration Views ====================

class ExternalAPIIntegrationListCreateView(generics.ListCreateAPIView):
	"""List and create external API integrations"""
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = ExternalAPIIntegrationSerializer
	
	def get_queryset(self):
		return ExternalAPIIntegration.objects.filter(tenant=self.request.user.userprofile.tenant)
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class ExternalAPIIntegrationDetailView(generics.RetrieveUpdateDestroyAPIView):
	"""Retrieve, update, or delete external API integration"""
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = ExternalAPIIntegrationSerializer
	
	def get_queryset(self):
		return ExternalAPIIntegration.objects.filter(tenant=self.request.user.userprofile.tenant)


class MenuSyncView(APIView):
	"""Sync menu from external API"""
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	
	def post(self, request, integration_id):
		"""Manually trigger menu sync"""
		try:
			integration = ExternalAPIIntegration.objects.get(
				id=integration_id,
				tenant=request.user.userprofile.tenant,
				is_active=True
			)
		except ExternalAPIIntegration.DoesNotExist:
			return Response({'error': 'Integration not found or inactive'}, status=status.HTTP_404_NOT_FOUND)
		
		try:
			result = sync_menu_from_api(integration)
			return Response({
				'message': 'Menu synced successfully',
				'result': result
			})
		except Exception as e:
			logger.error(f"Menu sync error: {str(e)}", exc_info=True)
			return Response({
				'error': f'Menu sync failed: {str(e)}'
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MenuSyncLogListView(generics.ListAPIView):
	"""List menu sync logs"""
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = MenuSyncLogSerializer
	
	def get_queryset(self):
		integration_id = self.request.query_params.get('integration')
		queryset = MenuSyncLog.objects.filter(
			integration__tenant=self.request.user.userprofile.tenant
		).select_related('integration').order_by('-synced_at')
		
		if integration_id:
			queryset = queryset.filter(integration_id=integration_id)
		
		return queryset[:50]  # Limit to last 50 logs


# ==================== Public API Views (Cloud Kitchen) ====================

class PublicMenuView(APIView):
	"""Public endpoint to view menu (no authentication required)"""
	permission_classes = [AllowAny]
	
	def get(self, request):
		"""Get public menu for a tenant"""
		tenant_id = request.query_params.get('tenant_id')
		if not tenant_id:
			return Response({'error': 'tenant_id is required'}, status=status.HTTP_400_BAD_REQUEST)
		
		try:
			tenant = Tenant.objects.get(id=tenant_id)
		except Tenant.DoesNotExist:
			return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
		
		# Get all categories with available items
		categories = MenuCategory.objects.filter(tenant=tenant).prefetch_related(
			'items'
		)
		
		# Filter only available items
		menu_data = []
		for category in categories:
			items = category.items.filter(is_available=True)
			if items.exists():
				menu_data.append({
					'id': category.id,
					'name': category.name,
					'description': category.description,
					'items': PublicMenuItemSerializer(items, many=True).data
				})
		
		return Response({
			'restaurant_name': tenant.name,
			'menu': menu_data
		})


class PublicOrderCreateView(APIView):
	"""Public endpoint for customers to place orders (cloud kitchen)"""
	permission_classes = [AllowAny]
	
	def post(self, request):
		"""Create a new order from public API"""
		tenant_id = request.data.get('tenant_id')
		if not tenant_id:
			return Response({'error': 'tenant_id is required'}, status=status.HTTP_400_BAD_REQUEST)
		
		try:
			tenant = Tenant.objects.get(id=tenant_id)
		except Tenant.DoesNotExist:
			return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
		
		# Validate order data
		serializer = PublicOrderCreateSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		
		data = serializer.validated_data
		
		# Create order
		order = Order.objects.create(
			tenant=tenant,
			customer_name=data['customer_name'],
			customer_phone=data['customer_phone'],
			customer_email=data.get('customer_email', ''),
			delivery_address=data['delivery_address'],
			order_type=data.get('order_type', 'cloud_kitchen'),
			notes=data.get('notes', ''),
			status='open'
		)
		
		# Create order items
		total_amount = Decimal('0.00')
		for item_data in data['items']:
			try:
				menu_item = MenuItem.objects.select_related('category').get(
					id=item_data.get('menu_item_id'),
					tenant=tenant,
					is_available=True
				)
				quantity = int(item_data.get('quantity', 1))
				price = menu_item.price
				
				OrderItem.objects.create(
					tenant=tenant,
					order=order,
					menu_item=menu_item,
					quantity=quantity,
					price=price
				)
				
				total_amount += price * quantity
			except MenuItem.DoesNotExist:
				return Response({
					'error': f"Menu item {item_data.get('menu_item_id')} not found or unavailable"
				}, status=status.HTTP_400_BAD_REQUEST)
			except (ValueError, KeyError) as e:
				return Response({
					'error': f"Invalid item data: {str(e)}"
				}, status=status.HTTP_400_BAD_REQUEST)
		
		order.total_amount = total_amount
		order.save()
		
		# Send webhook if configured
		send_order_webhook(order)
		
		# Generate payment link if Razorpay is configured
		payment_data = None
		if tenant.has_razorpay_configured():
			try:
				import razorpay
				from django.utils import timezone
				client = razorpay.Client(auth=(tenant.razorpay_key_id, tenant.razorpay_key_secret))
				amount = float(total_amount)
				order_data = {
					'amount': int(amount * 100),
					'currency': 'INR',
					'payment_capture': 1,
					'receipt': f"ORD-{order.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
					'notes': {
						'sector': 'restaurant',
						'reference_id': str(order.id),
						'customer_name': order.customer_name,
						'order_type': order.order_type,
						'tenant_id': str(tenant.id)
					}
				}
				razorpay_order = client.order.create(data=order_data)
				
				payment_data = {
					'order_id': razorpay_order['id'],
					'amount': razorpay_order['amount'],
					'currency': razorpay_order['currency'],
					'key_id': tenant.razorpay_key_id,
					'receipt': razorpay_order.get('receipt'),
					'payment_url': f"https://checkout.razorpay.com/v1/checkout.js?key={tenant.razorpay_key_id}&order_id={razorpay_order['id']}",
					'checkout_data': {
						'key': tenant.razorpay_key_id,
						'amount': razorpay_order['amount'],
						'currency': razorpay_order['currency'],
						'order_id': razorpay_order['id'],
						'name': tenant.name,
						'description': f"Order #{order.id}",
						'prefill': {
							'name': order.customer_name,
							'email': order.customer_email or '',
							'contact': order.customer_phone or ''
						}
					}
				}
			except Exception as e:
				logger.error(f"Failed to generate payment link for order {order.id}: {str(e)}")
				# Continue without payment link
		
		response_data = {
			'message': 'Order placed successfully',
			'order_id': order.id,
			'order_number': f"ORD-{order.id:06d}",
			'total_amount': str(total_amount),
			'status': order.status
		}
		
		if payment_data:
			response_data['payment'] = payment_data
			response_data['payment_link'] = payment_data['payment_url']
		
		return Response(response_data, status=status.HTTP_201_CREATED)


class PublicOrderStatusView(APIView):
	"""Public endpoint to check order status"""
	permission_classes = [AllowAny]
	
	def get(self, request, order_id):
		"""Get order status by order ID"""
		phone = request.query_params.get('phone')  # Optional phone verification
		
		try:
			order = Order.objects.get(id=order_id)
			if phone and order.customer_phone != phone:
				return Response({'error': 'Invalid order or phone number'}, status=status.HTTP_403_FORBIDDEN)
			
			return Response({
				'order_id': order.id,
				'order_number': f"ORD-{order.id:06d}",
				'status': order.status,
				'total_amount': str(order.total_amount),
				'created_at': order.created_at,
				'items': OrderItemSerializer(order.items.all(), many=True).data
			})
		except Order.DoesNotExist:
			return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


# ==================== Helper Functions ====================

def sync_menu_from_api(integration):
	"""Sync menu items from external API"""
	items_created = 0
	items_updated = 0
	items_failed = 0
	error_message = ''
	
	try:
		# Build API URL
		api_url = integration.api_url.rstrip('/') + integration.menu_endpoint
		
		# Prepare headers
		headers = {
			'Content-Type': 'application/json',
		}
		if integration.api_key:
			headers['Authorization'] = f"Bearer {integration.api_key}"
			# Or use API key in header based on API type
			if integration.api_type == 'zomato':
				headers['user-key'] = integration.api_key
			elif integration.api_type == 'swiggy':
				headers['x-api-key'] = integration.api_key
		
		# Make API request
		response = requests.get(api_url, headers=headers, timeout=30)
		response.raise_for_status()
		
		menu_data = response.json()
		
		# Parse menu data based on API type
		if integration.api_type == 'custom':
			# Custom API - use settings to map fields
			category_map = integration.settings.get('category_map', {})
			item_map = integration.settings.get('item_map', {})
			categories = menu_data.get('categories', menu_data.get('data', []))
		else:
			# Standard format: {categories: [{name, items: [{name, price, ...}]}]}
			categories = menu_data.get('categories', menu_data.get('data', []))
			category_map = {'name': 'name', 'description': 'description'}
			item_map = {'name': 'name', 'price': 'price', 'available': 'is_available'}
		
		# Sync categories and items
		for cat_data in categories:
			cat_name = cat_data.get(category_map.get('name', 'name'), '')
			cat_desc = cat_data.get(category_map.get('description', 'description'), '')
			
			# Get or create category
			category, created = MenuCategory.objects.get_or_create(
				tenant=integration.tenant,
				name=cat_name,
				defaults={'description': cat_desc}
			)
			
			# Sync items
			items = cat_data.get('items', cat_data.get('menu_items', []))
			for item_data in items:
				try:
					item_name = item_data.get(item_map.get('name', 'name'), '')
					item_price = Decimal(str(item_data.get(item_map.get('price', 'price'), 0)))
					is_available = item_data.get(item_map.get('available', 'is_available'), True)
					
					# Get or create menu item
					menu_item, created = MenuItem.objects.get_or_create(
						tenant=integration.tenant,
						category=category,
						name=item_name,
						defaults={
							'price': item_price,
							'is_available': is_available
						}
					)
					
					if not created:
						# Update existing item
						menu_item.price = item_price
						menu_item.is_available = is_available
						menu_item.save()
						items_updated += 1
					else:
						items_created += 1
				except Exception as e:
					items_failed += 1
					logger.error(f"Error syncing item: {str(e)}")
		
		# Update last synced time
		integration.last_synced_at = timezone.now()
		integration.save()
		
		# Create sync log
		status = 'success' if items_failed == 0 else ('partial' if items_created + items_updated > 0 else 'failed')
		MenuSyncLog.objects.create(
			integration=integration,
			status=status,
			items_synced=items_created + items_updated,
			items_created=items_created,
			items_updated=items_updated,
			items_failed=items_failed,
			error_message=error_message if items_failed > 0 else ''
		)
		
		return {
			'status': status,
			'items_created': items_created,
			'items_updated': items_updated,
			'items_failed': items_failed
		}
		
	except requests.RequestException as e:
		error_message = f"API request failed: {str(e)}"
		logger.error(error_message)
		MenuSyncLog.objects.create(
			integration=integration,
			status='failed',
			items_synced=0,
			items_created=0,
			items_updated=0,
			items_failed=0,
			error_message=error_message
		)
		raise Exception(error_message)
	except Exception as e:
		error_message = f"Sync error: {str(e)}"
		logger.error(error_message, exc_info=True)
		MenuSyncLog.objects.create(
			integration=integration,
			status='failed',
			items_synced=0,
			items_created=0,
			items_updated=0,
			items_failed=0,
			error_message=error_message
		)
		raise


def send_order_webhook(order):
	"""Send order webhook to external API if configured"""
	integrations = ExternalAPIIntegration.objects.filter(
		tenant=order.tenant,
		is_active=True,
		webhook_url__isnull=False
	).exclude(webhook_url='')
	
	for integration in integrations:
		try:
			headers = {
				'Content-Type': 'application/json',
			}
			if integration.webhook_secret:
				headers['X-Webhook-Secret'] = integration.webhook_secret
			
			payload = {
				'order_id': order.id,
				'order_number': f"ORD-{order.id:06d}",
				'status': order.status,
				'customer_name': order.customer_name,
				'customer_phone': order.customer_phone,
				'customer_email': order.customer_email,
				'delivery_address': order.delivery_address,
				'order_type': order.order_type,
				'total_amount': str(order.total_amount),
				'items': [
					{
						'menu_item_id': item.menu_item.id,
						'name': item.menu_item.name,
						'quantity': item.quantity,
						'price': str(item.price)
					}
					for item in order.items.all()
				],
				'created_at': order.created_at.isoformat()
			}
			
			response = requests.post(
				integration.webhook_url,
				json=payload,
				headers=headers,
				timeout=10
			)
			response.raise_for_status()
			logger.info(f"Webhook sent successfully for order {order.id} to {integration.name}")
		except Exception as e:
			logger.error(f"Webhook failed for order {order.id}: {str(e)}")
