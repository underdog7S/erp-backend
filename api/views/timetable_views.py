"""
Timetable Management API Views
Separate file for better organization
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
from education.models import Period, Room, Timetable, Holiday, SubstituteTeacher
from api.models.permissions import HasFeaturePermissionFactory
from api.models.serializers_education import (
    PeriodSerializer, RoomSerializer, TimetableSerializer, TimetableDetailSerializer,
    HolidaySerializer, SubstituteTeacherSerializer
)

logger = logging.getLogger(__name__)

# Period Views
class PeriodListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            periods = Period.objects.filter(tenant=profile.tenant, is_active=True).order_by('order', 'start_time')
            serializer = PeriodSerializer(periods, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            
            # Prepare data with proper formatting
            data = request.data.copy()
            
            # Ensure order is an integer
            if 'order' in data:
                try:
                    data['order'] = int(data['order'])
                except (ValueError, TypeError):
                    return Response({
                        'error': 'Invalid order value. Must be a positive integer.',
                        'details': f"Received: {data.get('order')}"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Ensure time fields are properly formatted (HTML time input sends HH:MM, Django accepts HH:MM:SS)
            if 'start_time' in data and data['start_time']:
                if len(data['start_time']) == 5:  # HH:MM format
                    data['start_time'] = data['start_time'] + ':00'  # Convert to HH:MM:SS
            if 'end_time' in data and data['end_time']:
                if len(data['end_time']) == 5:  # HH:MM format
                    data['end_time'] = data['end_time'] + ':00'  # Convert to HH:MM:SS
            
            # Handle break_type - only include if is_break is True
            if 'is_break' in data and not data.get('is_break'):
                data['break_type'] = ''
            
            serializer = PeriodSerializer(data=data)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            # Return detailed validation errors
            error_details = {}
            for field, errors in serializer.errors.items():
                if isinstance(errors, list):
                    error_details[field] = errors[0] if errors else 'Invalid value'
                else:
                    error_details[field] = str(errors)
            
            return Response({
                'error': 'Validation failed',
                'details': error_details
            }, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating period: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to create period: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PeriodDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            period = Period.objects.get(id=pk, tenant=profile.tenant)
            serializer = PeriodSerializer(period)
            return Response(serializer.data)
        except Period.DoesNotExist:
            return Response({'error': 'Period not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            period = Period.objects.get(id=pk, tenant=profile.tenant)
            
            # Prepare data with proper formatting
            data = request.data.copy()
            
            # Ensure order is an integer if provided
            if 'order' in data:
                try:
                    data['order'] = int(data['order'])
                except (ValueError, TypeError):
                    return Response({
                        'error': 'Invalid order value. Must be a positive integer.',
                        'details': f"Received: {data.get('order')}"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Ensure time fields are properly formatted
            if 'start_time' in data and data['start_time']:
                if len(data['start_time']) == 5:  # HH:MM format
                    data['start_time'] = data['start_time'] + ':00'  # Convert to HH:MM:SS
            if 'end_time' in data and data['end_time']:
                if len(data['end_time']) == 5:  # HH:MM format
                    data['end_time'] = data['end_time'] + ':00'  # Convert to HH:MM:SS
            
            # Handle break_type - only include if is_break is True
            if 'is_break' in data and not data.get('is_break'):
                data['break_type'] = ''
            
            serializer = PeriodSerializer(period, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            
            # Return detailed validation errors
            error_details = {}
            for field, errors in serializer.errors.items():
                if isinstance(errors, list):
                    error_details[field] = errors[0] if errors else 'Invalid value'
                else:
                    error_details[field] = str(errors)
            
            return Response({
                'error': 'Validation failed',
                'details': error_details
            }, status=status.HTTP_400_BAD_REQUEST)
        except Period.DoesNotExist:
            return Response({'error': 'Period not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating period: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to update period: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            period = Period.objects.get(id=pk, tenant=profile.tenant)
            period.delete()
            return Response({'message': 'Period deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Period.DoesNotExist:
            return Response({'error': 'Period not found.'}, status=status.HTTP_404_NOT_FOUND)


# Room Views
class RoomListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            rooms = Room.objects.filter(tenant=profile.tenant, is_active=True).order_by('name')
            serializer = RoomSerializer(rooms, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            serializer = RoomSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class RoomDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            room = Room.objects.get(id=pk, tenant=profile.tenant)
            serializer = RoomSerializer(room)
            return Response(serializer.data)
        except Room.DoesNotExist:
            return Response({'error': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            room = Room.objects.get(id=pk, tenant=profile.tenant)
            serializer = RoomSerializer(room, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Room.DoesNotExist:
            return Response({'error': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            room = Room.objects.get(id=pk, tenant=profile.tenant)
            room.delete()
            return Response({'message': 'Room deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Room.DoesNotExist:
            return Response({'error': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)


# Timetable Views
class TimetableListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            # Filter parameters
            academic_year_id = request.query_params.get('academic_year')
            class_id = request.query_params.get('class')
            day = request.query_params.get('day')
            teacher_id = request.query_params.get('teacher')
            
            queryset = Timetable.objects.filter(tenant=tenant, is_active=True)
            
            if academic_year_id:
                queryset = queryset.filter(academic_year_id=academic_year_id)
            if class_id:
                queryset = queryset.filter(class_obj_id=class_id)
            if day:
                queryset = queryset.filter(day=day)
            if teacher_id:
                queryset = queryset.filter(teacher_id=teacher_id)
            
            queryset = queryset.select_related('academic_year', 'class_obj', 'period', 'subject', 'teacher__user', 'room').order_by('academic_year', 'class_obj', 'day', 'period__order')
            serializer = TimetableSerializer(queryset, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            # Check for conflicts
            academic_year_id = request.data.get('academic_year')
            class_id = request.data.get('class_obj')
            day = request.data.get('day')
            period_id = request.data.get('period')
            teacher_id = request.data.get('teacher')
            room_id = request.data.get('room')
            
            # Check teacher conflict (same teacher, same day, same period)
            if teacher_id:
                teacher_conflict = Timetable.objects.filter(
                    tenant=tenant,
                    academic_year_id=academic_year_id,
                    day=day,
                    period_id=period_id,
                    teacher_id=teacher_id,
                    is_active=True
                ).exists()
                
                if teacher_conflict:
                    return Response({
                        'error': 'Teacher is already assigned to another class at this time.',
                        'conflict_type': 'teacher'
                    }, status=status.HTTP_409_CONFLICT)
            
            # Check room conflict (same room, same day, same period)
            if room_id:
                room_conflict = Timetable.objects.filter(
                    tenant=tenant,
                    academic_year_id=academic_year_id,
                    day=day,
                    period_id=period_id,
                    room_id=room_id,
                    is_active=True
                ).exists()
                
                if room_conflict:
                    return Response({
                        'error': 'Room is already booked by another class at this time.',
                        'conflict_type': 'room'
                    }, status=status.HTTP_409_CONFLICT)
            
            serializer = TimetableSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(tenant=tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class TimetableDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            timetable = Timetable.objects.select_related('academic_year', 'class_obj', 'period', 'subject', 'teacher__user', 'room').get(id=pk, tenant=profile.tenant)
            serializer = TimetableDetailSerializer(timetable)
            return Response(serializer.data)
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable entry not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            timetable = Timetable.objects.get(id=pk, tenant=tenant)
            
            # Check for conflicts (excluding current entry)
            academic_year_id = request.data.get('academic_year', timetable.academic_year_id)
            class_id = request.data.get('class_obj', timetable.class_obj_id)
            day = request.data.get('day', timetable.day)
            period_id = request.data.get('period', timetable.period_id)
            teacher_id = request.data.get('teacher', timetable.teacher_id if timetable.teacher else None)
            room_id = request.data.get('room', timetable.room_id if timetable.room else None)
            
            # Check teacher conflict
            if teacher_id:
                teacher_conflict = Timetable.objects.filter(
                    tenant=tenant,
                    academic_year_id=academic_year_id,
                    day=day,
                    period_id=period_id,
                    teacher_id=teacher_id,
                    is_active=True
                ).exclude(id=pk).exists()
                
                if teacher_conflict:
                    return Response({
                        'error': 'Teacher is already assigned to another class at this time.',
                        'conflict_type': 'teacher'
                    }, status=status.HTTP_409_CONFLICT)
            
            # Check room conflict
            if room_id:
                room_conflict = Timetable.objects.filter(
                    tenant=tenant,
                    academic_year_id=academic_year_id,
                    day=day,
                    period_id=period_id,
                    room_id=room_id,
                    is_active=True
                ).exclude(id=pk).exists()
                
                if room_conflict:
                    return Response({
                        'error': 'Room is already booked by another class at this time.',
                        'conflict_type': 'room'
                    }, status=status.HTTP_409_CONFLICT)
            
            serializer = TimetableSerializer(timetable, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable entry not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            timetable = Timetable.objects.get(id=pk, tenant=profile.tenant)
            timetable.delete()
            return Response({'message': 'Timetable entry deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable entry not found.'}, status=status.HTTP_404_NOT_FOUND)


class TimetableByClassView(APIView):
    """Get timetable for a specific class, organized by day"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, class_id):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            academic_year_id = request.query_params.get('academic_year')
            
            if not academic_year_id:
                return Response({'error': 'academic_year parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            timetables = Timetable.objects.filter(
                tenant=profile.tenant,
                class_obj_id=class_id,
                academic_year_id=academic_year_id,
                is_active=True
            ).select_related('period', 'subject', 'teacher__user', 'room').order_by('day', 'period__order')
            
            # Organize by day
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            result = {day: [] for day in days}
            
            for timetable in timetables:
                serializer = TimetableSerializer(timetable)
                result[timetable.day].append(serializer.data)
            
            return Response(result)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


# Holiday Views
class HolidayListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            academic_year_id = request.query_params.get('academic_year')
            
            queryset = Holiday.objects.filter(tenant=profile.tenant)
            if academic_year_id:
                queryset = queryset.filter(academic_year_id=academic_year_id)
            
            queryset = queryset.order_by('date')
            serializer = HolidaySerializer(queryset, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            serializer = HolidaySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class HolidayDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            holiday = Holiday.objects.get(id=pk, tenant=profile.tenant)
            serializer = HolidaySerializer(holiday)
            return Response(serializer.data)
        except Holiday.DoesNotExist:
            return Response({'error': 'Holiday not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            holiday = Holiday.objects.get(id=pk, tenant=profile.tenant)
            serializer = HolidaySerializer(holiday, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Holiday.DoesNotExist:
            return Response({'error': 'Holiday not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            holiday = Holiday.objects.get(id=pk, tenant=profile.tenant)
            holiday.delete()
            return Response({'message': 'Holiday deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Holiday.DoesNotExist:
            return Response({'error': 'Holiday not found.'}, status=status.HTTP_404_NOT_FOUND)


# SubstituteTeacher Views
class SubstituteTeacherListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            
            queryset = SubstituteTeacher.objects.filter(tenant=profile.tenant, is_active=True)
            
            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            if date_to:
                queryset = queryset.filter(date__lte=date_to)
            
            queryset = queryset.select_related('timetable__class_obj', 'timetable__period', 'timetable__subject', 'original_teacher__user', 'substitute_teacher__user').order_by('-date', 'timetable')
            serializer = SubstituteTeacherSerializer(queryset, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            serializer = SubstituteTeacherSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class SubstituteTeacherDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            substitute = SubstituteTeacher.objects.select_related('timetable__class_obj', 'timetable__period', 'timetable__subject', 'original_teacher__user', 'substitute_teacher__user').get(id=pk, tenant=profile.tenant)
            serializer = SubstituteTeacherSerializer(substitute)
            return Response(serializer.data)
        except SubstituteTeacher.DoesNotExist:
            return Response({'error': 'Substitute assignment not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            substitute = SubstituteTeacher.objects.get(id=pk, tenant=profile.tenant)
            serializer = SubstituteTeacherSerializer(substitute, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SubstituteTeacher.DoesNotExist:
            return Response({'error': 'Substitute assignment not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            substitute = SubstituteTeacher.objects.get(id=pk, tenant=profile.tenant)
            substitute.delete()
            return Response({'message': 'Substitute assignment deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except SubstituteTeacher.DoesNotExist:
            return Response({'error': 'Substitute assignment not found.'}, status=status.HTTP_404_NOT_FOUND)


class AvailableTeachersView(APIView):
    """Get available teachers for a specific time slot (day + period)"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            academic_year_id = request.query_params.get('academic_year')
            day = request.query_params.get('day')
            period_id = request.query_params.get('period')
            class_id = request.query_params.get('class', '')  # Optional: filter by class assignment
            
            if not all([academic_year_id, day, period_id]):
                return Response({
                    'error': 'academic_year, day, and period parameters are required.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get all teachers (staff members) in the tenant
            all_teachers = UserProfile.objects.filter(
                tenant=tenant
            ).exclude(role__name='student').select_related('user')
            
            # If class_id is provided, prefer teachers assigned to that class
            if class_id:
                from education.models import Class
                try:
                    class_obj = Class.objects.get(id=class_id, tenant=tenant)
                    assigned_teachers = all_teachers.filter(assigned_classes=class_obj)
                except Class.DoesNotExist:
                    assigned_teachers = all_teachers.none()
            else:
                assigned_teachers = all_teachers.none()
            
            # Find teachers who are already busy at this time slot
            busy_teachers = Timetable.objects.filter(
                tenant=tenant,
                academic_year_id=academic_year_id,
                day=day,
                period_id=period_id,
                is_active=True,
                teacher__isnull=False
            ).values_list('teacher_id', flat=True)
            
            # Get available teachers (not busy)
            available_teachers = all_teachers.exclude(id__in=busy_teachers)
            
            # Separate assigned vs other available teachers
            assigned_available = available_teachers.filter(id__in=assigned_teachers.values_list('id', flat=True))
            other_available = available_teachers.exclude(id__in=assigned_teachers.values_list('id', flat=True))
            
            # Format response
            def format_teacher(teacher):
                return {
                    'id': teacher.id,
                    'name': teacher.user.get_full_name() or teacher.user.username,
                    'username': teacher.user.username,
                    'email': teacher.user.email,
                    'role': teacher.role.name if teacher.role else None,
                    'is_assigned_to_class': assigned_teachers.filter(id=teacher.id).exists() if class_id else False
                }
            
            result = {
                'assigned_teachers': [format_teacher(t) for t in assigned_available],
                'other_teachers': [format_teacher(t) for t in other_available],
                'busy_teachers': [
                    {
                        'id': t.id,
                        'name': t.user.get_full_name() or t.user.username,
                        'busy_with': Timetable.objects.filter(
                            tenant=tenant,
                            academic_year_id=academic_year_id,
                            day=day,
                            period_id=period_id,
                            teacher=t,
                            is_active=True
                        ).first().class_obj.name if Timetable.objects.filter(
                            tenant=tenant,
                            academic_year_id=academic_year_id,
                            day=day,
                            period_id=period_id,
                            teacher=t,
                            is_active=True
                        ).exists() else None
                    }
                    for t in UserProfile.objects.filter(id__in=busy_teachers, tenant=tenant).select_related('user')
                ],
                'total_available': available_teachers.count(),
                'total_busy': len(busy_teachers)
            }
            
            return Response(result)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class AvailableRoomsView(APIView):
    """Get available rooms for a specific time slot (day + period)"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            academic_year_id = request.query_params.get('academic_year')
            day = request.query_params.get('day')
            period_id = request.query_params.get('period')
            room_type = request.query_params.get('room_type', '')  # Optional: filter by room type
            
            if not all([academic_year_id, day, period_id]):
                return Response({
                    'error': 'academic_year, day, and period parameters are required.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get all active rooms
            all_rooms = Room.objects.filter(tenant=tenant, is_active=True)
            
            # Filter by room type if provided
            if room_type:
                all_rooms = all_rooms.filter(room_type=room_type)
            
            # Find rooms that are already booked at this time slot
            booked_room_ids = Timetable.objects.filter(
                tenant=tenant,
                academic_year_id=academic_year_id,
                day=day,
                period_id=period_id,
                is_active=True,
                room__isnull=False
            ).values_list('room_id', flat=True)
            
            # Get available rooms
            available_rooms = all_rooms.exclude(id__in=booked_room_ids)
            
            # Format response
            def format_room(room):
                return {
                    'id': room.id,
                    'name': room.name,
                    'room_number': room.room_number,
                    'room_type': room.room_type,
                    'room_type_display': room.get_room_type_display(),
                    'capacity': room.capacity,
                    'facilities': room.facilities
                }
            
            result = {
                'available_rooms': [format_room(r) for r in available_rooms],
                'booked_rooms': [
                    {
                        'id': r.id,
                        'name': r.name,
                        'booked_by': Timetable.objects.filter(
                            tenant=tenant,
                            academic_year_id=academic_year_id,
                            day=day,
                            period_id=period_id,
                            room=r,
                            is_active=True
                        ).first().class_obj.name if Timetable.objects.filter(
                            tenant=tenant,
                            academic_year_id=academic_year_id,
                            day=day,
                            period_id=period_id,
                            room=r,
                            is_active=True
                        ).exists() else None
                    }
                    for r in Room.objects.filter(id__in=booked_room_ids, tenant=tenant)
                ],
                'total_available': available_rooms.count(),
                'total_booked': len(booked_room_ids)
            }
            
            return Response(result)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class TimetableSuggestionsView(APIView):
    """Get smart suggestions for timetable entry (available teachers and rooms)"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            academic_year_id = request.query_params.get('academic_year')
            class_id = request.query_params.get('class')
            day = request.query_params.get('day')
            period_id = request.query_params.get('period')
            subject_id = request.query_params.get('subject', '')  # Optional: for subject-specific suggestions
            
            if not all([academic_year_id, class_id, day, period_id]):
                return Response({
                    'error': 'academic_year, class, day, and period parameters are required.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get available teachers
            all_teachers = UserProfile.objects.filter(tenant=tenant).exclude(role__name='student').select_related('user')
            
            # Get teachers assigned to this class (preferred)
            from education.models import Class
            try:
                class_obj = Class.objects.get(id=class_id, tenant=tenant)
                assigned_teachers = all_teachers.filter(assigned_classes=class_obj)
            except Class.DoesNotExist:
                assigned_teachers = all_teachers.none()
            
            # Find busy teachers
            busy_teachers = Timetable.objects.filter(
                tenant=tenant,
                academic_year_id=academic_year_id,
                day=day,
                period_id=period_id,
                is_active=True,
                teacher__isnull=False
            ).exclude(class_obj_id=class_id).values_list('teacher_id', flat=True)
            
            available_teachers = all_teachers.exclude(id__in=busy_teachers)
            assigned_available = available_teachers.filter(id__in=assigned_teachers.values_list('id', flat=True))
            other_available = available_teachers.exclude(id__in=assigned_teachers.values_list('id', flat=True))
            
            # Get available rooms
            all_rooms = Room.objects.filter(tenant=tenant, is_active=True)
            booked_rooms = Timetable.objects.filter(
                tenant=tenant,
                academic_year_id=academic_year_id,
                day=day,
                period_id=period_id,
                is_active=True,
                room__isnull=False
            ).exclude(class_obj_id=class_id).values_list('room_id', flat=True)
            
            available_rooms = all_rooms.exclude(id__in=booked_rooms)
            
            # Get subject info if provided
            subject_info = None
            if subject_id:
                from education.models import Subject
                try:
                    subject = Subject.objects.get(id=subject_id, tenant=tenant)
                    subject_info = {
                        'id': subject.id,
                        'name': subject.name,
                        'code': subject.code,
                        'has_practical': subject.has_practical,
                        'suggested_room_types': ['lab'] if subject.has_practical else ['classroom']
                    }
                except Subject.DoesNotExist:
                    pass
            
            # Format teachers
            def format_teacher(teacher):
                # Check if teacher has taught this subject before (if subject_id provided)
                has_taught_subject = False
                if subject_id:
                    has_taught_subject = Timetable.objects.filter(
                        tenant=tenant,
                        teacher=teacher,
                        subject_id=subject_id,
                        is_active=True
                    ).exists()
                
                return {
                    'id': teacher.id,
                    'name': teacher.user.get_full_name() or teacher.user.username,
                    'username': teacher.user.username,
                    'email': teacher.user.email,
                    'role': teacher.role.name if teacher.role else None,
                    'is_assigned_to_class': assigned_teachers.filter(id=teacher.id).exists(),
                    'has_taught_subject': has_taught_subject,
                    'priority_score': (
                        10 if assigned_teachers.filter(id=teacher.id).exists() else 0
                    ) + (5 if has_taught_subject else 0)
                }
            
            # Format rooms
            def format_room(room):
                # Check if room is suitable for subject
                is_suitable = True
                if subject_info and subject_info['has_practical']:
                    is_suitable = room.room_type in ['lab', 'physics_lab', 'chemistry_lab', 'biology_lab', 'computer_lab']
                elif subject_info and not subject_info['has_practical']:
                    is_suitable = room.room_type in ['classroom', 'hall']
                
                return {
                    'id': room.id,
                    'name': room.name,
                    'room_number': room.room_number,
                    'room_type': room.room_type,
                    'room_type_display': room.get_room_type_display(),
                    'capacity': room.capacity,
                    'facilities': room.facilities,
                    'is_suitable_for_subject': is_suitable,
                    'priority_score': 10 if is_suitable else 5
                }
            
            # Sort by priority
            assigned_teachers_list = sorted(
                [format_teacher(t) for t in assigned_available],
                key=lambda x: x['priority_score'],
                reverse=True
            )
            other_teachers_list = sorted(
                [format_teacher(t) for t in other_available],
                key=lambda x: x['priority_score'],
                reverse=True
            )
            available_rooms_list = sorted(
                [format_room(r) for r in available_rooms],
                key=lambda x: x['priority_score'],
                reverse=True
            )
            
            result = {
                'available_teachers': {
                    'assigned_to_class': assigned_teachers_list,
                    'others': other_teachers_list,
                    'total': len(assigned_teachers_list) + len(other_teachers_list)
                },
                'available_rooms': {
                    'suitable': [r for r in available_rooms_list if r['is_suitable_for_subject']],
                    'others': [r for r in available_rooms_list if not r['is_suitable_for_subject']],
                    'total': len(available_rooms_list)
                },
                'subject_info': subject_info,
                'suggestions': {
                    'recommended_teacher': assigned_teachers_list[0] if assigned_teachers_list else (other_teachers_list[0] if other_teachers_list else None),
                    'recommended_room': available_rooms_list[0] if available_rooms_list else None
                }
            }
            
            return Response(result)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)

