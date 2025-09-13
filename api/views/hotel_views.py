from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
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
		status = self.request.query_params.get('status')
		if status:
			queryset = queryset.filter(status=status)
		return queryset
	
	def perform_create(self, serializer):
		serializer.save(tenant=self.request.user.userprofile.tenant)


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = BookingSerializer
	
	def get_queryset(self):
		return Booking.objects.filter(tenant=self.request.user.userprofile.tenant)
