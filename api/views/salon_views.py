from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from api.models.permissions import HasFeaturePermissionFactory
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from api.models.user import Tenant
from salon.models import ServiceCategory, Service, Stylist, Appointment
from api.serializers import ServiceCategorySerializer, ServiceSerializer, StylistSerializer, AppointmentSerializer


class ServiceCategoryListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]
	serializer_class = ServiceCategorySerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		queryset = ServiceCategory.objects.filter(tenant=self.request.user.userprofile.tenant)
		search = self.request.query_params.get('search')
		if search:
			queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
		return queryset
	
	def create(self, request, *args, **kwargs):
		print(f"ServiceCategoryListCreateView.create called")
		print(f"Request data: {request.data}")
		print(f"Request user: {request.user}")
		print(f"Request user profile: {request.user.userprofile}")
		print(f"Request user tenant: {request.user.userprofile.tenant}")
		try:
			return super().create(request, *args, **kwargs)
		except Exception as e:
			print(f"Error in create method: {e}")
			print(f"Error type: {type(e)}")
			raise
	
	def perform_create(self, serializer):
		try:
			tenant = self.request.user.userprofile.tenant
			print(f"Creating salon service category for tenant: {tenant}")
			print(f"Serializer data: {serializer.validated_data}")
			serializer.save(tenant=tenant)
			print("Category created successfully")
		except Exception as e:
			print(f"Error in perform_create: {e}")
			raise


class ServiceCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]
	serializer_class = ServiceCategorySerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		return ServiceCategory.objects.filter(tenant=self.request.user.userprofile.tenant)


class ServiceListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]
	serializer_class = ServiceSerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		queryset = Service.objects.filter(tenant=self.request.user.userprofile.tenant)
		category = self.request.query_params.get('category')
		active = self.request.query_params.get('active')
		if category:
			queryset = queryset.filter(category_id=category)
		if active is not None:
			if active.lower() == 'true':
				queryset = queryset.filter(is_active=True)
			elif active.lower() == 'false':
				queryset = queryset.filter(is_active=False)
		return queryset
	
	def get_serializer_context(self):
		context = super().get_serializer_context()
		context['request'] = self.request
		return context
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class ServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]
	serializer_class = ServiceSerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		return Service.objects.filter(tenant=self.request.user.userprofile.tenant)


class StylistListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]
	serializer_class = StylistSerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		queryset = Stylist.objects.filter(tenant=self.request.user.userprofile.tenant)
		search = self.request.query_params.get('search')
		if search:
			queryset = queryset.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(phone__icontains=search) | Q(email__icontains=search))
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class StylistDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]
	serializer_class = StylistSerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		return Stylist.objects.filter(tenant=self.request.user.userprofile.tenant)


class AppointmentListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]
	serializer_class = AppointmentSerializer
	
	def get_queryset(self):
		queryset = Appointment.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
			'service', 'stylist', 'service__category'
		)
		status_param = self.request.query_params.get('status')
		stylist = self.request.query_params.get('stylist')
		service = self.request.query_params.get('service')
		search = self.request.query_params.get('search')
		date = self.request.query_params.get('date')  # YYYY-MM-DD
		date_from = self.request.query_params.get('date_from')
		date_to = self.request.query_params.get('date_to')
		
		if status_param:
			queryset = queryset.filter(status=status_param)
		if stylist:
			queryset = queryset.filter(stylist_id=stylist)
		if service:
			queryset = queryset.filter(service_id=service)
		if search:
			queryset = queryset.filter(
				Q(customer_name__icontains=search) |
				Q(customer_phone__icontains=search) |
				Q(service__name__icontains=search) |
				Q(stylist__first_name__icontains=search) |
				Q(stylist__last_name__icontains=search)
			)
		if date:
			try:
				from datetime import datetime
				date_obj = datetime.strptime(date, '%Y-%m-%d').date()
				queryset = queryset.filter(start_time__date=date_obj)
			except Exception:
				pass
		if date_from:
			try:
				date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
				queryset = queryset.filter(start_time__date__gte=date_from_obj)
			except:
				pass
		if date_to:
			try:
				date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
				queryset = queryset.filter(start_time__date__lte=date_to_obj)
			except:
				pass
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]
	serializer_class = AppointmentSerializer
	
	def get_queryset(self):
		return Appointment.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
			'service', 'stylist', 'service__category'
		)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone


class AppointmentCheckInView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]

	def post(self, request, pk):
		try:
			appt = Appointment.objects.select_related('service', 'stylist').get(id=pk, tenant=request.user.userprofile.tenant)
			appt.status = 'in_progress'
			appt.save()
			return Response({'message': 'Appointment checked in', 'status': appt.status})
		except Appointment.DoesNotExist:
			return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)


class AppointmentCompleteView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]

	def post(self, request, pk):
		try:
			appt = Appointment.objects.select_related('service', 'stylist').get(id=pk, tenant=request.user.userprofile.tenant)
			appt.status = 'completed'
			if not appt.end_time:
				appt.end_time = timezone.now()
			appt.save()
			return Response({'message': 'Appointment completed', 'status': appt.status})
		except Appointment.DoesNotExist:
			return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)


class AppointmentCancelView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]

	def post(self, request, pk):
		try:
			appt = Appointment.objects.select_related('service', 'stylist').get(id=pk, tenant=request.user.userprofile.tenant)
			appt.status = 'cancelled'
			appt.save()
			return Response({'message': 'Appointment cancelled', 'status': appt.status})
		except Appointment.DoesNotExist:
			return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)


class SalonAnalyticsView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon'), HasFeaturePermissionFactory('analytics')]

	def get(self, request):
		tenant = request.user.userprofile.tenant
		today = timezone.now().date()
		thirty_days_ago = today - timedelta(days=30)
		
		# Service statistics
		total_services = Service.objects.filter(tenant=tenant).count()
		active_services = Service.objects.filter(tenant=tenant, is_active=True).count()
		total_categories = ServiceCategory.objects.filter(tenant=tenant).count()
		
		# Stylist statistics
		total_stylists = Stylist.objects.filter(tenant=tenant).count()
		active_stylists = Stylist.objects.filter(tenant=tenant, is_active=True).count()
		
		# Appointment statistics
		total_appointments = Appointment.objects.filter(tenant=tenant).count()
		scheduled_appointments = Appointment.objects.filter(tenant=tenant, status='scheduled').count()
		in_progress_appointments = Appointment.objects.filter(tenant=tenant, status='in_progress').count()
		completed_appointments = Appointment.objects.filter(tenant=tenant, status='completed').count()
		recent_appointments = Appointment.objects.filter(tenant=tenant, created_at__date__gte=thirty_days_ago).count()
		
		# Revenue statistics
		revenue_stats = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago,
			status='completed'
		).aggregate(
			total_revenue=Sum('price'),
			avg_appointment_value=Avg('price'),
			appointment_count=Count('id')
		)
		
		# Popular services (top 5)
		popular_services = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago,
			status='completed'
		).values(
			'service__name'
		).annotate(
			count=Count('id'),
			total_revenue=Sum('price')
		).order_by('-count')[:5]
		
		# Stylist performance (top 10)
		stylist_performance = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago,
			status='completed'
		).values(
			'stylist__first_name',
			'stylist__last_name',
			'stylist__id'
		).annotate(
			appointment_count=Count('id'),
			total_revenue=Sum('price'),
			avg_revenue=Avg('price')
		).order_by('-total_revenue')[:10]
		
		# Weekly revenue comparison (NEW)
		seven_days_ago = today - timedelta(days=7)
		this_week_revenue = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=seven_days_ago,
			status='completed'
		).aggregate(total=Sum('price'))
		last_week_revenue = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=seven_days_ago - timedelta(days=7),
			created_at__date__lt=seven_days_ago,
			status='completed'
		).aggregate(total=Sum('price'))
		week_growth = ((float(this_week_revenue['total'] or 0) - float(last_week_revenue['total'] or 0)) / float(last_week_revenue['total'] or 1) * 100) if last_week_revenue['total'] else 0
		
		# Daily revenue trend (last 7 days) (NEW)
		daily_revenue = []
		for i in range(7):
			date = today - timedelta(days=i)
			day_revenue = Appointment.objects.filter(
				tenant=tenant,
				created_at__date=date,
				status='completed'
			).aggregate(total=Sum('price'))
			daily_revenue.append({
				'date': date.strftime('%Y-%m-%d'),
				'day': date.strftime('%a'),
				'revenue': float(day_revenue['total'] or 0),
				'appointments': Appointment.objects.filter(tenant=tenant, created_at__date=date, status='completed').count()
			})
		daily_revenue.reverse()
		
		# Peak hours analysis (NEW)
		from django.db.models.functions import ExtractHour
		peak_hours = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago,
			status='completed'
		).annotate(
			hour=ExtractHour('start_time')
		).values('hour').annotate(
			appointment_count=Count('id'),
			revenue=Sum('price')
		).order_by('-appointment_count')[:5]
		
		# Category performance (NEW)
		category_performance = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago,
			status='completed'
		).values(
			'service__category__name'
		).annotate(
			total_revenue=Sum('price'),
			appointment_count=Count('id'),
			avg_revenue=Avg('price')
		).order_by('-total_revenue')[:5]
		
		# Customer analytics (NEW)
		unique_customers = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago
		).exclude(customer_name='').values('customer_name').distinct().count()
		
		repeat_customers = Appointment.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago
		).exclude(customer_name='').values('customer_name').annotate(
			appointment_count=Count('id')
		).filter(appointment_count__gt=1).count()
		
		# Cancellation rate (NEW)
		cancelled_appointments = Appointment.objects.filter(tenant=tenant, status='cancelled').count()
		cancellation_rate = (cancelled_appointments / total_appointments * 100) if total_appointments > 0 else 0
		
		# Today's stats (NEW)
		today_revenue = Appointment.objects.filter(
			tenant=tenant,
			created_at__date=today,
			status='completed'
		).aggregate(total=Sum('price'))
		today_appointments = Appointment.objects.filter(
			tenant=tenant,
			created_at__date=today,
			status='completed'
		).count()
		
		return Response({
			'services': {
				'total': total_services,
				'active': active_services,
				'total_categories': total_categories
			},
			'stylists': {
				'total': total_stylists,
				'active': active_stylists
			},
			'appointments': {
				'total': total_appointments,
				'scheduled': scheduled_appointments,
				'in_progress': in_progress_appointments,
				'completed': completed_appointments,
				'cancelled': cancelled_appointments,
				'cancellation_rate': round(cancellation_rate, 2),
				'recent_30_days': recent_appointments,
				'today': today_appointments
			},
			'revenue': {
				'total_30_days': float(revenue_stats['total_revenue'] or 0),
				'today': float(today_revenue['total'] or 0),
				'this_week': float(this_week_revenue['total'] or 0),
				'last_week': float(last_week_revenue['total'] or 0),
				'week_growth_percent': round(week_growth, 2),
				'average_appointment_value': float(revenue_stats['avg_appointment_value'] or 0),
				'appointment_count': revenue_stats['appointment_count'] or 0
			},
			'daily_trends': daily_revenue,
			'peak_hours': list(peak_hours),
			'popular_services': list(popular_services),
			'category_performance': list(category_performance),
			'stylist_performance': list(stylist_performance),
			'customers': {
				'unique_customers_30_days': unique_customers,
				'repeat_customers': repeat_customers,
				'retention_rate': round((repeat_customers / unique_customers * 100) if unique_customers > 0 else 0, 2)
			}
		})


class AppointmentBulkDeleteView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]

	def post(self, request):
		appointment_ids = request.data.get('ids', [])
		if not appointment_ids:
			return Response({'error': 'No appointment IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
		
		tenant = request.user.userprofile.tenant
		deleted_count = Appointment.objects.filter(id__in=appointment_ids, tenant=tenant).delete()[0]
		return Response({'message': f'{deleted_count} appointment(s) deleted successfully'})


class AppointmentBulkStatusUpdateView(APIView):
	permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('salon')]

	def post(self, request):
		appointment_ids = request.data.get('ids', [])
		new_status = request.data.get('status')
		
		if not appointment_ids:
			return Response({'error': 'No appointment IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
		if not new_status:
			return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
		if new_status not in ['scheduled', 'in_progress', 'completed', 'cancelled']:
			return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
		
		tenant = request.user.userprofile.tenant
		updated_count = Appointment.objects.filter(id__in=appointment_ids, tenant=tenant).update(status=new_status)
		return Response({'message': f'{updated_count} appointment(s) updated successfully'})
