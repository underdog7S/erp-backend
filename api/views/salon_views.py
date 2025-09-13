from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from api.models.user import Tenant
from salon.models import ServiceCategory, Service, Stylist, Appointment
from api.serializers import ServiceCategorySerializer, ServiceSerializer, StylistSerializer, AppointmentSerializer


class ServiceCategoryListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
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
	permission_classes = [IsAuthenticated]
	serializer_class = ServiceCategorySerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		return ServiceCategory.objects.filter(tenant=self.request.user.userprofile.tenant)


class ServiceListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
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
	permission_classes = [IsAuthenticated]
	serializer_class = ServiceSerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		return Service.objects.filter(tenant=self.request.user.userprofile.tenant)


class StylistListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
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
	permission_classes = [IsAuthenticated]
	serializer_class = StylistSerializer
	parser_classes = [JSONParser, MultiPartParser, FormParser]
	
	def get_queryset(self):
		return Stylist.objects.filter(tenant=self.request.user.userprofile.tenant)


class AppointmentListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentSerializer
	
	def get_queryset(self):
		queryset = Appointment.objects.filter(tenant=self.request.user.userprofile.tenant)
		status = self.request.query_params.get('status')
		stylist = self.request.query_params.get('stylist')
		date = self.request.query_params.get('date')  # YYYY-MM-DD
		if status:
			queryset = queryset.filter(status=status)
		if stylist:
			queryset = queryset.filter(stylist_id=stylist)
		if date:
			try:
				from datetime import datetime
				date_obj = datetime.strptime(date, '%Y-%m-%d').date()
				queryset = queryset.filter(start_time__date=date_obj)
			except Exception:
				pass
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentSerializer
	
	def get_queryset(self):
		return Appointment.objects.filter(tenant=self.request.user.userprofile.tenant)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone


class AppointmentCheckInView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		try:
			appt = Appointment.objects.get(id=pk, tenant=request.user.userprofile.tenant)
			appt.status = 'in_progress'
			appt.save()
			return Response({'message': 'Appointment checked in', 'status': appt.status})
		except Appointment.DoesNotExist:
			return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)


class AppointmentCompleteView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		try:
			appt = Appointment.objects.get(id=pk, tenant=request.user.userprofile.tenant)
			appt.status = 'completed'
			if not appt.end_time:
				appt.end_time = timezone.now()
			appt.save()
			return Response({'message': 'Appointment completed', 'status': appt.status})
		except Appointment.DoesNotExist:
			return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)


class AppointmentCancelView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		try:
			appt = Appointment.objects.get(id=pk, tenant=request.user.userprofile.tenant)
			appt.status = 'cancelled'
			appt.save()
			return Response({'message': 'Appointment cancelled', 'status': appt.status})
		except Appointment.DoesNotExist:
			return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
