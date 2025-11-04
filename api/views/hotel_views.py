from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from api.models.user import Tenant
from hotel.models import RoomType, Room, Guest, Booking
from api.serializers import RoomTypeSerializer, RoomSerializer, GuestSerializer, BookingSerializer


class RoomTypeListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = RoomTypeSerializer
	
	def get_queryset(self):
		return RoomType.objects.filter(tenant=self.request.user.userprofile.tenant)
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class RoomTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = RoomTypeSerializer
	
	def get_queryset(self):
		return RoomType.objects.filter(tenant=self.request.user.userprofile.tenant)


class RoomListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = RoomSerializer
	
	def get_queryset(self):
		queryset = Room.objects.filter(tenant=self.request.user.userprofile.tenant)
		room_type = self.request.query_params.get('room_type')
		status = self.request.query_params.get('status')
		if room_type:
			queryset = queryset.filter(room_type_id=room_type)
		if status:
			queryset = queryset.filter(status=status)
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = RoomSerializer
	
	def get_queryset(self):
		return Room.objects.filter(tenant=self.request.user.userprofile.tenant)


class GuestListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = GuestSerializer
	
	def get_queryset(self):
		queryset = Guest.objects.filter(tenant=self.request.user.userprofile.tenant)
		search = self.request.query_params.get('search')
		if search:
			queryset = queryset.filter(first_name__icontains=search) | queryset.filter(last_name__icontains=search) | queryset.filter(phone__icontains=search)
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class GuestDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = GuestSerializer
	
	def get_queryset(self):
		return Guest.objects.filter(tenant=self.request.user.userprofile.tenant)


class BookingListCreateView(generics.ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = BookingSerializer
	
	def get_queryset(self):
		queryset = Booking.objects.filter(tenant=self.request.user.userprofile.tenant)
		status_param = self.request.query_params.get('status')
		search = self.request.query_params.get('search')
		date_from = self.request.query_params.get('date_from')
		date_to = self.request.query_params.get('date_to')
		
		if status_param:
			queryset = queryset.filter(status=status_param)
		if search:
			queryset = queryset.filter(
				Q(guest__first_name__icontains=search) |
				Q(guest__last_name__icontains=search) |
				Q(guest__phone__icontains=search) |
				Q(guest__email__icontains=search) |
				Q(room__room_number__icontains=search)
			)
		if date_from:
			try:
				date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
				queryset = queryset.filter(check_in__date__gte=date_from_obj)
			except:
				pass
		if date_to:
			try:
				date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
				queryset = queryset.filter(check_out__date__lte=date_to_obj)
			except:
				pass
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = BookingSerializer
	
	def get_queryset(self):
		return Booking.objects.filter(tenant=self.request.user.userprofile.tenant)


class BookingCheckInView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		try:
			booking = Booking.objects.get(id=pk, tenant=request.user.userprofile.tenant)
			booking.status = 'checked_in'
			booking.save()
			# Update room status
			booking.room.status = 'occupied'
			booking.room.save()
			return Response({'message': 'Guest checked in successfully', 'status': booking.status})
		except Booking.DoesNotExist:
			return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)


class BookingCheckOutView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		try:
			booking = Booking.objects.get(id=pk, tenant=request.user.userprofile.tenant)
			booking.status = 'checked_out'
			booking.save()
			# Update room status
			booking.room.status = 'available'
			booking.room.save()
			return Response({'message': 'Guest checked out successfully', 'status': booking.status})
		except Booking.DoesNotExist:
			return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)


class HotelAnalyticsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		tenant = request.user.userprofile.tenant
		today = timezone.now().date()
		thirty_days_ago = today - timedelta(days=30)
		
		# Room statistics
		total_rooms = Room.objects.filter(tenant=tenant).count()
		available_rooms = Room.objects.filter(tenant=tenant, status='available').count()
		occupied_rooms = Room.objects.filter(tenant=tenant, status='occupied').count()
		maintenance_rooms = Room.objects.filter(tenant=tenant, status='maintenance').count()
		
		# Booking statistics
		total_bookings = Booking.objects.filter(tenant=tenant).count()
		active_bookings = Booking.objects.filter(tenant=tenant, status='checked_in').count()
		reserved_bookings = Booking.objects.filter(tenant=tenant, status='reserved').count()
		recent_bookings = Booking.objects.filter(tenant=tenant, created_at__date__gte=thirty_days_ago).count()
		
		# Revenue statistics
		revenue_stats = Booking.objects.filter(
			tenant=tenant,
			created_at__date__gte=thirty_days_ago,
			status__in=['checked_out']
		).aggregate(
			total_revenue=Sum('total_amount'),
			avg_revenue=Avg('total_amount'),
			booking_count=Count('id')
		)
		
		# Guest statistics
		total_guests = Guest.objects.filter(tenant=tenant).count()
		recent_guests = Guest.objects.filter(tenant=tenant, bookings__created_at__date__gte=thirty_days_ago).distinct().count()
		
		return Response({
			'rooms': {
				'total': total_rooms,
				'available': available_rooms,
				'occupied': occupied_rooms,
				'maintenance': maintenance_rooms,
				'occupancy_rate': round((occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0, 2)
			},
			'bookings': {
				'total': total_bookings,
				'active': active_bookings,
				'reserved': reserved_bookings,
				'recent_30_days': recent_bookings
			},
			'revenue': {
				'total_30_days': float(revenue_stats['total_revenue'] or 0),
				'average_booking': float(revenue_stats['avg_revenue'] or 0),
				'booking_count': revenue_stats['booking_count'] or 0
			},
			'guests': {
				'total': total_guests,
				'recent_30_days': recent_guests
			}
		})


class BookingBulkDeleteView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		booking_ids = request.data.get('ids', [])
		if not booking_ids:
			return Response({'error': 'No booking IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
		
		tenant = request.user.userprofile.tenant
		deleted_count = Booking.objects.filter(id__in=booking_ids, tenant=tenant).delete()[0]
		return Response({'message': f'{deleted_count} booking(s) deleted successfully'})


class BookingBulkStatusUpdateView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		booking_ids = request.data.get('ids', [])
		new_status = request.data.get('status')
		
		if not booking_ids:
			return Response({'error': 'No booking IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
		if not new_status:
			return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
		if new_status not in ['reserved', 'checked_in', 'checked_out', 'cancelled']:
			return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
		
		tenant = request.user.userprofile.tenant
		updated_count = Booking.objects.filter(id__in=booking_ids, tenant=tenant).update(status=new_status)
		
		# Update room statuses if checking in/out
		if new_status == 'checked_in':
			bookings = Booking.objects.filter(id__in=booking_ids, tenant=tenant)
			for booking in bookings:
				booking.room.status = 'occupied'
				booking.room.save()
		elif new_status == 'checked_out':
			bookings = Booking.objects.filter(id__in=booking_ids, tenant=tenant)
			for booking in bookings:
				booking.room.status = 'available'
				booking.room.save()
		
		return Response({'message': f'{updated_count} booking(s) updated successfully'})
