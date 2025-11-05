from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from api.models.permissions import HasFeaturePermissionFactory
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from datetime import datetime, timedelta
from api.models.user import Tenant
from restaurant.models import MenuCategory, MenuItem, Table, Order, OrderItem
from api.serializers import MenuCategorySerializer, MenuItemSerializer, TableSerializer, OrderSerializer, OrderItemSerializer


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
		queryset = Order.objects.filter(tenant=self.request.user.userprofile.tenant)
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
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = OrderSerializer
	
	def get_queryset(self):
		return Order.objects.filter(tenant=self.request.user.userprofile.tenant)


class OrderItemListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = OrderItemSerializer
	
	def get_queryset(self):
		return OrderItem.objects.filter(tenant=self.request.user.userprofile.tenant)
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class OrderItemDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]
	serializer_class = OrderItemSerializer
	
	def get_queryset(self):
		return OrderItem.objects.filter(tenant=self.request.user.userprofile.tenant)


class OrderServeView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

	def post(self, request, pk):
		try:
			order = Order.objects.get(id=pk, tenant=request.user.userprofile.tenant)
			order.status = 'served'
			order.save()
			return Response({'message': 'Order marked as served', 'status': order.status})
		except Order.DoesNotExist:
			return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


class OrderMarkPaidView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant')]

	def post(self, request, pk):
		try:
			order = Order.objects.get(id=pk, tenant=request.user.userprofile.tenant)
			order.status = 'paid'
			order.save()
			return Response({'message': 'Order marked as paid', 'status': order.status})
		except Order.DoesNotExist:
			return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


class RestaurantAnalyticsView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('restaurant'), HasFeaturePermissionFactory('analytics')]

	def get(self, request):
		tenant = request.user.userprofile.tenant
		today = timezone.now().date()
		thirty_days_ago = today - timedelta(days=30)
		
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
		
		# Popular items (top 5) - calculate line_total as quantity * price
		popular_items = OrderItem.objects.filter(
			tenant=tenant,
			order__created_at__date__gte=thirty_days_ago
		).annotate(
			line_total=F('quantity') * F('price')
		).values(
			'menu_item__name'
		).annotate(
			total_quantity=Sum('quantity'),
			total_revenue=Sum('line_total')
		).order_by('-total_quantity')[:5]
		
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
				'recent_30_days': recent_orders
			},
			'revenue': {
				'total_30_days': float(revenue_stats['total_revenue'] or 0),
				'today': float(today_revenue['total'] or 0),
				'average_order_value': float(revenue_stats['avg_order_value'] or 0),
				'order_count': revenue_stats['order_count'] or 0
			},
			'popular_items': list(popular_items),
			'top_items': list(popular_items)  # Alias for compatibility
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
