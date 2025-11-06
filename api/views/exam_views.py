"""
Exam Management System - API Views
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
from education.models import Exam, ExamSchedule, SeatingArrangement, HallTicket, Student, Class, Subject, Room
from api.models.permissions import HasFeaturePermissionFactory, role_required
from api.models.serializers_education import (
    ExamSerializer, ExamScheduleSerializer, SeatingArrangementSerializer, HallTicketSerializer
)
from django.db.models import Q
from django.utils import timezone
import uuid

logger = logging.getLogger(__name__)


# ============================================
# EXAM MANAGEMENT
# ============================================

class ExamListCreateView(APIView):
    """List and create exams"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            exams = Exam.objects.filter(tenant=profile.tenant, is_active=True).order_by('-start_date')
            serializer = ExamSerializer(exams, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            serializer = ExamSerializer(data=request.data, context={'request': request})
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
            logger.error(f"Error creating exam: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to create exam: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExamDetailView(APIView):
    """Get, update, delete exam"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            exam = Exam.objects.get(id=pk, tenant=profile.tenant)
            serializer = ExamSerializer(exam)
            return Response(serializer.data)
        except Exam.DoesNotExist:
            return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            exam = Exam.objects.get(id=pk, tenant=profile.tenant)
            serializer = ExamSerializer(exam, data=request.data, partial=True, context={'request': request})
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
        except Exam.DoesNotExist:
            return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating exam: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to update exam: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @role_required('admin', 'principal')
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            exam = Exam.objects.get(id=pk, tenant=profile.tenant)
            exam.is_active = False
            exam.save()
            return Response({'message': 'Exam deactivated successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exam.DoesNotExist:
            return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


# ============================================
# EXAM SCHEDULE MANAGEMENT
# ============================================

class ExamScheduleListCreateView(APIView):
    """List and create exam schedules"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            exam_id = request.query_params.get('exam_id')
            class_id = request.query_params.get('class_id')
            date = request.query_params.get('date')
            
            schedules = ExamSchedule.objects.filter(tenant=profile.tenant, is_active=True)
            
            if exam_id:
                schedules = schedules.filter(exam_id=exam_id)
            if class_id:
                schedules = schedules.filter(class_obj_id=class_id)
            if date:
                schedules = schedules.filter(date=date)
            
            schedules = schedules.order_by('date', 'start_time', 'class_obj')
            serializer = ExamScheduleSerializer(schedules, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            
            # Check for room conflicts
            room_id = request.data.get('room')
            date = request.data.get('date')
            start_time = request.data.get('start_time')
            end_time = request.data.get('end_time')
            
            if room_id and date and start_time and end_time:
                # Validate time format and convert if needed
                from datetime import datetime
                try:
                    if isinstance(start_time, str):
                        start_time = datetime.strptime(start_time, '%H:%M:%S').time() if ':' in start_time and len(start_time.split(':')) == 3 else datetime.strptime(start_time, '%H:%M').time()
                    if isinstance(end_time, str):
                        end_time = datetime.strptime(end_time, '%H:%M:%S').time() if ':' in end_time and len(end_time.split(':')) == 3 else datetime.strptime(end_time, '%H:%M').time()
                except (ValueError, TypeError):
                    return Response({
                        'error': 'Invalid time format. Please use HH:MM or HH:MM:SS format.',
                        'details': {'start_time': start_time, 'end_time': end_time}
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check for overlapping schedules in same room
                conflict = ExamSchedule.objects.filter(
                    tenant=profile.tenant,
                    room_id=room_id,
                    date=date,
                    is_active=True
                ).filter(
                    Q(start_time__lt=end_time, end_time__gt=start_time)
                ).exists()
                
                if conflict:
                    return Response({
                        'error': 'Room is already booked for another exam at this time.',
                        'conflict_type': 'room'
                    }, status=status.HTTP_409_CONFLICT)
            
            serializer = ExamScheduleSerializer(data=request.data, context={'request': request})
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


class ExamScheduleDetailView(APIView):
    """Get, update, delete exam schedule"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            schedule = ExamSchedule.objects.get(id=pk, tenant=profile.tenant)
            serializer = ExamScheduleSerializer(schedule)
            return Response(serializer.data)
        except ExamSchedule.DoesNotExist:
            return Response({'error': 'Exam schedule not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            schedule = ExamSchedule.objects.get(id=pk, tenant=profile.tenant)
            
            # Check for room conflicts
            room_id = request.data.get('room', schedule.room_id if schedule.room else None)
            date = request.data.get('date', schedule.date)
            start_time = request.data.get('start_time', schedule.start_time)
            end_time = request.data.get('end_time', schedule.end_time)
            
            if room_id and date and start_time and end_time:
                # Validate time format and convert if needed
                from datetime import datetime
                try:
                    if isinstance(start_time, str):
                        start_time = datetime.strptime(start_time, '%H:%M:%S').time() if ':' in start_time and len(start_time.split(':')) == 3 else datetime.strptime(start_time, '%H:%M').time()
                    if isinstance(end_time, str):
                        end_time = datetime.strptime(end_time, '%H:%M:%S').time() if ':' in end_time and len(end_time.split(':')) == 3 else datetime.strptime(end_time, '%H:%M').time()
                except (ValueError, TypeError):
                    return Response({
                        'error': 'Invalid time format. Please use HH:MM or HH:MM:SS format.',
                        'details': {'start_time': start_time, 'end_time': end_time}
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                conflict = ExamSchedule.objects.filter(
                    tenant=profile.tenant,
                    room_id=room_id,
                    date=date,
                    is_active=True
                ).exclude(id=pk).filter(
                    Q(start_time__lt=end_time, end_time__gt=start_time)
                ).exists()
                
                if conflict:
                    return Response({
                        'error': 'Room is already booked for another exam at this time.',
                        'conflict_type': 'room'
                    }, status=status.HTTP_409_CONFLICT)
            
            serializer = ExamScheduleSerializer(schedule, data=request.data, partial=True, context={'request': request})
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
        except ExamSchedule.DoesNotExist:
            return Response({'error': 'Exam schedule not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating exam schedule: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to update exam schedule: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @role_required('admin', 'principal')
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            schedule = ExamSchedule.objects.get(id=pk, tenant=profile.tenant)
            schedule.is_active = False
            schedule.save()
            return Response({'message': 'Exam schedule deactivated successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except ExamSchedule.DoesNotExist:
            return Response({'error': 'Exam schedule not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting exam schedule: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to delete exam schedule: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# SEATING ARRANGEMENT MANAGEMENT
# ============================================

class SeatingArrangementListCreateView(APIView):
    """List and create seating arrangements"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            exam_schedule_id = request.query_params.get('exam_schedule_id')
            student_id = request.query_params.get('student_id')
            
            arrangements = SeatingArrangement.objects.filter(tenant=profile.tenant, is_active=True)
            
            if exam_schedule_id:
                arrangements = arrangements.filter(exam_schedule_id=exam_schedule_id)
            if student_id:
                arrangements = arrangements.filter(student_id=student_id)
            
            arrangements = arrangements.order_by('exam_schedule', 'seat_number')
            serializer = SeatingArrangementSerializer(arrangements, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            serializer = SeatingArrangementSerializer(data=request.data, context={'request': request})
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
            logger.error(f"Error creating seating arrangement: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to create seating arrangement: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SeatingArrangementDetailView(APIView):
    """Get, update, delete seating arrangement"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            arrangement = SeatingArrangement.objects.get(id=pk, tenant=profile.tenant)
            serializer = SeatingArrangementSerializer(arrangement)
            return Response(serializer.data)
        except SeatingArrangement.DoesNotExist:
            return Response({'error': 'Seating arrangement not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            arrangement = SeatingArrangement.objects.get(id=pk, tenant=profile.tenant)
            serializer = SeatingArrangementSerializer(arrangement, data=request.data, partial=True, context={'request': request})
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
        except SeatingArrangement.DoesNotExist:
            return Response({'error': 'Seating arrangement not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating seating arrangement: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to update seating arrangement: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @role_required('admin', 'principal')
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            arrangement = SeatingArrangement.objects.get(id=pk, tenant=profile.tenant)
            arrangement.is_active = False
            arrangement.save()
            return Response({'message': 'Seating arrangement deactivated successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except SeatingArrangement.DoesNotExist:
            return Response({'error': 'Seating arrangement not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting seating arrangement: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to delete seating arrangement: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# HALL TICKET MANAGEMENT
# ============================================

class HallTicketListCreateView(APIView):
    """List and create hall tickets"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            exam_id = request.query_params.get('exam_id')
            student_id = request.query_params.get('student_id')
            status_filter = request.query_params.get('status')
            
            tickets = HallTicket.objects.filter(tenant=profile.tenant)
            
            if exam_id:
                tickets = tickets.filter(exam_id=exam_id)
            if student_id:
                tickets = tickets.filter(student_id=student_id)
            if status_filter:
                tickets = tickets.filter(status=status_filter)
            
            tickets = tickets.order_by('-generated_at', 'student')
            serializer = HallTicketSerializer(tickets, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            
            # Generate ticket number if not provided
            data = request.data.copy()
            if not data.get('ticket_number'):
                exam_id = data.get('exam')
                student_id = data.get('student')
                try:
                    exam = Exam.objects.get(id=exam_id, tenant=profile.tenant)
                    student = Student.objects.get(id=student_id, tenant=profile.tenant)
                    hall_ticket = HallTicket(
                        tenant=profile.tenant,
                        exam=exam,
                        student=student,
                        generated_by=profile
                    )
                    data['ticket_number'] = hall_ticket.generate_ticket_number()
                except (Exam.DoesNotExist, Student.DoesNotExist):
                    pass
            
            serializer = HallTicketSerializer(data=data)
            if serializer.is_valid():
                instance = serializer.save(tenant=profile.tenant, generated_by=profile)
                if not instance.ticket_number:
                    instance.ticket_number = instance.generate_ticket_number()
                    instance.save()
                return Response(HallTicketSerializer(instance).data, status=status.HTTP_201_CREATED)
            
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
            logger.error(f"Error creating hall ticket: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to create hall ticket: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HallTicketDetailView(APIView):
    """Get, update hall ticket"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            ticket = HallTicket.objects.get(id=pk, tenant=profile.tenant)
            serializer = HallTicketSerializer(ticket)
            return Response(serializer.data)
        except HallTicket.DoesNotExist:
            return Response({'error': 'Hall ticket not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            ticket = HallTicket.objects.get(id=pk, tenant=profile.tenant)
            serializer = HallTicketSerializer(ticket, data=request.data, partial=True)
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
        except HallTicket.DoesNotExist:
            return Response({'error': 'Hall ticket not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating hall ticket: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to update hall ticket: {str(e)}',
                'details': 'Please check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateHallTicketsView(APIView):
    """Bulk generate hall tickets for all students in an exam"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            exam_id = request.data.get('exam_id')
            class_id = request.data.get('class_id')  # Optional: filter by class
            
            if not exam_id:
                return Response({'error': 'exam_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                exam = Exam.objects.get(id=exam_id, tenant=profile.tenant)
            except Exam.DoesNotExist:
                return Response({'error': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)
            
            # Get students
            students = Student.objects.filter(tenant=profile.tenant, is_active=True)
            if class_id:
                students = students.filter(assigned_class_id=class_id)
            
            generated_count = 0
            errors = []
            
            for student in students:
                # Check if ticket already exists
                existing = HallTicket.objects.filter(
                    tenant=profile.tenant,
                    exam=exam,
                    student=student
                ).first()
                
                if existing:
                    errors.append(f"Ticket already exists for {student.name}")
                    continue
                
                # Create hall ticket
                hall_ticket = HallTicket(
                    tenant=profile.tenant,
                    exam=exam,
                    student=student,
                    generated_by=profile,
                    status='generated'
                )
                hall_ticket.generate_ticket_number()
                
                # Handle ticket number uniqueness
                max_attempts = 10
                attempt = 0
                while attempt < max_attempts:
                    try:
                        hall_ticket.save()
                        generated_count += 1
                        break
                    except Exception as e:
                        if 'ticket_number' in str(e).lower() or 'unique' in str(e).lower():
                            # Regenerate ticket number if collision
                            import random
                            suffix = str(random.randint(1000, 9999))
                            hall_ticket.ticket_number = f"{hall_ticket.ticket_number}-{suffix}"
                            attempt += 1
                        else:
                            errors.append(f"Error creating ticket for {student.name}: {str(e)}")
                            break
                else:
                    errors.append(f"Failed to generate unique ticket number for {student.name} after {max_attempts} attempts")
            
            return Response({
                'message': f'Generated {generated_count} hall tickets.',
                'generated_count': generated_count,
                'errors': errors if errors else None
            }, status=status.HTTP_201_CREATED)
            
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error generating hall tickets: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate hall tickets: {str(e)}',
                'details': 'Check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

