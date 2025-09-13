from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from api.models.user import Tenant
from restaurant.models import MenuCategory, MenuItem, Table, Order, OrderItem
from api.serializers import MenuCategorySerializer, MenuItemSerializer, TableSerializer, OrderSerializer, OrderItemSerializer


class MenuCategoryListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
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
	permission_classes = [IsAuthenticated]
	serializer_class = MenuCategorySerializer
	
	def get_queryset(self):
		return MenuCategory.objects.filter(tenant=self.request.user.userprofile.tenant)


class MenuItemListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
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
	permission_classes = [IsAuthenticated]
	serializer_class = MenuItemSerializer
	
	def get_queryset(self):
		return MenuItem.objects.filter(tenant=self.request.user.userprofile.tenant)


class TableListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = TableSerializer
	
	def get_queryset(self):
		return Table.objects.filter(tenant=self.request.user.userprofile.tenant)
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class TableDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = TableSerializer
	
	def get_queryset(self):
		return Table.objects.filter(tenant=self.request.user.userprofile.tenant)


class OrderListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = OrderSerializer
	
	def get_queryset(self):
		queryset = Order.objects.filter(tenant=self.request.user.userprofile.tenant)
		status = self.request.query_params.get('status')
		if status:
			queryset = queryset.filter(status=status)
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = OrderSerializer
	
	def get_queryset(self):
		return Order.objects.filter(tenant=self.request.user.userprofile.tenant)


class OrderItemListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = OrderItemSerializer
	
	def get_queryset(self):
		return OrderItem.objects.filter(tenant=self.request.user.userprofile.tenant)
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class OrderItemDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = OrderItemSerializer
	
	def get_queryset(self):
		return OrderItem.objects.filter(tenant=self.request.user.userprofile.tenant)
