import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
from education.models import (
    Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, 
    ReportCard, StaffAttendance, Department, AcademicYear, Term, Subject, 
    Unit, AssessmentType, Assessment, MarksEntry, FeeInstallmentPlan, FeeInstallment,
    OldBalance, BalanceAdjustment, StudentPromotion, TransferCertificate, AdmissionApplication,
    Period, Room, Timetable, Holiday, SubstituteTeacher, ReportTemplate, ReportField
)
from api.models.permissions import HasFeaturePermissionFactory, role_required, role_exclude
from api.models.serializers_education import (
    AdmissionApplicationSerializer,
    ClassSerializer, StudentSerializer, FeeStructureSerializer, FeePaymentSerializer, 
    FeeDiscountSerializer, AttendanceSerializer, ReportCardSerializer, 
    StaffAttendanceSerializer, DepartmentSerializer, AcademicYearSerializer, 
    TermSerializer, SubjectSerializer, UnitSerializer, AssessmentTypeSerializer, 
    AssessmentSerializer, MarksEntrySerializer, FeeInstallmentPlanSerializer, 
    FeeInstallmentSerializer, OldBalanceSerializer, BalanceAdjustmentSerializer,
    TransferCertificateSerializer,
    PeriodSerializer, RoomSerializer, TimetableSerializer, TimetableDetailSerializer,
    HolidaySerializer, SubstituteTeacherSerializer
)
from django.http import HttpResponse
import csv
from io import BytesIO
from django.db.models import Q, Count, Sum
from django.utils import timezone
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    pass  # reportlab is optional, PDF export will error if not installed
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets

logger = logging.getLogger(__name__)

class ClassListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
            classes = Class._default_manager.filter(tenant=profile.tenant)  # type: ignore
            serializer = ClassSerializer(classes, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in ClassListCreateView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = ClassSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ClassDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        try:
            c = Class._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            serializer = ClassSerializer(c)
            return Response(serializer.data)
        except Class._default_manager.model.DoesNotExist:  # type: ignore
            return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            c = Class._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = ClassSerializer(c, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Class._default_manager.model.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            c = Class._default_manager.get(id=pk, tenant=profile.tenant)
            c.delete()
            return Response({'message': 'Class deleted.'})
        except Class._default_manager.model.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

class StudentListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
            if profile.role and profile.role.name in ['admin', 'accountant', 'principal']:
                students = Student._default_manager.filter(tenant=profile.tenant)  # type: ignore
            else:
                # Staff/Teachers: only students in their assigned classes
                students = Student._default_manager.filter(tenant=profile.tenant, assigned_class__in=profile.assigned_classes.all())  # type: ignore
            # Filtering
            search = request.query_params.get('search')
            class_id = request.query_params.get('class')
            date_from = request.query_params.get('admission_date_from')
            date_to = request.query_params.get('admission_date_to')
            if search:
                students = students.filter(
                    (Q(name__icontains=search) | Q(email__icontains=search))
                )
            if class_id:
                students = students.filter(assigned_class_id=class_id)
            if date_from:
                students = students.filter(admission_date__gte=date_from)
            if date_to:
                students = students.filter(admission_date__lte=date_to)
            serializer = StudentSerializer(students, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in StudentListCreateView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_required('admin', 'principal', 'teacher', 'staff', 'accountant')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = StudentSerializer(data=data, context={'tenant': profile.tenant})
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StudentDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        try:
            s = Student._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            serializer = StudentSerializer(s)
            return Response(serializer.data)
        except Student.DoesNotExist:  # type: ignore
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        # Check role-based permissions
        user_role = profile.role.name if profile.role else None
        
        # Only admin, principal, teacher, staff, and accountant can update students
        if user_role not in ['admin', 'principal', 'teacher', 'staff', 'accountant']:
            return Response({'error': 'You do not have permission to update students.'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            s = Student._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            
            # Teachers and staff can only update students in their assigned classes
            if user_role in ['teacher', 'staff']:
                assigned_class_ids = list(profile.assigned_classes.values_list('id', flat=True))
                if not s.assigned_class or s.assigned_class.id not in assigned_class_ids:
                    return Response({'error': 'You can only update students in your assigned classes.'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = StudentSerializer(s, data=request.data, partial=True, context={'tenant': profile.tenant})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Student.DoesNotExist:  # type: ignore
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            s = Student._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            s.delete()
            return Response({'message': 'Student deleted.'})
        except Student.DoesNotExist:  # type: ignore
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

# TODO: Update Fee views to use new FeeStructure, FeePayment, FeeDiscount models
# class FeeListCreateView(APIView):
#     pass

# class FeeDetailView(APIView):
#     pass

class AttendanceListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
            if profile.role and profile.role.name == 'admin':
                attendance = Attendance._default_manager.filter(tenant=profile.tenant)  # type: ignore
            else:
                # Staff: only attendance for students in their assigned classes
                attendance = Attendance._default_manager.filter(tenant=profile.tenant, student__assigned_class__in=profile.assigned_classes.all())  # type: ignore
            serializer = AttendanceSerializer(attendance, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in AttendanceListCreateView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = AttendanceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AttendanceDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        try:
            a = Attendance._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            serializer = AttendanceSerializer(a)
            return Response(serializer.data)
        except Attendance.DoesNotExist:  # type: ignore
            return Response({'error': 'Attendance record not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'teacher')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            a = Attendance._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            serializer = AttendanceSerializer(a, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Attendance.DoesNotExist:  # type: ignore
            return Response({'error': 'Attendance record not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'teacher')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            a = Attendance._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            a.delete()
            return Response({'message': 'Attendance record deleted.'})
        except Attendance.DoesNotExist:  # type: ignore
            return Response({'error': 'Attendance record not found.'}, status=status.HTTP_404_NOT_FOUND)

class ReportCardListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
            reportcards = ReportCard._default_manager.filter(tenant=profile.tenant)
            serializer = ReportCardSerializer(reportcards, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in ReportCardListCreateView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        # Accept either *_id or plain FK keys and map to serializer fields
        if 'student' in data and 'student_id' not in data:
            data['student_id'] = data.get('student')
        if 'academic_year' in data and 'academic_year_id' not in data:
            data['academic_year_id'] = data.get('academic_year')
        if 'term' in data and 'term_id' not in data:
            data['term_id'] = data.get('term')
        if 'class_obj' in data and 'class_obj_id' not in data:
            data['class_obj_id'] = data.get('class_obj')
        # Handle uniqueness gracefully: upsert by (tenant, student, academic_year, term)
        serializer = ReportCardSerializer(data=data)
        if serializer.is_valid():
            student = serializer.validated_data.get('student')
            academic_year = serializer.validated_data.get('academic_year')
            term = serializer.validated_data.get('term')
            class_obj = serializer.validated_data.get('class_obj')
            # Try get_or_create
            from education.models import ReportCard as RC
            rc, created = RC._default_manager.get_or_create(
                tenant=profile.tenant,
                student=student,
                academic_year=academic_year,
                term=term,
                defaults={
                    'class_obj': class_obj,
                    'teacher_remarks': serializer.validated_data.get('teacher_remarks', ''),
                    'principal_remarks': serializer.validated_data.get('principal_remarks', ''),
                    'conduct_grade': serializer.validated_data.get('conduct_grade', ''),
                    'issued_date': serializer.validated_data.get('issued_date'),
                }
            )
            if not created:
                # Update optional fields if provided
                for f in ['class_obj', 'teacher_remarks', 'principal_remarks', 'conduct_grade', 'issued_date']:
                    val = serializer.validated_data.get(f, None)
                    if val is not None:
                        setattr(rc, f, val)
                rc.save()
            return Response(ReportCardSerializer(rc).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReportCardDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        try:
            r = ReportCard._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            serializer = ReportCardSerializer(r)
            return Response(serializer.data)
        except ReportCard.DoesNotExist:  # type: ignore
            return Response({'error': 'Report card not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'teacher')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            r = ReportCard._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            serializer = ReportCardSerializer(r, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ReportCard.DoesNotExist:  # type: ignore
            return Response({'error': 'Report card not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'teacher')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            r = ReportCard._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            r.delete()
            return Response({'message': 'Report card deleted.'})
        except ReportCard.DoesNotExist:  # type: ignore
            return Response({'error': 'Report card not found.'}, status=status.HTTP_404_NOT_FOUND)

# Academic Structure Views
class AcademicYearListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        academic_years = AcademicYear._default_manager.filter(tenant=profile.tenant)
        serializer = AcademicYearSerializer(academic_years, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = AcademicYearSerializer(data=data)
        if serializer.is_valid():
            # If this is set as current, unset others
            if data.get('is_current'):
                AcademicYear._default_manager.filter(tenant=profile.tenant).update(is_current=False)
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AcademicYearDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            ay = AcademicYear._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = AcademicYearSerializer(ay)
            return Response(serializer.data)
        except AcademicYear.DoesNotExist:
            return Response({'error': 'Academic year not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            ay = AcademicYear._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = AcademicYearSerializer(ay, data=request.data, partial=True)
            if serializer.is_valid():
                # If setting as current, unset others
                if request.data.get('is_current'):
                    AcademicYear._default_manager.filter(tenant=profile.tenant).exclude(id=pk).update(is_current=False)
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except AcademicYear.DoesNotExist:
            return Response({'error': 'Academic year not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            ay = AcademicYear._default_manager.get(id=pk, tenant=profile.tenant)
            ay.delete()
            return Response({'message': 'Academic year deleted.'})
        except AcademicYear.DoesNotExist:
            return Response({'error': 'Academic year not found.'}, status=status.HTTP_404_NOT_FOUND)

class TermListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        academic_year_id = request.query_params.get('academic_year')
        terms = Term._default_manager.filter(tenant=profile.tenant)
        if academic_year_id:
            terms = terms.filter(academic_year_id=academic_year_id)
        serializer = TermSerializer(terms, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = TermSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubjectListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        class_id = request.query_params.get('class')
        subjects = Subject._default_manager.filter(tenant=profile.tenant)
        if class_id:
            subjects = subjects.filter(class_obj_id=class_id)
        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = SubjectSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UnitListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        subject_id = request.query_params.get('subject')
        units = Unit._default_manager.filter(tenant=profile.tenant)
        if subject_id:
            units = units.filter(subject_id=subject_id)
        serializer = UnitSerializer(units, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            data = request.data.copy()
            data['tenant'] = profile.tenant.id
            serializer = UnitSerializer(data=data)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            logger.error(f"Unit creation validation error: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unit creation error: {str(e)}", exc_info=True)
            return Response({'error': f'Failed to create unit: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UnitDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            unit = Unit._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = UnitSerializer(unit)
            return Response(serializer.data)
        except Unit.DoesNotExist:
            return Response({'error': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'teacher')
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            unit = Unit._default_manager.get(id=pk, tenant=profile.tenant)
            data = request.data.copy()
            data['tenant'] = profile.tenant.id
            serializer = UnitSerializer(unit, data=data, partial=False)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Unit.DoesNotExist:
            return Response({'error': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Unit update error: {str(e)}", exc_info=True)
            return Response({'error': f'Failed to update unit: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_required('admin', 'principal', 'teacher')
    def patch(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            unit = Unit._default_manager.get(id=pk, tenant=profile.tenant)
            data = request.data.copy()
            data['tenant'] = profile.tenant.id
            serializer = UnitSerializer(unit, data=data, partial=True)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Unit.DoesNotExist:
            return Response({'error': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Unit update error: {str(e)}", exc_info=True)
            return Response({'error': f'Failed to update unit: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_required('admin', 'principal')
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            unit = Unit._default_manager.get(id=pk, tenant=profile.tenant)
            unit.delete()
            return Response({'message': 'Unit deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Unit.DoesNotExist:
            return Response({'error': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)

class AssessmentTypeListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            assessment_types = AssessmentType._default_manager.filter(tenant=profile.tenant)
            serializer = AssessmentTypeSerializer(assessment_types, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in AssessmentTypeListCreateView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = AssessmentTypeSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AssessmentListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        term_id = request.query_params.get('term')
        subject_id = request.query_params.get('subject')
        assessments = Assessment._default_manager.filter(tenant=profile.tenant)
        if term_id:
            assessments = assessments.filter(term_id=term_id)
        if subject_id:
            assessments = assessments.filter(subject_id=subject_id)
        serializer = AssessmentSerializer(assessments, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            data = request.data.copy()
            data['tenant'] = profile.tenant.id
            serializer = AssessmentSerializer(data=data)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            logger.error(f"Assessment creation validation error: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Assessment creation error: {str(e)}", exc_info=True)
            return Response({'error': f'Failed to create assessment: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MarksEntryListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        student_id = request.query_params.get('student')
        assessment_id = request.query_params.get('assessment')
        term_id = request.query_params.get('term')
        
        marks_entries = MarksEntry._default_manager.filter(tenant=profile.tenant)
        if student_id:
            marks_entries = marks_entries.filter(student_id=student_id)
        if assessment_id:
            marks_entries = marks_entries.filter(assessment_id=assessment_id)
        if term_id:
            marks_entries = marks_entries.filter(assessment__term_id=term_id)
        
        serializer = MarksEntrySerializer(marks_entries, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        data['entered_by'] = profile.id
        
        # Set max_marks from assessment if not provided
        if 'max_marks' not in data and 'assessment_id' in data:
            try:
                assessment = Assessment._default_manager.get(id=data['assessment_id'], tenant=profile.tenant)
                data['max_marks'] = assessment.max_marks
            except Assessment.DoesNotExist:
                pass
        
        serializer = MarksEntrySerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant, entered_by=profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MarksEntryDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            me = MarksEntry._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = MarksEntrySerializer(me)
            return Response(serializer.data)
        except MarksEntry.DoesNotExist:
            return Response({'error': 'Marks entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'teacher')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            me = MarksEntry._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = MarksEntrySerializer(me, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except MarksEntry.DoesNotExist:
            return Response({'error': 'Marks entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'teacher')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            me = MarksEntry._default_manager.get(id=pk, tenant=profile.tenant)
            me.delete()
            return Response({'message': 'Marks entry deleted.'})
        except MarksEntry.DoesNotExist:
            return Response({'error': 'Marks entry not found.'}, status=status.HTTP_404_NOT_FOUND)

class ReportCardGenerateView(APIView):
    """Generate or regenerate report card with auto-calculation"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        # Accept either *_id or plain FK keys
        student_id = data.get('student_id') or data.get('student')
        academic_year_id = data.get('academic_year_id') or data.get('academic_year')
        term_id = data.get('term_id') or data.get('term')
        
        if not all([student_id, academic_year_id, term_id]):
            return Response(
                {'error': 'student_id, academic_year_id, and term_id are required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student._default_manager.get(id=student_id, tenant=profile.tenant)
            academic_year = AcademicYear._default_manager.get(id=academic_year_id, tenant=profile.tenant)
            term = Term._default_manager.get(id=term_id, tenant=profile.tenant)
            class_obj = student.assigned_class
            
            if not class_obj:
                return Response(
                    {'error': 'Student must be assigned to a class.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create report card
            report_card, created = ReportCard._default_manager.get_or_create(
                tenant=profile.tenant,
                student=student,
                academic_year=academic_year,
                term=term,
                defaults={'class_obj': class_obj}
            )
            
            # Update class if changed
            if report_card.class_obj != class_obj:
                report_card.class_obj = class_obj
            
            # Auto-calculate totals
            report_card.calculate_totals()
            
            # Calculate rank
            from django.db.models import F, Window
            same_class_term = ReportCard._default_manager.filter(
                tenant=profile.tenant,
                academic_year=academic_year,
                term=term,
                class_obj=class_obj
            ).order_by('-percentage')
            
            rank = 1
            for rc in same_class_term:
                if rc.id == report_card.id:
                    report_card.rank_in_class = rank
                    report_card.save()
                    break
                rank += 1
            
            # Update remarks if provided
            if 'teacher_remarks' in data:
                report_card.teacher_remarks = data['teacher_remarks']
            if 'principal_remarks' in data:
                report_card.principal_remarks = data['principal_remarks']
            if 'conduct_grade' in data:
                report_card.conduct_grade = data['conduct_grade']
            if 'issued_date' in data:
                report_card.issued_date = data['issued_date']
            
            report_card.save()
            
            serializer = ReportCardSerializer(report_card)
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        except AcademicYear.DoesNotExist:
            return Response({'error': 'Academic year not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Term.DoesNotExist:
            return Response({'error': 'Term not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error generating report card: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportCardPDFView(APIView):
    """Generate PDF for a specific report card"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            report_card = ReportCard._default_manager.get(id=pk, tenant=profile.tenant)
        except ReportCard.DoesNotExist:
            return Response({'error': 'Report card not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error accessing report card: {str(e)}", exc_info=True)
            return Response({'error': f'Error accessing report card: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # Validate report card has required data
            if not report_card.student:
                return Response({'error': 'Report card missing student information.'}, status=status.HTTP_400_BAD_REQUEST)
            if not report_card.term:
                return Response({'error': 'Report card missing term information.'}, status=status.HTTP_400_BAD_REQUEST)
            if not report_card.academic_year:
                return Response({'error': 'Report card missing academic year information.'}, status=status.HTTP_400_BAD_REQUEST)
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from io import BytesIO

            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            # Classic border frame around entire page
            p.setStrokeColor(colors.HexColor('#1a237e'))
            p.setLineWidth(2)
            p.rect(15 * mm, 15 * mm, width - 30 * mm, height - 30 * mm, stroke=1, fill=0)
            
            # Inner decorative border
            p.setStrokeColor(colors.HexColor('#666666'))
            p.setLineWidth(0.5)
            p.rect(18 * mm, 18 * mm, width - 36 * mm, height - 36 * mm, stroke=1, fill=0)

            # Header with logo on LEFT and school name + info on RIGHT
            tenant = profile.tenant
            school_name = getattr(tenant, 'name', '') or 'School'
            
            # Get school contact information from admin user profile
            school_address = ''
            school_phone = ''
            school_email = ''
            try:
                # Get admin user profile for contact info
                admin_profile = UserProfile._default_manager.filter(
                    tenant=tenant, 
                    role__name='admin'
                ).first()
                if admin_profile:
                    school_address = admin_profile.address or ''
                    school_phone = admin_profile.phone or ''
                    school_email = admin_profile.user.email if admin_profile.user else ''
            except Exception:
                pass
            
            # OPTION: Remove logo completely for cleaner PDFs (or keep it small)
            # Set REMOVE_LOGO = True to remove logos from all PDFs
            REMOVE_LOGO = True  # Set to True to remove logos completely
            
            logo_drawn = False
            FIXED_TEXT_START_X = 25 * mm  # Text starts at left margin (no logo space needed)
            logo_y_top = height - 25 * mm  # Define logo_y_top regardless of REMOVE_LOGO
            
            if not REMOVE_LOGO and tenant.logo:
                try:
                    from PIL import Image
                    import os
                    logo_path = tenant.logo.path
                    if os.path.exists(logo_path):
                        img = Image.open(logo_path)
                        # Very small logo: max 15mm to avoid text overlap
                        max_height = 15 * mm
                        max_width = 15 * mm
                        img_width, img_height = img.size
                        scale = min(max_height / img_height, max_width / img_width, 1.0)
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        from reportlab.lib.utils import ImageReader
                        logo_reader = ImageReader(img)
                        # Logo at top-left corner, very small
                        logo_x = 25 * mm
                        logo_y_top = height - 25 * mm
                        logo_y = logo_y_top - new_height
                        p.drawImage(logo_reader, logo_x, logo_y, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
                        logo_drawn = True
                        # Adjust text start if logo is drawn
                        FIXED_TEXT_START_X = logo_x + new_width + 5 * mm
                except Exception as e:
                    logger.warning(f"Could not load tenant logo: {e}")
            
            # Text always starts at FIXED position
            p.setFillColor(colors.black)
            text_x = FIXED_TEXT_START_X  # Fixed position for text
            p.setFont('Helvetica-Bold', 20)
            school_y = logo_y_top
            p.drawString(text_x, school_y, school_name.upper())
            
            # School contact info below name
            info_y = school_y - 18
            p.setFont('Helvetica', 10)
            if school_address:
                max_addr_width = width - text_x - 25 * mm
                if p.stringWidth(school_address, 'Helvetica', 10) > max_addr_width:
                    addr_lines = [school_address[i:i+50] for i in range(0, min(len(school_address), 100), 50)]
                    for line in addr_lines[:2]:
                        p.drawString(text_x, info_y, line)
                        info_y -= 12
                else:
                    p.drawString(text_x, info_y, school_address)
                    info_y -= 12
            if school_phone:
                p.drawString(text_x, info_y, f"Phone: {school_phone}")
                info_y -= 12
            if school_email:
                p.drawString(text_x, info_y, f"Email: {school_email}")
                info_y -= 12
            
            # Document title below contact info
            info_y -= 5
            p.setFont('Helvetica-Bold', 12)
            p.drawString(text_x, info_y, 'OFFICIAL REPORT CARD')
            p.setFont('Helvetica', 10)
            academic_year_text = 'ACADEMIC YEAR ' + (report_card.academic_year.name if report_card.academic_year else '')
            p.drawString(text_x, info_y - 13, academic_year_text)
            
            # Separator line (simple border, no background)
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            y = height - 75
            p.line(20 * mm, y, width - 20 * mm, y)
            
            y -= 20
            p.setFillColor(colors.black)

            # Student information section - clean white background, no colors
            y = height - 90
            # Outer border only - no background color
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(22 * mm, y - 65, width - 44 * mm, 65, stroke=1, fill=0)
            # Simple header line (no background color)
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.line(22 * mm, y - 12, width - 22 * mm, y - 12)
            # Header text (black on white)
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 13)
            p.drawCentredString(width / 2, y - 7, 'STUDENT INFORMATION')
            
            y -= 18
            p.setFillColor(colors.black)
            
            # Student details in classic two-column layout - Government marksheet standard alignment
            p.setFillColor(colors.black)
            # Fixed-width columns for consistent alignment (like government marksheets)
            label_x = 25 * mm          # Fixed label position (left column)
            value_x = 95 * mm          # Fixed value position (consistent spacing)
            label_x2 = 130 * mm        # Fixed label position (right column)
            value_x2 = 170 * mm        # Fixed value position (consistent spacing)
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Full Name:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x, y, report_card.student.name.upper())
            
            roll_val = getattr(report_card.student, 'roll_number', None) or getattr(report_card.student, 'admission_number', None) or report_card.student.id
            upper_val = getattr(report_card.student, 'upper_id', None) or getattr(report_card.student, 'admission_number', None)
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Roll Number:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x2, y, str(roll_val))
            y -= 15
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Class:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x, y, report_card.class_obj.name if report_card.class_obj else 'N/A')
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Academic Year:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x2, y, report_card.academic_year.name if report_card.academic_year else 'N/A')
            y -= 15
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Term:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x, y, report_card.term.name if report_card.term else 'N/A')
            
            # Use generated_at safely
            gen_date = report_card.generated_at if hasattr(report_card, 'generated_at') and report_card.generated_at else (report_card.created_at if hasattr(report_card, 'created_at') and report_card.created_at else timezone.now())
            issued_str = report_card.issued_date.strftime('%d-%m-%Y') if report_card.issued_date else gen_date.strftime('%d-%m-%Y')
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Issued Date:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x2, y, issued_str)
            
            if upper_val:
                y -= 15
                p.setFont('Helvetica-Bold', 11)
                p.drawString(label_x, y, 'Student ID:')
                p.setFont('Helvetica', 11)
                p.drawString(value_x, y, upper_val)
            
            y -= 20

            # Classic styled marks table - with formal borders (FIXED COLUMNS TO PREVENT OVERFLOW)
            y -= 5
            # Get marks entries first to calculate table height
            from education.models import MarksEntry
            marks_entries = MarksEntry._default_manager.filter(
                tenant=report_card.tenant,
                student=report_card.student,
                assessment__term=report_card.term
            ).select_related('assessment', 'assessment__subject').order_by('assessment__subject__name')
            
            # Table outer border - calculate height based on entries
            table_height = len(marks_entries) * 14 + 15
            if table_height > y - 80:
                table_height = y - 80
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            # Ensure table fits within page margins
            table_left = 22 * mm
            table_right = width - 22 * mm
            table_width = table_right - table_left
            p.rect(table_left, y - table_height, table_width, table_height, stroke=1, fill=0)
            
            # Table header - no background color
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.line(table_left, y - 12, table_right, y - 12)
            
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 10)  # Slightly smaller font to fit better
            headers = ['SUBJECT', 'MARKS OBTAINED', 'MAX MARKS', 'PERCENTAGE']
            # FIXED column positions - properly calculated to fit within page margins
            # Page width margins: 22mm left, 22mm right = 44mm total margin
            # Available width = width - 44mm
            available_width = width - 44 * mm
            table_left = 22 * mm
            table_right = width - 22 * mm
            
            # Column positions - IMPROVED: Better calculation to prevent overflow
            # SUBJECT: flexible width (takes remaining space after fixed columns)
            # MARKS OBTAINED: 24mm (fixed)
            # MAX MARKS: 24mm (fixed)
            # PERCENTAGE: 24mm (fixed)
            # Total fixed columns = 72mm
            # Column spacing = 3mm between columns
            fixed_cols_width = 72 * mm
            col_spacing = 3 * mm
            subject_col_width = available_width - fixed_cols_width - (col_spacing * 3)  # Reserve space for 3 gaps
            
            # Ensure minimum subject column width
            if subject_col_width < 30 * mm:
                subject_col_width = 30 * mm
            
            # Calculate exact column positions from left edge
            # All columns aligned within table boundaries
            col_x = [
                table_left + 3 * mm,                           # SUBJECT (left-aligned, 3mm padding from left edge)
                table_left + subject_col_width + col_spacing,   # MARKS OBTAINED (starts after subject + gap)
                table_left + subject_col_width + 24 * mm + (col_spacing * 2),  # MAX MARKS
                table_left + subject_col_width + 48 * mm + (col_spacing * 3)   # PERCENTAGE
            ]
            
            # Validate rightmost column doesn't exceed table boundary
            if col_x[3] + 24 * mm > table_right - 3 * mm:
                # Adjust: reduce subject width to fit
                excess = (col_x[3] + 24 * mm) - (table_right - 3 * mm)
                subject_col_width = max(30 * mm, subject_col_width - excess - col_spacing)
                # Recalculate positions
                col_x = [
                    table_left + 3 * mm,
                    table_left + subject_col_width + col_spacing,
                    table_left + subject_col_width + 24 * mm + (col_spacing * 2),
                    table_left + subject_col_width + 48 * mm + (col_spacing * 3)
                ]
            
            col_widths = [
                subject_col_width,      # SUBJECT width (adjusted to fit)
                24 * mm,                # MARKS OBTAINED width
                24 * mm,                # MAX MARKS width
                24 * mm                 # PERCENTAGE width
            ]
            
            for i, htxt in enumerate(headers):
                if i == 0:
                    # Left align subject column header (truncate if too long)
                    max_subject_width = col_widths[0] - 3 * mm
                    if p.stringWidth(htxt, 'Helvetica-Bold', 10) > max_subject_width:
                        htxt = htxt[:15] + '...'
                    p.drawString(col_x[i], y - 8, htxt)
                else:
                    # Right align number column headers
                    p.drawRightString(col_x[i] + col_widths[i], y - 8, htxt)
            p.setFillColor(colors.black)
            y -= 15
            
            # Vertical column separators (fixed positions - match column boundaries)
            p.setStrokeColor(colors.HexColor('#cccccc'))
            p.setLineWidth(0.3)
            # Separators at column boundaries (between SUBJECT/MARKS, MARKS/MAX, MAX/PERCENTAGE)
            sep_positions = [
                col_x[1] - 1 * mm,  # Between SUBJECT and MARKS OBTAINED
                col_x[2] - 1 * mm,  # Between MARKS OBTAINED and MAX MARKS
                col_x[3] - 1 * mm   # Between MAX MARKS and PERCENTAGE
            ]
            for sep_x in sep_positions:
                p.line(sep_x, y, sep_x, y - table_height + 12)

            # Table rows - properly aligned within fixed columns
            p.setFont('Helvetica', 9)  # Slightly smaller font to prevent overflow
            row_num = 0
            for entry in marks_entries:
                if y < 80:
                    # New page - reset and redraw
                    p.showPage()
                    p.setStrokeColor(colors.HexColor('#1a237e'))
                    p.setLineWidth(2)
                    p.rect(15 * mm, 15 * mm, width - 30 * mm, height - 30 * mm, stroke=1, fill=0)
                    p.setStrokeColor(colors.HexColor('#666666'))
                    p.setLineWidth(0.5)
                    p.rect(18 * mm, 18 * mm, width - 36 * mm, height - 36 * mm, stroke=1, fill=0)
                    
                    # Redraw table header on new page
                    p.setStrokeColor(colors.HexColor('#000000'))
                    p.setLineWidth(1)
                    p.line(table_left, height - 40 - 12, table_right, height - 40 - 12)
                    p.setFillColor(colors.black)
                    p.setFont('Helvetica-Bold', 10)
                    for i, htxt in enumerate(headers):
                        if i == 0:
                            max_subject_width = col_widths[0] - 3 * mm
                            display_htxt = htxt[:15] + '...' if p.stringWidth(htxt, 'Helvetica-Bold', 10) > max_subject_width else htxt
                            p.drawString(col_x[i], height - 40 - 8, display_htxt)
                        else:
                            p.drawRightString(col_x[i] + col_widths[i], height - 40 - 8, htxt)
                    p.setFont('Helvetica', 9)
                    y = height - 40 - 15
                    row_num = 0
                
                subject_name = entry.assessment.subject.name if entry.assessment and entry.assessment.subject else 'N/A'
                percent = (float(entry.marks_obtained) / float(entry.max_marks) * 100) if entry.max_marks else 0
                
                # Row separator line
                p.setStrokeColor(colors.HexColor('#d0d0d0'))
                p.setLineWidth(0.5)
                p.line(table_left, y - 12, table_right, y - 12)
                p.setFillColor(colors.black)
                
                # IMPROVED: Truncate subject name to fit EXACTLY within column boundaries
                # Calculate available width more precisely (column width minus padding)
                max_subject_width = col_widths[0] - 6 * mm  # 3mm padding on each side
                display_subject = subject_name
                if p.stringWidth(subject_name, 'Helvetica', 9) > max_subject_width:
                    # Binary search for optimal truncation
                    low, high = 0, len(subject_name)
                    while low < high:
                        mid = (low + high + 1) // 2
                        test_name = subject_name[:mid]
                        if p.stringWidth(test_name, 'Helvetica', 9) <= max_subject_width - p.stringWidth('...', 'Helvetica', 9):
                            low = mid
                        else:
                            high = mid - 1
                    display_subject = subject_name[:low] + '...' if low < len(subject_name) else subject_name[:low]
                    # Final safety check - ensure it fits
                    if p.stringWidth(display_subject, 'Helvetica', 9) > max_subject_width:
                        display_subject = display_subject[:max(0, len(display_subject) - 3)] + '...'
                
                # Draw subject name - ensure it stays within column boundary
                subject_x = col_x[0] + 3 * mm  # 3mm padding from left edge
                subject_max_x = col_x[0] + col_widths[0] - 3 * mm  # Right boundary
                # Clamp to ensure it doesn't exceed column
                if p.stringWidth(display_subject, 'Helvetica', 9) + subject_x > subject_max_x:
                    display_subject = display_subject[:max(0, len(display_subject) - 5)] + '...'
                p.drawString(subject_x, y, display_subject)
                
                # Right align numbers - ensure they stay within column boundaries
                # Marks Obtained
                marks_str = str(int(float(entry.marks_obtained)))
                marks_col_right = col_x[1] + col_widths[1] - 3 * mm  # Right boundary with padding
                marks_col_left = col_x[1] + 2 * mm  # Left boundary with padding
                marks_width = p.stringWidth(marks_str, 'Helvetica', 9)
                # Truncate if too long (unlikely but safety check)
                if marks_width > col_widths[1] - 6 * mm:
                    marks_str = marks_str[:3] + '...'
                    marks_width = p.stringWidth(marks_str, 'Helvetica', 9)
                p.drawRightString(marks_col_right, y, marks_str)
                
                # Max Marks
                max_marks_str = str(int(float(entry.max_marks)))
                max_marks_col_right = col_x[2] + col_widths[2] - 3 * mm
                max_marks_width = p.stringWidth(max_marks_str, 'Helvetica', 9)
                if max_marks_width > col_widths[2] - 6 * mm:
                    max_marks_str = max_marks_str[:3] + '...'
                    max_marks_width = p.stringWidth(max_marks_str, 'Helvetica', 9)
                p.drawRightString(max_marks_col_right, y, max_marks_str)
                
                # Percentage - ensure it fits
                percent_str = f"{percent:.1f}%"
                percent_col_right = col_x[3] + col_widths[3] - 3 * mm
                percent_width = p.stringWidth(percent_str, 'Helvetica', 9)
                if percent_width > col_widths[3] - 6 * mm:
                    percent_str = f"{percent:.0f}%"  # Remove decimal if still too long
                    percent_width = p.stringWidth(percent_str, 'Helvetica', 9)
                # Final safety check
                if percent_width > col_widths[3] - 6 * mm:
                    percent_str = percent_str[:4]  # Just keep number
                p.drawRightString(percent_col_right, y, percent_str)
                y -= 14
                row_num += 1

            # Academic summary section - no background colors
            y -= 8
            # Outer border only
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(22 * mm, y - 55, width - 44 * mm, 55, stroke=1, fill=0)
            # Header line
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.line(22 * mm, y - 12, width - 22 * mm, y - 12)
            
            p.setFillColor(colors.black)  # Black text on white background
            p.setFont('Helvetica-Bold', 14)
            p.drawCentredString(width / 2, y - 7, 'ACADEMIC SUMMARY')
            y -= 18
            
            # Summary layout - black text on white
            p.setFillColor(colors.black)
            summary_items = [
                ('Total Marks', f"{float(report_card.total_marks)} / {float(report_card.max_total_marks)}"),
                ('Percentage', f"{float(report_card.percentage):.2f}%"),
                ('Grade', report_card.grade),
            ]
            if report_card.rank_in_class:
                summary_items.append(('Class Rank', f"#{report_card.rank_in_class}"))
            
            # IMPROVED: Better alignment for summary items - consistent spacing within margins
            # Use page width minus margins (22mm each side) to calculate safe positions
            available_summary_width = width - 44 * mm
            summary_start_x = 25 * mm
            summary_end_x = width - 25 * mm
            
            # IMPROVED: Better spacing and alignment to prevent text overlapping
            # Use two-column layout with proper spacing
            left_label_x = 30 * mm
            left_value_x = 95 * mm
            right_label_x = 130 * mm
            right_value_x = 170 * mm
            
            # Calculate row positions with proper vertical spacing
            row_height = 20  # Increased spacing between rows
            current_y = y
            
            for i, (label, value) in enumerate(summary_items):
                if i % 2 == 0:
                    # Left column (even indices)
                    label_x = left_label_x
                    value_x = left_value_x
                    row_y = current_y
                else:
                    # Right column (odd indices)
                    label_x = right_label_x
                    value_x = right_value_x
                    row_y = current_y
                
                # Draw label and value on same line
                p.setFont('Helvetica-Bold', 10)
                label_text = label + ':'
                # Ensure label doesn't exceed column boundary
                max_label_width = value_x - label_x - 5 * mm
                if p.stringWidth(label_text, 'Helvetica-Bold', 10) > max_label_width:
                    label_text = label_text[:15] + '...'
                p.drawString(label_x, row_y, label_text)
                
                # Draw value - ensure it doesn't exceed right margin
                p.setFont('Helvetica', 11)
                value_width = p.stringWidth(value, 'Helvetica', 11)
                max_value_x = width - 25 * mm
                if value_x + value_width > max_value_x:
                    value_x = max_value_x - value_width
                p.drawString(value_x, row_y, value)
                
                # Move to next row if we've filled both columns or this is the last item
                if i % 2 == 1 or i == len(summary_items) - 1:
                    current_y -= row_height
            
            p.setFillColor(colors.black)  # Switch back to black for rest
            y = current_y - 5  # Add extra spacing after summary

            # Attendance and Conduct - clean white background, no colors
            y -= 5
            # Outer border only - no background color
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(22 * mm, y - 45, width - 44 * mm, 45, stroke=1, fill=0)
            # Header line
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.line(22 * mm, y - 12, width - 22 * mm, y - 12)
            
            p.setFillColor(colors.black)  # Black text on white background
            p.setFont('Helvetica-Bold', 12)
            p.drawCentredString(width / 2, y - 7, 'ATTENDANCE & CONDUCT')
            y -= 18
            
            # IMPROVED: Better spacing to prevent overlapping
            # First row: Days Present and Days Absent
            p.setFont('Helvetica-Bold', 10)
            p.drawString(25 * mm, y, 'Days Present:')
            p.setFont('Helvetica', 10)
            present_val = str(report_card.days_present)
            p.drawString(90 * mm, y, present_val)  # Increased spacing
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(120 * mm, y, 'Days Absent:')  # Increased spacing from previous
            p.setFont('Helvetica', 10)
            absent_val = str(report_card.days_absent)
            p.drawString(170 * mm, y, absent_val)  # Increased spacing
            y -= 16  # Increased line spacing
            
            # Second row: Attendance Percentage and Conduct Grade
            p.setFont('Helvetica-Bold', 10)
            p.drawString(25 * mm, y, 'Attendance Percentage:')
            p.setFont('Helvetica', 10)
            att_percent = f"{float(report_card.attendance_percentage):.2f}%"
            p.drawString(100 * mm, y, att_percent)  # Increased spacing
            
            if report_card.conduct_grade:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(150 * mm, y, 'Conduct Grade:')  # Increased spacing
                p.setFont('Helvetica', 10)
                p.drawString(175 * mm, y, report_card.conduct_grade)
            y -= 25  # Increased spacing after section

            # Remarks section - clean white background
            if report_card.teacher_remarks or report_card.principal_remarks:
                remarks_height = 0
                if report_card.teacher_remarks:
                    remarks_height += (len(report_card.teacher_remarks) // 95 + 1) * 12 + 20
                if report_card.principal_remarks:
                    remarks_height += (len(report_card.principal_remarks) // 95 + 1) * 12 + 20
                
                # Border only - no background color
                p.setStrokeColor(colors.HexColor('#000000'))
                p.setLineWidth(1)
                p.rect(22 * mm, y - remarks_height - 15, width - 44 * mm, remarks_height + 15, stroke=1, fill=0)
                # Header line
                p.setStrokeColor(colors.HexColor('#000000'))
                p.setLineWidth(1)
                p.line(22 * mm, y - 12, width - 22 * mm, y - 12)
                p.setFillColor(colors.black)
                p.setFont('Helvetica-Bold', 12)
                p.drawCentredString(width / 2, y - 7, 'REMARKS')
                y -= 18
                
                p.setFont('Helvetica', 10)
                # IMPROVED: Better text wrapping that respects word boundaries
                def wrap_text(text, max_width_mm):
                    """Wrap text at word boundaries to fit within max_width_mm"""
                    if not text:
                        return []
                    words = text.split()
                    lines = []
                    current_line = ''
                    max_width = max_width_mm
                    
                    for word in words:
                        test_line = current_line + (' ' if current_line else '') + word
                        test_width = p.stringWidth(test_line, 'Helvetica', 9)
                        if test_width <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                            # If single word is too long, truncate it
                            if p.stringWidth(word, 'Helvetica', 9) > max_width:
                                # Truncate word to fit
                                while p.stringWidth(current_line, 'Helvetica', 9) > max_width and len(current_line) > 1:
                                    current_line = current_line[:-1]
                                current_line += '...'
                    if current_line:
                        lines.append(current_line)
                    return lines
                
                max_remarks_width = width - 50 * mm  # Available width for remarks
                
                if report_card.teacher_remarks:
                    p.setFont('Helvetica-Bold', 10)
                    p.drawString(25 * mm, y, 'Class Teacher:')
                    y -= 14  # Increased spacing
                    p.setFont('Helvetica', 9)
                    remarks_lines = wrap_text(report_card.teacher_remarks, max_remarks_width)
                    for line in remarks_lines[:5]:  # Limit to 5 lines
                        if y < 60:  # Prevent overflow to footer
                            break
                        p.drawString(25 * mm, y, line)
                        y -= 12  # Consistent line spacing
                    y -= 8  # Extra spacing after section
                
                if report_card.principal_remarks:
                    p.setFont('Helvetica-Bold', 10)
                    p.drawString(25 * mm, y, 'Principal:')
                    y -= 14  # Increased spacing
                    p.setFont('Helvetica', 9)
                    remarks_lines = wrap_text(report_card.principal_remarks, max_remarks_width)
                    for line in remarks_lines[:5]:  # Limit to 5 lines
                        if y < 60:  # Prevent overflow to footer
                            break
                        p.drawString(25 * mm, y, line)
                        y -= 12  # Consistent line spacing
                y -= 10  # Extra spacing after section

            # Signature section - clean white background, no colors
            sig_y_start = 25 * mm
            sig_height = 40 * mm
            # Outer border only - no background color
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(22 * mm, sig_y_start, width - 44 * mm, sig_height, stroke=1, fill=0)
            # Header line
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.line(22 * mm, sig_y_start + sig_height - 12, width - 22 * mm, sig_y_start + sig_height - 12)
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 10)
            p.drawCentredString(width / 2, sig_y_start + sig_height - 7, 'AUTHENTICATION')
            
            # Signature lines with labels - formal style
            p.setStrokeColor(colors.black)
            p.setLineWidth(1)
            sig_line_y = sig_y_start + 22 * mm
            
            # Class Teacher signature box
            p.setStrokeColor(colors.HexColor('#666666'))
            p.setLineWidth(0.5)
            p.rect(30 * mm, sig_line_y - 8, 50 * mm, 20 * mm, stroke=1, fill=0)
            p.line(30 * mm, sig_line_y + 4, 80 * mm, sig_line_y + 4)
            p.setFont('Helvetica-Bold', 9)
            p.setFillColor(colors.black)
            p.drawString(32 * mm, sig_line_y + 8, 'Class Teacher')
            p.setFont('Helvetica', 7)
            p.drawString(32 * mm, sig_line_y - 3, '(Signature & Seal)')
            
            # Principal signature box
            p.rect(120 * mm, sig_line_y - 8, 50 * mm, 20 * mm, stroke=1, fill=0)
            p.line(120 * mm, sig_line_y + 4, 170 * mm, sig_line_y + 4)
            p.setFont('Helvetica-Bold', 9)
            p.drawString(122 * mm, sig_line_y + 8, 'Principal')
            p.setFont('Helvetica', 7)
            p.drawString(122 * mm, sig_line_y - 3, '(Signature & Seal)')
            
            # Footer with classic styling
            p.setFont('Helvetica', 8)
            p.setFillColor(colors.black)
            # Use created_at or current time if generated_at doesn't exist
            gen_date = report_card.generated_at if hasattr(report_card, 'generated_at') and report_card.generated_at else (report_card.created_at if hasattr(report_card, 'created_at') and report_card.created_at else timezone.now())
            footer_text = f"Generated on {gen_date.strftime('%d-%m-%Y at %I:%M %p')} — {school_name.upper()}"
            p.drawCentredString(width / 2, 20 * mm, footer_text)
            p.setFont('Helvetica-Oblique', 7)
            p.drawCentredString(width / 2, 15 * mm, 'This is a computer-generated document and does not require a physical signature.')

            p.showPage()
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="report_card_{report_card.student.name}_{report_card.id}.pdf"'
            return response
        except ImportError as e:
            logger.error(f"PDF generation import error: {str(e)}", exc_info=True)
            return Response({
                'error': 'PDF generation library not installed.',
                'details': 'Install required packages: pip install reportlab Pillow',
                'missing': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
            return Response({
                'error': f'PDF generation failed: {str(e)}',
                'details': 'Check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting user profile in StudentExportView: {str(e)}", exc_info=True)
            return Response({'error': 'An error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        students = Student._default_manager.filter(tenant=profile.tenant)
        # Filtering (same as list)
        search = request.query_params.get('search')
        class_id = request.query_params.get('class')
        date_from = request.query_params.get('admission_date_from')
        date_to = request.query_params.get('admission_date_to')
        if search:
            students = students.filter(
                (Q(name__icontains=search) | Q(email__icontains=search))
            )
        if class_id:
            students = students.filter(assigned_class_id=class_id)
        if date_from:
            students = students.filter(admission_date__gte=date_from)
        if date_to:
            students = students.filter(admission_date__lte=date_to)
        export_format = request.query_params.get('format', 'csv').lower()
        if export_format == 'pdf':
            # PDF export
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Student List")
                y -= 30
                p.setFont("Helvetica", 10)
                headers = ["ID", "Name", "Email", "Admission Date", "Assigned Class"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*120, y, h)
                y -= 20
                for s in students:
                    row = [
                        str(s.id),
                        s.name,
                        s.email,
                        s.admission_date.strftime('%Y-%m-%d'),
                        s.assigned_class.name if s.assigned_class else ""
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*120, y, val)
                    y -= 18
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="students.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            # CSV export
            try:
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="students.csv"'
                writer = csv.writer(response)
                # Include new fields: Aadhaar, Father, Mother details
                writer.writerow([
                    "ID", "Name", "Email", "Admission Date", "Assigned Class",
                    "Aadhaar UID", "Father Name", "Father Aadhaar", "Mother Name", "Mother Aadhaar",
                    "Phone", "Address", "Date of Birth", "Gender"
                ])
                for s in students:
                    writer.writerow([
                        s.id,
                        s.name,
                        s.email,
                        s.admission_date.strftime('%Y-%m-%d') if s.admission_date else "",
                        s.assigned_class.name if s.assigned_class else "",
                        getattr(s, 'aadhaar_uid', '') or "",
                        getattr(s, 'father_name', '') or "",
                        getattr(s, 'father_aadhaar', '') or "",
                        getattr(s, 'mother_name', '') or "",
                        getattr(s, 'mother_aadhaar', '') or "",
                        s.phone or "",
                        s.address or "",
                        s.date_of_birth.strftime('%Y-%m-%d') if s.date_of_birth else "",
                        s.gender or ""
                    ])
                return response
            except Exception as e:
                logger.error(f"Error in CSV export: {str(e)}", exc_info=True)
                return Response({'error': f'CSV export failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

class ClassFeeStructureListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
            # Allow admin, accountant, principal, and teacher to view fee structures (read-only for teachers)
            if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal', 'teacher']:
                return Response({'error': 'You do not have permission to view fee structures.'}, status=status.HTTP_403_FORBIDDEN)
            fee_structures = FeeStructure._default_manager.filter(tenant=profile.tenant)  # type: ignore
            serializer = FeeStructureSerializer(fee_structures, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in ClassFeeStructureListCreateView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        if not profile.role or profile.role.name != 'admin':
            return Response({'error': 'Only admins can create fee structures.'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = FeeStructureSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ClassFeeStructureDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        if not profile.role or profile.role.name != 'admin':
            return Response({'error': 'Only admins can update fee structures.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            fee_structure = FeeStructure._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
        except Exception:
            return Response({'error': 'Fee structure not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = FeeStructureSerializer(fee_structure, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        if not profile.role or profile.role.name != 'admin':
            return Response({'error': 'Only admins can delete fee structures.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            fee_structure = FeeStructure._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            fee_structure.delete()
            return Response({'message': 'Fee structure deleted.'})
        except Exception:
            return Response({'error': 'Fee structure not found.'}, status=status.HTTP_404_NOT_FOUND) 

class StaffAttendanceListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
            if profile.role and profile.role.name == 'admin':
                # Admin can filter by staff, class, date
                staff_id = request.query_params.get('staff')
                class_id = request.query_params.get('class')
                date = request.query_params.get('date')
                qs = StaffAttendance._default_manager.filter(tenant=profile.tenant)  # type: ignore
                if staff_id:
                    qs = qs.filter(staff_id=staff_id)
                if class_id:
                    qs = qs.filter(staff__assigned_classes__id=class_id)
                if date:
                    qs = qs.filter(date=date)
                qs = qs.distinct()
            else:
                # Staff can only see their own
                qs = StaffAttendance._default_manager.filter(tenant=profile.tenant, staff=profile)  # type: ignore
            serializer = StaffAttendanceSerializer(qs, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in StaffAttendanceListCreateView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_exclude('student')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
            print(f"DEBUG: User profile found: {profile.id} - {profile.user.username}")
            logger.info(f"User profile found: {profile.id} - {profile.user.username}")
        except Exception as e:
            print(f"DEBUG: Error getting user profile: {e}")
            logger.error(f"Error getting user profile: {e}")
            return Response({'error': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        
        # Debug: Log incoming data
        print(f"DEBUG: Incoming data: {data}")
        logger.info(f"Incoming data: {data}")
        
        # No need to convert staff_id - serializer handles it directly
        print(f"DEBUG: Using staff_id directly from request data")
        logger.info(f"Using staff_id directly from request data")
        
        # Debug: Log processed data
        print(f"DEBUG: Processed data: {data}")
        logger.info(f"Processed data: {data}")
        
        # Only admin can create for others, staff can only create for self
        if profile.role and profile.role.name == 'admin':
            if not data.get('staff_id'):
                return Response({'error': 'Staff ID required.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            data['staff_id'] = profile.id
        
        # Debug: Log final data before serialization
        print(f"DEBUG: Final data before serialization: {data}")
        logger.info(f"Final data before serialization: {data}")
        
        # Check if the staff user exists
        staff_id_to_check = data.get('staff_id')
        if staff_id_to_check:
            try:
                staff_user = UserProfile._default_manager.get(id=staff_id_to_check)
                print(f"DEBUG: Staff user found: {staff_user.id} - {staff_user.user.username} - Tenant: {staff_user.tenant.id}")
                logger.info(f"Staff user found: {staff_user.id} - {staff_user.user.username} - Tenant: {staff_user.tenant.id}")
            except UserProfile._default_manager.model.DoesNotExist:
                print(f"DEBUG: Staff user with ID {staff_id_to_check} does not exist!")
                logger.error(f"Staff user with ID {staff_id_to_check} does not exist!")
                return Response({'error': f'Staff user with ID {staff_id_to_check} does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Double-check that staff field is not present (we use staff_id)
        if 'staff' in data:
            print(f"DEBUG: staff field found in data, removing: {data}")
            logger.warning(f"staff field found in data, removing: {data}")
            data.pop('staff', None)
        
        try:
            serializer = StaffAttendanceSerializer(data=data, context={'request': request})
            print(f"DEBUG: Serializer created with data: {data}")
            logger.info(f"Serializer created with data: {data}")
            
            if serializer.is_valid():
                print("DEBUG: Serializer is valid, saving...")
                logger.info("Serializer is valid, saving...")
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                print(f"DEBUG: Serializer errors: {serializer.errors}")
                logger.error(f"Serializer errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"DEBUG: Exception in serializer: {e}")
            logger.error(f"Exception in serializer: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class StaffAttendanceDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        try:
            att = StaffAttendance._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
        except StaffAttendance.DoesNotExist:  # type: ignore
            return Response({'error': 'Attendance record not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Only admin or the staff themselves can update
        if not (profile.role and profile.role.name == 'admin') and att.staff != profile:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = StaffAttendanceSerializer(att, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        try:
            att = StaffAttendance._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
        except StaffAttendance.DoesNotExist:  # type: ignore
            return Response({'error': 'Attendance record not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Only admin or the staff themselves can update
        if not (profile.role and profile.role.name == 'admin') and att.staff != profile:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = StaffAttendanceSerializer(att, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        try:
            att = StaffAttendance._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
        except StaffAttendance.DoesNotExist:  # type: ignore
            return Response({'error': 'Attendance record not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Only admin or the staff themselves can delete
        if not (profile.role and profile.role.name == 'admin') and att.staff != profile:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        att.delete()
        return Response({'message': 'Attendance record deleted.'})

class AdminEducationSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can view admin summary.'}, status=status.HTTP_403_FORBIDDEN)
        tenant = profile.tenant
        total_students = Student._default_manager.filter(tenant=tenant).count()  # type: ignore
        total_staff = UserProfile._default_manager.filter(tenant=tenant).exclude(role__name='student').count()  # type: ignore
        total_fees = FeePayment._default_manager.filter(tenant=tenant).count()  # type: ignore
        fees_paid = FeePayment._default_manager.filter(tenant=tenant).count()  # type: ignore
        fees_unpaid = 0  # We'll calculate this differently since FeePayment doesn't have a paid field
        today = timezone.now().date()
        staff_present = StaffAttendance._default_manager.filter(tenant=tenant, date=today, check_in_time__isnull=False).count()  # type: ignore
        staff_absent = UserProfile._default_manager.filter(tenant=tenant).exclude(role__name='student').count() - staff_present  # type: ignore
        student_present = Attendance._default_manager.filter(tenant=tenant, date=today, present=True).count()  # type: ignore
        student_absent = total_students - student_present
        data = {
            'total_students': total_students,
            'total_staff': total_staff,
            'total_fees': total_fees,
            'fees_paid': fees_paid,
            'fees_unpaid': fees_unpaid,
            'staff_present_today': staff_present,
            'staff_absent_today': staff_absent,
            'student_present_today': student_present,
            'student_absent_today': student_absent,
        }
        return Response(data) 

class ClassStatsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can view class stats.'}, status=status.HTTP_403_FORBIDDEN)
        tenant = profile.tenant
        classes = Class._default_manager.filter(tenant=tenant)  # type: ignore
        data = []
        for c in classes:
            student_count = Student._default_manager.filter(tenant=tenant, assigned_class=c).count()  # type: ignore
            staff_count = UserProfile._default_manager.filter(tenant=tenant, assigned_classes=c).count()  # type: ignore
            fees_total = FeePayment._default_manager.filter(tenant=tenant, student__assigned_class=c).aggregate(total=Sum('amount_paid'))['total'] or 0  # type: ignore
            fees_paid = FeePayment._default_manager.filter(tenant=tenant, student__assigned_class=c).aggregate(total=Sum('amount_paid'))['total'] or 0  # type: ignore
            fees_unpaid = 0  # Calculate based on FeeStructure vs FeePayment difference
            data.append({
                'class_id': c.id,
                'class_name': c.name,
                'student_count': student_count,
                'staff_count': staff_count,
                'fees_total': fees_total,
                'fees_paid': fees_paid,
                'fees_unpaid': fees_unpaid,
            })
        return Response(data)

class MonthlyReportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can view monthly reports.'}, status=status.HTTP_403_FORBIDDEN)
        tenant = profile.tenant
        month = request.query_params.get('month')  # format: YYYY-MM
        if not month:
            return Response({'error': 'Month parameter required (YYYY-MM).'}, status=status.HTTP_400_BAD_REQUEST)
        year, month_num = map(int, month.split('-'))
        from datetime import date
        from calendar import monthrange
        start_date = date(year, month_num, 1)
        end_date = date(year, month_num, monthrange(year, month_num)[1])
        students = Student._default_manager.filter(tenant=tenant, admission_date__range=(start_date, end_date)).count()  # type: ignore
        fees_collected = FeePayment._default_manager.filter(tenant=tenant, payment_date__range=(start_date, end_date)).aggregate(total=Sum('amount_paid'))['total'] or 0  # type: ignore
        staff_attendance = StaffAttendance._default_manager.filter(tenant=tenant, date__range=(start_date, end_date), check_in_time__isnull=False).count()  # type: ignore
        student_attendance = Attendance._default_manager.filter(tenant=tenant, date__range=(start_date, end_date), present=True).count()  # type: ignore
        return Response({
            'month': month,
            'new_students': students,
            'fees_collected': fees_collected,
            'staff_attendance_records': staff_attendance,
            'student_attendance_records': student_attendance,
        }) 

class ExportClassStatsCSVView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]
    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can export class stats.'}, status=status.HTTP_403_FORBIDDEN)
        tenant = profile.tenant
        classes = Class._default_manager.filter(tenant=tenant)  # type: ignore
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="class_stats.csv"'
        writer = csv.writer(response)
        writer.writerow(['Class', 'Students', 'Staff', 'Total Fees', 'Paid', 'Unpaid'])
        for c in classes:
            student_count = Student._default_manager.filter(tenant=tenant, assigned_class=c).count()  # type: ignore
            staff_count = UserProfile._default_manager.filter(tenant=tenant, assigned_classes=c).count()  # type: ignore
            fees_total = FeePayment._default_manager.filter(tenant=tenant, student__assigned_class=c).aggregate(total=Sum('amount_paid'))['total'] or 0  # type: ignore
            fees_paid = FeePayment._default_manager.filter(tenant=tenant, student__assigned_class=c).aggregate(total=Sum('amount_paid'))['total'] or 0  # type: ignore
            fees_unpaid = 0  # Calculate based on FeeStructure vs FeePayment difference
            writer.writerow([c.name, student_count, staff_count, fees_total, fees_paid, fees_unpaid])
        return response

class ExportMonthlyReportCSVView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can export monthly reports.'}, status=status.HTTP_403_FORBIDDEN)
        tenant = profile.tenant
        month = request.query_params.get('month')  # format: YYYY-MM
        if not month:
            return Response({'error': 'Month parameter required (YYYY-MM).'}, status=status.HTTP_400_BAD_REQUEST)
        year, month_num = map(int, month.split('-'))
        from datetime import date
        from calendar import monthrange
        start_date = date(year, month_num, 1)
        end_date = date(year, month_num, monthrange(year, month_num)[1])
        students = Student._default_manager.filter(tenant=tenant, admission_date__range=(start_date, end_date)).count()  # type: ignore
        fees_collected = FeePayment._default_manager.filter(tenant=tenant, payment_date__range=(start_date, end_date)).aggregate(total=Sum('amount_paid'))['total'] or 0  # type: ignore
        staff_attendance = StaffAttendance._default_manager.filter(tenant=tenant, date__range=(start_date, end_date), check_in_time__isnull=False).count()  # type: ignore
        student_attendance = Attendance._default_manager.filter(tenant=tenant, date__range=(start_date, end_date), present=True).count()  # type: ignore
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="monthly_report_{month}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Month', 'New Students', 'Fees Collected', 'Staff Attendance Records', 'Student Attendance Records'])
        writer.writerow([month, students, fees_collected, staff_attendance, student_attendance])
        return response 

class StaffListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        # Optionally filter by role if you want only staff/teachers
        staff = UserProfile._default_manager.filter(tenant=profile.tenant, role__name__in=['staff', 'teacher'])
        data = [{"id": s.id, "name": s.user.get_full_name() or s.user.username} for s in staff]
        return Response(data)

class StudentListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100 

class StaffAttendanceCheckInView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        today = timezone.now().date()
        # Check if already checked in
        attendance, created = StaffAttendance.objects.get_or_create(
            staff=profile,
            date=today,
            tenant=profile.tenant,
            defaults={"check_in_time": timezone.now()}
        )
        if not created:
            return Response({"message": "Already checked in today.", "attendance": StaffAttendanceSerializer(attendance).data}, status=200)
        return Response({"message": "Checked in successfully.", "attendance": StaffAttendanceSerializer(attendance).data}, status=201)

class StaffAttendanceCheckOutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        staff_id = request.data.get('staff_id')
        if not staff_id:
            return Response({'error': 'staff_id is required.'}, status=400)
        staff = UserProfile._default_manager.filter(id=staff_id, tenant=profile.tenant).first()
        if not staff:
            return Response({'error': 'Staff not found.'}, status=404)
        today = timezone.now().date()
        attendance = StaffAttendance._default_manager.filter(
            staff=staff, date=today, tenant=profile.tenant
        ).first()
        if not attendance or not attendance.check_in_time:
            return Response({'error': 'Not checked in yet.'}, status=400)
        if attendance.check_out_time:
            return Response({'error': 'Already checked out.'}, status=400)
        attendance.check_out_time = timezone.now()
        attendance.save()
        return Response({'message': 'Checked out successfully.'})

class EducationDepartmentListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        # Allow admin, principal, and teacher to view departments (read-only for teachers)
        if not profile.role or profile.role.name not in ['admin', 'principal', 'teacher', 'staff']:
            return Response({'error': 'You do not have permission to view departments.'}, status=status.HTTP_403_FORBIDDEN)
        departments = Department._default_manager.filter(tenant=profile.tenant)
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = DepartmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FeePaymentListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        if profile.role and profile.role.name in ['admin', 'accountant', 'principal']:
            # Admin/Accountant/Principal can see all fee payments
            payments = FeePayment._default_manager.filter(tenant=profile.tenant)
        else:
            # Staff/teachers can only see payments for their assigned classes
            payments = FeePayment._default_manager.filter(tenant=profile.tenant, student__assigned_class__in=profile.assigned_classes.all())
        serializer = FeePaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal', 'teacher', 'accountant')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = FeePaymentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FeePaymentDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            payment = FeePayment._default_manager.get(id=pk, tenant=profile.tenant)
        except Exception:
            return Response({'error': 'Fee payment not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = FeePaymentSerializer(payment)
        return Response(serializer.data)

    @role_required('admin', 'principal', 'teacher', 'accountant')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            payment = FeePayment._default_manager.get(id=pk, tenant=profile.tenant)
        except Exception:
            return Response({'error': 'Fee payment not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = FeePaymentSerializer(payment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @role_required('admin', 'principal', 'teacher', 'accountant')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            payment = FeePayment._default_manager.get(id=pk, tenant=profile.tenant)
        except Exception:
            return Response({'error': 'Fee payment not found.'}, status=status.HTTP_404_NOT_FOUND)
        payment.delete()
        return Response({'message': 'Fee payment deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)

class FeePaymentReceiptPDFView(APIView):
    """Generate PDF receipt for a fee payment"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            payment = FeePayment._default_manager.get(id=pk, tenant=profile.tenant)
        except FeePayment.DoesNotExist:
            return Response({'error': 'Fee payment not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from io import BytesIO

            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            # Get tenant info
            tenant = profile.tenant
            school_name = getattr(tenant, 'name', '') or 'School'
            
            # Get school contact information from admin user profile
            school_address = ''
            school_phone = ''
            school_email = ''
            try:
                # Get admin user profile for contact info
                admin_profile = UserProfile._default_manager.filter(
                    tenant=tenant, 
                    role__name='admin'
                ).first()
                if admin_profile:
                    school_address = admin_profile.address or ''
                    school_phone = admin_profile.phone or ''
                    school_email = admin_profile.user.email if admin_profile.user else ''
            except Exception:
                pass
            
            # OPTION: Remove logo completely for cleaner PDFs (or keep it small)
            REMOVE_LOGO = True  # Set to True to remove logos completely
            
            logo_drawn = False
            FIXED_TEXT_START_X = 25 * mm  # Text starts at left margin (no logo space needed)
            logo_y_top = height - 25 * mm
            
            if not REMOVE_LOGO and tenant.logo:
                try:
                    from PIL import Image
                    import os
                    logo_path = tenant.logo.path
                    if os.path.exists(logo_path):
                        img = Image.open(logo_path)
                        # Very small logo: max 15mm to avoid text overlap
                        max_height = 15 * mm
                        max_width = 15 * mm
                        img_width, img_height = img.size
                        scale = min(max_height / img_height, max_width / img_width, 1.0)
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        from reportlab.lib.utils import ImageReader
                        logo_reader = ImageReader(img)
                        # Logo at top-left corner, very small
                        logo_x = 25 * mm
                        logo_y = logo_y_top - new_height
                        p.drawImage(logo_reader, logo_x, logo_y, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
                        logo_drawn = True
                        # Adjust text start if logo is drawn
                        FIXED_TEXT_START_X = logo_x + new_width + 5 * mm
                except Exception as e:
                    logger.warning(f"Could not load tenant logo: {e}")
            
            # Text always starts at FIXED position
            p.setFillColor(colors.black)
            text_x = FIXED_TEXT_START_X  # Fixed position for text
            p.setFont('Helvetica-Bold', 18)
            school_y = logo_y_top
            p.drawString(text_x, school_y, school_name.upper())
            
            # School contact info below name - IMPROVED SPACING
            info_y = school_y - 20  # Increased spacing from school name
            p.setFont('Helvetica', 9)
            if school_address:
                max_addr_width = width - text_x - 25 * mm
                if p.stringWidth(school_address, 'Helvetica', 9) > max_addr_width:
                    addr_lines = [school_address[i:i+50] for i in range(0, min(len(school_address), 100), 50)]
                    for line in addr_lines[:2]:
                        p.drawString(text_x, info_y, line)
                        info_y -= 12  # Consistent line spacing
                else:
                    p.drawString(text_x, info_y, school_address)
                    info_y -= 12  # Consistent line spacing
            if school_phone:
                p.drawString(text_x, info_y, f"Phone: {school_phone}")
                info_y -= 12  # Consistent line spacing
            if school_email:
                p.drawString(text_x, info_y, f"Email: {school_email}")
                info_y -= 12  # Consistent line spacing
            
            # Document title below contact info - IMPROVED SPACING
            info_y -= 10  # Increased spacing before title
            p.setFont('Helvetica-Bold', 14)
            p.drawString(text_x, info_y, 'FEE PAYMENT RECEIPT')
            
            y = info_y - 25  # Start receipt details section with proper spacing
            p.setFillColor(colors.black)

            # Receipt number and date section - IMPROVED SPACING AND LAYOUT
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(20 * mm, y - 40, width - 40 * mm, 40, stroke=1, fill=0)  # Increased height for better spacing
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 10, 'RECEIPT DETAILS')  # Adjusted position
            y -= 20  # Increased spacing after header
            
            receipt_number = payment.receipt_number or f"RCP-{payment.id:08X}"
            payment_date = payment.payment_date.strftime('%d/%m/%Y')
            
            # IMPROVED: Better alignment with more spacing
            receipt_label_x = 25 * mm
            receipt_value_x = 105 * mm  # Increased spacing
            date_label_x = 140 * mm  # Increased spacing
            date_value_x = 175 * mm  # Increased spacing
            
            p.setFont('Helvetica-Bold', 11)
            p.drawString(receipt_label_x, y, 'Receipt Number:')
            p.setFont('Helvetica', 11)
            p.drawString(receipt_value_x, y, receipt_number)
            
            p.setFont('Helvetica-Bold', 11)
            p.drawString(date_label_x, y, 'Date:')
            p.setFont('Helvetica', 11)
            p.drawString(date_value_x, y, payment_date)
            y -= 20  # Increased spacing after section

            # Student information section - IMPROVED SPACING AND LAYOUT
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            p.rect(20 * mm, y - 55, width - 40 * mm, 55, stroke=1, fill=0)  # Increased height
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 10, 'STUDENT INFORMATION')  # Adjusted position
            y -= 20  # Increased spacing after header
            
            student_name = payment.student.name if payment.student else 'N/A'
            roll_number = getattr(payment.student, 'roll_number', None) or getattr(payment.student, 'admission_number', None) or getattr(payment.student, 'upper_id', None) or 'N/A'
            class_name = payment.student.assigned_class.name if payment.student and payment.student.assigned_class else 'N/A'
            
            # IMPROVED: Better alignment with proper spacing to prevent overlapping
            label_x = 25 * mm          # Fixed label position (left column)
            value_x = 100 * mm          # Increased spacing for values
            label_x2 = 140 * mm         # Increased spacing for right column
            value_x2 = 175 * mm         # Increased spacing for right column values (reduced to prevent overflow)
            
            # First row: Student Name and Roll Number
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Student Name:')
            p.setFont('Helvetica', 10)
            # Truncate if too long to prevent overflow
            name_text = student_name.upper()
            max_name_width = label_x2 - value_x - 10 * mm  # Available space between columns
            if p.stringWidth(name_text, 'Helvetica', 10) > max_name_width:
                # Truncate name to fit
                while p.stringWidth(name_text, 'Helvetica', 10) > max_name_width and len(name_text) > 1:
                    name_text = name_text[:-1]
                name_text = name_text.rstrip() + '...'
            p.drawString(value_x, y, name_text)
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Roll Number:')
            p.setFont('Helvetica', 10)
            roll_text = str(roll_number)
            # Ensure roll number doesn't exceed page width
            max_roll_x = width - 25 * mm
            if value_x2 + p.stringWidth(roll_text, 'Helvetica', 10) > max_roll_x:
                value_x2 = max_roll_x - p.stringWidth(roll_text, 'Helvetica', 10)
            p.drawString(value_x2, y, roll_text)
            y -= 20  # Increased line spacing
            
            # Second row: Class and Fee Type
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Class:')
            p.setFont('Helvetica', 10)
            class_text = class_name
            # Ensure class name doesn't exceed column boundary
            if p.stringWidth(class_text, 'Helvetica', 10) > max_name_width:
                while p.stringWidth(class_text, 'Helvetica', 10) > max_name_width and len(class_text) > 1:
                    class_text = class_text[:-1]
                class_text = class_text.rstrip() + '...'
            p.drawString(value_x, y, class_text)
            
            fee_type = payment.fee_structure.fee_type if payment.fee_structure else 'N/A'
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Fee Type:')
            p.setFont('Helvetica', 10)
            fee_type_text = fee_type
            # Ensure fee type doesn't exceed page width
            if value_x2 + p.stringWidth(fee_type_text, 'Helvetica', 10) > max_roll_x:
                value_x2_fee = max_roll_x - p.stringWidth(fee_type_text, 'Helvetica', 10)
            else:
                value_x2_fee = value_x2
            p.drawString(value_x2_fee, y, fee_type_text)
            y -= 25  # Increased spacing after section

            # Payment details section - IMPROVED SPACING AND LAYOUT
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1)
            # Calculate dynamic height based on content
            section_height = 75 if (payment.fee_structure and remaining > 0) else 60
            p.rect(20 * mm, y - section_height, width - 40 * mm, section_height, stroke=1, fill=0)
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 10, 'PAYMENT INFORMATION')  # Adjusted position
            y -= 20  # Increased spacing after header
            
            payment_method = payment.get_payment_method_display() if hasattr(payment, 'get_payment_method_display') else payment.payment_method or 'CASH'
            amount_paid = float(payment.amount_paid)
            total_fee = float(payment.fee_structure.amount) if payment.fee_structure else amount_paid
            remaining = max(0, total_fee - amount_paid)
            discount = float(payment.discount_amount) if payment.discount_amount else 0
            
            # IMPROVED: Better alignment with proper spacing
            label_x = 25 * mm          # Fixed label position (left column)
            value_x = 105 * mm         # Increased spacing for text values
            currency_x = width - 30 * mm  # Fixed right-aligned position for all currency with margin
            
            # Payment Method - on its own line
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Payment Method:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x, y, payment_method.upper())
            y -= 18  # Increased line spacing
            
            # Amount Paid - on its own line
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Amount Paid:')
            p.setFont('Helvetica-Bold', 11)
            p.setFillColor(colors.black)
            amount_text = f"₹{amount_paid:,.2f}"
            amount_width = p.stringWidth(amount_text, 'Helvetica-Bold', 11)
            if amount_width > (width - currency_x):
                p.setFont('Helvetica-Bold', 10)
                amount_text = f"₹{amount_paid:,.2f}"
            p.drawRightString(currency_x, y, amount_text)
            y -= 18  # Increased line spacing
            
            # Discount (if exists) - on its own line
            if discount > 0:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(label_x, y, 'Discount:')
                p.setFont('Helvetica', 10)
                discount_text = f"₹{discount:,.2f}"
                p.drawRightString(currency_x, y, discount_text)
                y -= 18  # Increased line spacing
            
            # Total Fee (if exists) - on its own line
            if payment.fee_structure:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(label_x, y, 'Total Fee:')
                p.setFont('Helvetica', 10)
                total_text = f"₹{total_fee:,.2f}"
                total_width = p.stringWidth(total_text, 'Helvetica', 10)
                if total_width > (width - currency_x):
                    p.setFont('Helvetica', 9)
                    total_text = f"₹{total_fee:,.2f}"
                p.drawRightString(currency_x, y, total_text)
                y -= 18  # Increased line spacing
            
            # Remaining (if exists) - on its own line
            if payment.fee_structure and remaining > 0:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(label_x, y, 'Remaining:')
                p.setFont('Helvetica', 10)
                p.setFillColor(colors.black)
                remaining_text = f"₹{remaining:,.2f}"
                remaining_width = p.stringWidth(remaining_text, 'Helvetica', 10)
                if remaining_width > (width - currency_x):
                    p.setFont('Helvetica', 9)
                    remaining_text = f"₹{remaining:,.2f}"
                p.drawRightString(currency_x, y, remaining_text)
                y -= 18  # Increased line spacing
            
            y -= 15  # Extra spacing after payment section

            # Notes section (if exists) - IMPROVED: Better text wrapping to prevent word collapsing
            if payment.notes:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(25 * mm, y, 'Notes:')
                y -= 12
                p.setFont('Helvetica', 9)
                # IMPROVED: Smart word wrapping - break at word boundaries, not mid-word
                notes_text = str(payment.notes)
                max_width = width - 50 * mm  # Available width for notes
                words = notes_text.split()
                lines = []
                current_line = ''
                for word in words:
                    test_line = current_line + (' ' if current_line else '') + word
                    if p.stringWidth(test_line, 'Helvetica', 9) <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                # Display up to 4 lines with proper spacing
                for line in lines[:4]:
                    if y < 60:
                        break
                    p.drawString(25 * mm, y, line)
                    y -= 11
                y -= 8
            else:
                y -= 15

            # Total amount section - IMPROVED SPACING AND ALIGNMENT
            p.setStrokeColor(colors.HexColor('#000000'))
            p.setLineWidth(1.5)
            p.rect(20 * mm, y - 40, width - 40 * mm, 40, stroke=1, fill=0)  # Increased height
            p.setFillColor(colors.black)
            p.setFont('Helvetica-Bold', 14)
            p.drawString(25 * mm, y - 15, 'TOTAL AMOUNT PAID:')  # Adjusted position
            p.setFont('Helvetica-Bold', 18)
            # IMPROVED: Ensure total amount fits within bounds
            total_paid_text = f"₹{amount_paid:,.2f}"
            total_paid_width = p.stringWidth(total_paid_text, 'Helvetica-Bold', 18)
            if total_paid_width > (width - 30 * mm):
                p.setFont('Helvetica-Bold', 16)
                total_paid_text = f"₹{amount_paid:,.2f}"
            p.drawRightString(width - 30 * mm, y - 12, total_paid_text)  # Adjusted position with margin
            y -= 50  # Increased spacing after total section

            # Thank you message (black text on white background)
            p.setFont('Helvetica', 11)
            p.setFillColor(colors.black)  # Black text on white
            p.drawCentredString(width / 2, y, 'Thank you for your payment!')
            y -= 15

            # Footer
            p.setFont('Helvetica', 8)
            p.setFillColor(colors.black)
            footer_text = f"Generated on {timezone.now().strftime('%d-%m-%Y at %I:%M %p')} — {school_name.upper()}"
            p.drawCentredString(width / 2, 20 * mm, footer_text)
            p.setFont('Helvetica-Oblique', 7)
            p.drawCentredString(width / 2, 15 * mm, 'This is a computer-generated receipt and does not require a physical signature.')

            p.showPage()
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            receipt_filename = f"fee_receipt_{receipt_number}_{payment.id}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{receipt_filename}"'
            return response
        except ImportError as e:
            logger.error(f"PDF generation import error: {str(e)}", exc_info=True)
            return Response({
                'error': 'PDF generation library not installed.',
                'details': 'Install required packages: pip install reportlab Pillow',
                'missing': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error generating receipt PDF: {str(e)}", exc_info=True)
            return Response({
                'error': f'Receipt PDF generation failed: {str(e)}',
                'details': 'Check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Installment Management Views
class FeeInstallmentPlanListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        fee_structure_id = request.query_params.get('fee_structure')
        plans = FeeInstallmentPlan._default_manager.filter(tenant=profile.tenant)
        if fee_structure_id:
            plans = plans.filter(fee_structure_id=fee_structure_id)
        serializer = FeeInstallmentPlanSerializer(plans, many=True)
        return Response(serializer.data)

    @role_required('admin', 'principal', 'accountant')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = FeeInstallmentPlanSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FeeInstallmentPlanDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            plan = FeeInstallmentPlan._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = FeeInstallmentPlanSerializer(plan)
            return Response(serializer.data)
        except FeeInstallmentPlan.DoesNotExist:
            return Response({'error': 'Installment plan not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'accountant')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            plan = FeeInstallmentPlan._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = FeeInstallmentPlanSerializer(plan, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except FeeInstallmentPlan.DoesNotExist:
            return Response({'error': 'Installment plan not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'accountant')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            plan = FeeInstallmentPlan._default_manager.get(id=pk, tenant=profile.tenant)
            plan.delete()
            return Response({'message': 'Installment plan deleted.'})
        except FeeInstallmentPlan.DoesNotExist:
            return Response({'error': 'Installment plan not found.'}, status=status.HTTP_404_NOT_FOUND)

class FeeInstallmentListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            student_id = request.query_params.get('student')
            fee_structure_id = request.query_params.get('fee_structure')
            status_filter = request.query_params.get('status')
            
            installments = FeeInstallment._default_manager.filter(tenant=profile.tenant)
            if student_id:
                installments = installments.filter(student_id=student_id)
            if fee_structure_id:
                installments = installments.filter(fee_structure_id=fee_structure_id)
            if status_filter:
                installments = installments.filter(status=status_filter)
            
            # Recompute paid amounts and status from payments to ensure UI reflects actual payments
            try:
                from django.db.models import Sum
                from education.models import FeePayment
                from decimal import Decimal
                # Group installments by (student, fee_structure)
                groups = {}
                for inst in installments.order_by('fee_structure', 'installment_number'):
                    key = (inst.student_id, inst.fee_structure_id)
                    groups.setdefault(key, []).append(inst)
                for (student_id_val, fee_structure_id_val), inst_list in groups.items():
                    # Sum all payments for this student+fee_structure
                    total_paid_all = FeePayment._default_manager.filter(
                        tenant=profile.tenant,
                        student_id=student_id_val,
                        fee_structure_id=fee_structure_id_val
                    ).aggregate(total=Sum('amount_paid'))['total'] or 0
                    total_paid_all = Decimal(str(total_paid_all))
                    # Compute current allocated (direct + split)
                    total_allocated = Decimal('0')
                    per_inst_paid = {}
                    for inst in inst_list:
                        direct_paid = FeePayment._default_manager.filter(
                            tenant=profile.tenant,
                            installment=inst
                        ).aggregate(total=Sum('amount_paid'))['total'] or 0
                        direct_paid = Decimal(str(direct_paid))
                        split_paid = Decimal('0')
                        for p in FeePayment._default_manager.filter(
                            tenant=profile.tenant,
                            student_id=student_id_val,
                            fee_structure_id=fee_structure_id_val
                        ):
                            try:
                                alloc = p.split_installments.get(str(inst.id))
                                if alloc:
                                    split_paid += Decimal(str(alloc))
                            except Exception:
                                continue
                        per_inst_paid[inst.id] = direct_paid + split_paid
                        total_allocated += per_inst_paid[inst.id]
                    # Residual from generic payments not tagged to installments
                    residual = total_paid_all - total_allocated
                    # Allocate residual across installments in order
                    for inst in inst_list:
                        if residual <= 0:
                            break
                        due = Decimal(str(inst.due_amount))
                        current = per_inst_paid.get(inst.id, Decimal('0'))
                        need = max(Decimal('0'), due - current)
                        apply = min(residual, need)
                        if apply > 0:
                            current += apply
                            per_inst_paid[inst.id] = current
                            residual -= apply
                    # Update installments
                    for inst in inst_list:
                        inst.paid_amount = per_inst_paid.get(inst.id, Decimal('0'))
                        inst.update_status()
            except Exception as e:
                logger.error(f"Error computing installment status in FeeInstallmentListCreateView.get: {str(e)}", exc_info=True)
                # Continue with serialization even if status update fails
            
            serializer = FeeInstallmentSerializer(installments, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in FeeInstallmentListCreateView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @role_required('admin', 'principal', 'accountant')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        serializer = FeeInstallmentSerializer(data=data)
        if serializer.is_valid():
            installment = serializer.save(tenant=profile.tenant)
            installment.update_status()  # Auto-update status
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FeeInstallmentDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            installment = FeeInstallment._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = FeeInstallmentSerializer(installment)
            return Response(serializer.data)
        except FeeInstallment.DoesNotExist:
            return Response({'error': 'Installment not found.'}, status=status.HTTP_404_NOT_FOUND)

    @role_required('admin', 'principal', 'accountant')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            installment = FeeInstallment._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = FeeInstallmentSerializer(installment, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                installment.update_status()  # Auto-update status after change
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except FeeInstallment.DoesNotExist:
            return Response({'error': 'Installment not found.'}, status=status.HTTP_404_NOT_FOUND)

class FeeInstallmentGenerateView(APIView):
    """Generate installments for a student based on installment plan"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    @role_required('admin', 'principal', 'accountant')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        
        student_id = data.get('student_id')
        fee_structure_id = data.get('fee_structure_id')
        installment_plan_id = data.get('installment_plan_id')
        
        if not all([student_id, fee_structure_id, installment_plan_id]):
            return Response(
                {'error': 'student_id, fee_structure_id, and installment_plan_id are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student._default_manager.get(id=student_id, tenant=profile.tenant)
            fee_structure = FeeStructure._default_manager.get(id=fee_structure_id, tenant=profile.tenant)
            installment_plan = FeeInstallmentPlan._default_manager.get(id=installment_plan_id, tenant=profile.tenant)
            
            # Check if installments already exist
            existing = FeeInstallment._default_manager.filter(
                tenant=profile.tenant,
                student=student,
                fee_structure=fee_structure
            )
            if existing.exists():
                return Response(
                    {'error': 'Installments already exist for this student and fee structure.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate installments based on plan
            installments_data = data.get('installments', [])  # Custom installments if provided
            created_installments = []
            
            if installment_plan.installment_type in ('EQUAL', 'PERCENTAGE'):
                # Equal split with rounding and proper due dates from start_date
                from decimal import Decimal, ROUND_HALF_UP
                from datetime import timedelta, date
                from django.utils import timezone

                n = int(installment_plan.number_of_installments or 1)
                total = Decimal(str(fee_structure.amount))
                base = (total / Decimal(n)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                amounts = [base for _ in range(n)]
                # Adjust last installment to fix rounding difference
                diff = total - sum(amounts)
                if diff != 0:
                    amounts[-1] = (amounts[-1] + diff).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                # Start date parsing
                start_date_str = data.get('start_date')
                try:
                    start_dt = date.fromisoformat(start_date_str) if start_date_str else timezone.now().date()
                except Exception:
                    start_dt = timezone.now().date()

                for i in range(1, n + 1):
                    # Approximate month increment by 30-day blocks
                    due_dt = (start_dt + timedelta(days=30 * (i - 1)))
                    installment = FeeInstallment._default_manager.create(
                        tenant=profile.tenant,
                        student=student,
                        fee_structure=fee_structure,
                        installment_plan=installment_plan,
                        installment_number=i,
                        due_amount=amounts[i - 1],
                        due_date=due_dt
                    )
                    installment.update_status()
                    created_installments.append(installment)
            else:
                # Custom amounts - use provided installments_data
                if not installments_data:
                    return Response(
                        {'error': 'installments data required for CUSTOM installment type.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                for inst_data in installments_data:
                    installment = FeeInstallment._default_manager.create(
                        tenant=profile.tenant,
                        student=student,
                        fee_structure=fee_structure,
                        installment_plan=installment_plan,
                        installment_number=inst_data['installment_number'],
                        due_amount=inst_data['due_amount'],
                        due_date=inst_data['due_date']
                    )
                    installment.update_status()
                    created_installments.append(installment)
            
            serializer = FeeInstallmentSerializer(created_installments, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        except FeeStructure.DoesNotExist:
            return Response({'error': 'Fee structure not found.'}, status=status.HTTP_404_NOT_FOUND)
        except FeeInstallmentPlan.DoesNotExist:
            return Response({'error': 'Installment plan not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error generating installments: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FeeInstallmentRegenerateView(APIView):
    """Delete existing installments for student+fee_structure and regenerate from a plan"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    @role_required('admin', 'principal', 'accountant')
    def post(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()

        student_id = data.get('student_id')
        fee_structure_id = data.get('fee_structure_id')
        installment_plan_id = data.get('installment_plan_id')
        if not all([student_id, fee_structure_id, installment_plan_id]):
            return Response({'error': 'student_id, fee_structure_id, and installment_plan_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student._default_manager.get(id=student_id, tenant=profile.tenant)
            fee_structure = FeeStructure._default_manager.get(id=fee_structure_id, tenant=profile.tenant)
            installment_plan = FeeInstallmentPlan._default_manager.get(id=installment_plan_id, tenant=profile.tenant)

            # Delete existing installments
            FeeInstallment._default_manager.filter(
                tenant=profile.tenant,
                student=student,
                fee_structure=fee_structure
            ).delete()

            # Reuse generation logic
            from decimal import Decimal, ROUND_HALF_UP
            from datetime import timedelta, date
            from django.utils import timezone

            created_installments = []
            if installment_plan.installment_type in ('EQUAL', 'PERCENTAGE'):
                n = int(installment_plan.number_of_installments or 1)
                total = Decimal(str(fee_structure.amount))
                base = (total / Decimal(n)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                amounts = [base for _ in range(n)]
                diff = total - sum(amounts)
                if diff != 0:
                    amounts[-1] = (amounts[-1] + diff).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                start_date_str = data.get('start_date')
                try:
                    start_dt = date.fromisoformat(start_date_str) if start_date_str else timezone.now().date()
                except Exception:
                    start_dt = timezone.now().date()

                for i in range(1, n + 1):
                    due_dt = (start_dt + timedelta(days=30 * (i - 1)))
                    installment = FeeInstallment._default_manager.create(
                        tenant=profile.tenant,
                        student=student,
                        fee_structure=fee_structure,
                        installment_plan=installment_plan,
                        installment_number=i,
                        due_amount=amounts[i - 1],
                        due_date=due_dt
                    )
                    installment.update_status()
                    created_installments.append(installment)
            else:
                installments_data = data.get('installments', [])
                if not installments_data:
                    return Response({'error': 'installments data required for CUSTOM installment type.'}, status=status.HTTP_400_BAD_REQUEST)
                for inst_data in installments_data:
                    installment = FeeInstallment._default_manager.create(
                        tenant=profile.tenant,
                        student=student,
                        fee_structure=fee_structure,
                        installment_plan=installment_plan,
                        installment_number=inst_data['installment_number'],
                        due_amount=inst_data['due_amount'],
                        due_date=inst_data['due_date']
                    )
                    installment.update_status()
                    created_installments.append(installment)

            serializer = FeeInstallmentSerializer(created_installments, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        except FeeStructure.DoesNotExist:
            return Response({'error': 'Fee structure not found.'}, status=status.HTTP_404_NOT_FOUND)
        except FeeInstallmentPlan.DoesNotExist:
            return Response({'error': 'Installment plan not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error regenerating installments: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentInstallmentsView(APIView):
    """Get all installments for a specific student"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, student_id):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            student = Student._default_manager.get(id=student_id, tenant=profile.tenant)
            installments = FeeInstallment._default_manager.filter(
                tenant=profile.tenant,
                student=student
            ).order_by('fee_structure', 'installment_number')
            
            serializer = FeeInstallmentSerializer(installments, many=True)
            return Response(serializer.data)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

class OverdueInstallmentsView(APIView):
    """Get all overdue installments"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        from django.utils import timezone
        today = timezone.now().date()
        
        overdue = FeeInstallment._default_manager.filter(
            tenant=profile.tenant,
            status__in=['PENDING', 'PARTIAL'],
            due_date__lt=today
        ).order_by('due_date')
        
        # Update status to OVERDUE for any that are overdue
        for inst in overdue.filter(status__in=['PENDING', 'PARTIAL']):
            inst.update_status()
        
        serializer = FeeInstallmentSerializer(overdue, many=True)
        return Response(serializer.data)

class FeeDiscountViewSet(viewsets.ModelViewSet):
    serializer_class = FeeDiscountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = UserProfile._default_manager.get(user=self.request.user)
        return FeeDiscount._default_manager.filter(tenant=profile.tenant)

    def perform_create(self, serializer):
        profile = UserProfile._default_manager.get(user=self.request.user)
        serializer.save(tenant=profile.tenant)

class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = UserProfile._default_manager.get(user=self.request.user)
        return Department._default_manager.filter(tenant=profile.tenant)

    def perform_create(self, serializer):
        profile = UserProfile._default_manager.get(user=self.request.user)
        serializer.save(tenant=profile.tenant) 

class FeeStructureListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        # Allow admin, accountant, principal, and teacher to view fee structures (read-only for teachers)
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal', 'teacher']:
            return Response({'error': 'You do not have permission to view fee structures.'}, status=status.HTTP_403_FORBIDDEN)
        fee_structures = FeeStructure._default_manager.filter(tenant=profile.tenant)
        serializer = FeeStructureSerializer(fee_structures, many=True)
        return Response(serializer.data) 

class ClassAttendanceStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        tenant = profile.tenant
        class_id = request.query_params.get('class_id')
        date_str = request.query_params.get('date')

        # If class_id provided, return per-student status for that class/date
        if class_id:
            try:
                class_obj = Class._default_manager.get(id=class_id, tenant=tenant)  # type: ignore
            except Class.DoesNotExist:  # type: ignore
                return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

            try:
                query_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
            except Exception:
                query_date = timezone.now().date()

            students = Student._default_manager.filter(tenant=tenant, assigned_class=class_obj)  # type: ignore
            result = []
            for s in students:
                att = Attendance._default_manager.filter(tenant=tenant, student=s, date=query_date).first()  # type: ignore
                result.append({
                    'student': {
                        'id': s.id,
                        'name': s.name,
                    },
                    'present': bool(att.present) if att is not None else False,
                })
            return Response(result)

        # Default: return class summary for today
        classes = Class._default_manager.filter(tenant=tenant)  # type: ignore
        data = []
        today = timezone.now().date()
        for c in classes:
            total_students = Student._default_manager.filter(tenant=tenant, assigned_class=c).count()  # type: ignore
            present_today = Attendance._default_manager.filter(tenant=tenant, student__assigned_class=c, date=today, present=True).count()  # type: ignore
            absent_today = Attendance._default_manager.filter(tenant=tenant, student__assigned_class=c, date=today, present=False).count()  # type: ignore
            data.append({
                'class_id': c.id,
                'class_name': c.name,
                'total_students': total_students,
                'present_today': present_today,
                'absent_today': absent_today,
                'attendance_percentage': round((present_today / total_students * 100) if total_students > 0 else 0, 2)
            })
        return Response(data)

# Missing analytics endpoints
class AttendanceTrendsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        tenant = profile.tenant
        
        # Get attendance data for the last 30 days
        from datetime import timedelta
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        attendance_data = []
        current_date = start_date
        while current_date <= end_date:
            present_count = Attendance._default_manager.filter(tenant=tenant, date=current_date, present=True).count()  # type: ignore
            absent_count = Attendance._default_manager.filter(tenant=tenant, date=current_date, present=False).count()  # type: ignore
            total_count = present_count + absent_count
            
            attendance_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'present': present_count,
                'absent': absent_count,
                'total': total_count,
                'percentage': round((present_count / total_count * 100) if total_count > 0 else 0, 2)
            })
            current_date += timedelta(days=1)
        
        return Response(attendance_data)

class StaffDistributionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        tenant = profile.tenant
        
        # Get staff distribution by role
        staff_by_role = {}
        staff_profiles = UserProfile._default_manager.filter(tenant=tenant)  # type: ignore
        
        for staff in staff_profiles:
            role_name = staff.role.name if staff.role else 'No Role'
            if role_name not in staff_by_role:
                staff_by_role[role_name] = 0
            staff_by_role[role_name] += 1
        
        # Get staff distribution by department
        staff_by_department = {}
        for staff in staff_profiles:
            if staff.assigned_classes.exists():
                for class_obj in staff.assigned_classes.all():
                    dept_name = class_obj.department.name if class_obj.department else 'No Department'
                    if dept_name not in staff_by_department:
                        staff_by_department[dept_name] = 0
                    staff_by_department[dept_name] += 1
        
        return Response({
            'by_role': staff_by_role,
            'by_department': staff_by_department,
            'total_staff': staff_profiles.count()
        })

class FeeCollectionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        tenant = profile.tenant
        
        # Get fee collection data for the last 12 months
        from datetime import date
        from calendar import monthrange
        
        fee_data = []
        current_date = timezone.now().date()
        
        for i in range(12):
            # Calculate month and year
            if current_date.month - i <= 0:
                year = current_date.year - 1
                month = 12 + (current_date.month - i)
            else:
                year = current_date.year
                month = current_date.month - i
            
            # Get month range
            start_date = date(year, month, 1)
            end_date = date(year, month, monthrange(year, month)[1])
            
            # Calculate fee collection for this month
            fees_collected = FeePayment._default_manager.filter(tenant=tenant, payment_date__range=(start_date, end_date)).aggregate(total=Sum('amount_paid'))['total'] or 0  # type: ignore
            
            fee_data.append({
                'month': f"{year}-{month:02d}",
                'fees_collected': fees_collected,
                'year': year,
                'month_num': month
            })
        
        # Sort by date
        fee_data.sort(key=lambda x: (x['year'], x['month_num']))
        
        return Response(fee_data)

class ClassPerformanceView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        tenant = profile.tenant
        classes = Class._default_manager.filter(tenant=tenant)  # type: ignore
        
        performance_data = []
        for c in classes:
            # Get student count
            student_count = Student._default_manager.filter(tenant=tenant, assigned_class=c).count()  # type: ignore
            
            # Get average attendance for this class
            attendance_records = Attendance._default_manager.filter(tenant=tenant, assigned_class=c)  # type: ignore
            total_attendance = attendance_records.count()
            present_attendance = attendance_records.filter(present=True).count()
            attendance_percentage = round((present_attendance / total_attendance * 100) if total_attendance > 0 else 0, 2)
            
            # Get fee collection for this class
            fees_collected = FeePayment._default_manager.filter(tenant=tenant, student__assigned_class=c).aggregate(total=Sum('amount_paid'))['total'] or 0  # type: ignore
            
            # Get report card performance (average grades)
            report_cards = ReportCard._default_manager.filter(tenant=tenant, student__assigned_class=c)  # type: ignore
            total_grades = 0
            grade_count = 0
            
            for rc in report_cards:
                if rc.total_marks and rc.obtained_marks:
                    total_grades += (rc.obtained_marks / rc.total_marks) * 100
                    grade_count += 1
            
            average_performance = round(total_grades / grade_count, 2) if grade_count > 0 else 0
            
            performance_data.append({
                'class_id': c.id,
                'class_name': c.name,
                'student_count': student_count,
                'attendance_percentage': attendance_percentage,
                'fees_collected': fees_collected,
                'average_performance': average_performance
            })
        
        return Response(performance_data) 

class FeeStructureExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can export fee structures.'}, status=status.HTTP_403_FORBIDDEN)
        
        fee_structures = FeeStructure._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        class_id = request.query_params.get('class')
        fee_type = request.query_params.get('fee_type')
        academic_year = request.query_params.get('academic_year')
        
        if class_id:
            fee_structures = fee_structures.filter(class_obj_id=class_id)
        if fee_type:
            fee_structures = fee_structures.filter(fee_type=fee_type)
        if academic_year:
            fee_structures = fee_structures.filter(academic_year=academic_year)
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Fee Structures Report")
                y -= 30
                p.setFont("Helvetica", 10)
                headers = ["ID", "Class", "Fee Type", "Amount", "Optional", "Due Date", "Academic Year"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*80, y, h)
                y -= 20
                
                for fs in fee_structures:
                    row = [
                        str(fs.id),
                        fs.class_obj.name if fs.class_obj else "N/A",
                        fs.fee_type,
                        f"₹{fs.amount}",
                        "Yes" if fs.is_optional else "No",
                        fs.due_date.strftime('%Y-%m-%d') if fs.due_date else "Not Set",
                        fs.academic_year or "N/A"
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*80, y, val)
                    y -= 18
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="fee_structures.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="fee_structures.csv"'
            writer = csv.writer(response)
            writer.writerow(["ID", "Class", "Fee Type", "Amount", "Description", "Optional", "Due Date", "Academic Year"])
            for fs in fee_structures:
                writer.writerow([
                    fs.id,
                    fs.class_obj.name if fs.class_obj else "N/A",
                    fs.fee_type,
                    fs.amount,
                    fs.description or "",
                    "Yes" if fs.is_optional else "No",
                    fs.due_date.strftime('%Y-%m-%d') if fs.due_date else "Not Set",
                    fs.academic_year or "N/A"
                ])
            return response

class FeePaymentExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can export fee payments.'}, status=status.HTTP_403_FORBIDDEN)
        
        fee_payments = FeePayment._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        student_id = request.query_params.get('student')
        payment_method = request.query_params.get('payment_method')
        date_from = request.query_params.get('payment_date_from')
        date_to = request.query_params.get('payment_date_to')
        
        if student_id:
            fee_payments = fee_payments.filter(student_id=student_id)
        if payment_method:
            fee_payments = fee_payments.filter(payment_method=payment_method)
        if date_from:
            fee_payments = fee_payments.filter(payment_date__gte=date_from)
        if date_to:
            fee_payments = fee_payments.filter(payment_date__lte=date_to)
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Fee Payments Report")
                y -= 30
                p.setFont("Helvetica", 8)
                headers = ["ID", "Student", "Fee Type", "Amount Paid", "Payment Date", "Method", "Receipt"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*70, y, h)
                y -= 20
                
                for fp in fee_payments:
                    row = [
                        str(fp.id),
                        fp.student.name if fp.student else "N/A",
                        fp.fee_structure.fee_type if fp.fee_structure else "N/A",
                        f"₹{fp.amount_paid}",
                        fp.payment_date.strftime('%Y-%m-%d'),
                        fp.payment_method,
                        fp.receipt_number or "N/A"
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*70, y, val)
                    y -= 15
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="fee_payments.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="fee_payments.csv"'
            writer = csv.writer(response)
            writer.writerow(["ID", "Student", "Student Roll", "Fee Type", "Amount Paid", "Payment Date", "Method", "Receipt", "Notes", "Discount"])
            for fp in fee_payments:
                writer.writerow([
                    fp.id,
                    fp.student.name if fp.student else "N/A",
                    fp.student.roll_number if fp.student else "N/A",
                    fp.fee_structure.fee_type if fp.fee_structure else "N/A",
                    fp.amount_paid,
                    fp.payment_date.strftime('%Y-%m-%d'),
                    fp.payment_method,
                    fp.receipt_number or "",
                    fp.notes or "",
                    fp.discount_amount or 0
                ])
            return response

class FeeDiscountExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can export fee discounts.'}, status=status.HTTP_403_FORBIDDEN)
        
        fee_discounts = FeeDiscount._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        discount_type = request.query_params.get('discount_type')
        is_active = request.query_params.get('is_active')
        
        if discount_type:
            fee_discounts = fee_discounts.filter(discount_type=discount_type)
        if is_active is not None:
            fee_discounts = fee_discounts.filter(is_active=is_active.lower() == 'true')
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Fee Discounts Report")
                y -= 30
                p.setFont("Helvetica", 8)
                headers = ["ID", "Name", "Type", "Value", "Valid From", "Valid Until", "Active"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*70, y, h)
                y -= 20
                
                for fd in fee_discounts:
                    row = [
                        str(fd.id),
                        fd.name,
                        fd.discount_type,
                        f"{fd.discount_value}{'%' if fd.discount_type == 'PERCENTAGE' else '₹'}",
                        fd.valid_from.strftime('%Y-%m-%d') if fd.valid_from else "N/A",
                        fd.valid_until.strftime('%Y-%m-%d') if fd.valid_until else "No End",
                        "Yes" if fd.is_active else "No"
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*70, y, val)
                    y -= 15
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="fee_discounts.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="fee_discounts.csv"'
            writer = csv.writer(response)
            writer.writerow(["ID", "Name", "Type", "Value", "Min Amount", "Max Discount", "Valid From", "Valid Until", "Active", "Description"])
            for fd in fee_discounts:
                writer.writerow([
                    fd.id,
                    fd.name,
                    fd.discount_type,
                    fd.discount_value,
                    fd.min_amount or 0,
                    fd.max_discount or "",
                    fd.valid_from.strftime('%Y-%m-%d') if fd.valid_from else "",
                    fd.valid_until.strftime('%Y-%m-%d') if fd.valid_until else "",
                    "Yes" if fd.is_active else "No",
                    fd.description or ""
                ])
            return response

class StudentFeeStatusView(APIView):
    """Get comprehensive fee status for a specific student"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, student_id):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            student = Student._default_manager.get(id=student_id, tenant=profile.tenant)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all fee structures for the student's class
        fee_structures = FeeStructure._default_manager.filter(
            tenant=profile.tenant, 
            class_obj=student.assigned_class
        )
        
        # Get all payments made by this student
        payments = FeePayment._default_manager.filter(
            tenant=profile.tenant,
            student=student
        )
        
        # Calculate fee status
        fee_status = []
        total_due = 0
        total_paid = 0
        
        for fee_structure in fee_structures:
            # Calculate total paid for this fee type
            paid_amount = payments.filter(fee_structure=fee_structure).aggregate(
                total=Sum('amount_paid')
            )['total'] or 0
            
            # Calculate discount applied
            discount_amount = payments.filter(fee_structure=fee_structure).aggregate(
                total=Sum('discount_amount')
            )['total'] or 0
            
            remaining_amount = fee_structure.amount - paid_amount
            is_paid = remaining_amount <= 0
            
            fee_status.append({
                'fee_structure_id': fee_structure.id,
                'fee_type': fee_structure.fee_type,
                'total_amount': fee_structure.amount,
                'paid_amount': paid_amount,
                'discount_amount': discount_amount,
                'remaining_amount': max(0, remaining_amount),
                'is_paid': is_paid,
                'due_date': fee_structure.due_date,
                'is_overdue': fee_structure.due_date and fee_structure.due_date < timezone.now().date() and not is_paid
            })
            
            total_due += fee_structure.amount
            total_paid += paid_amount
        
        # Calculate overall status
        overall_remaining = total_due - total_paid
        payment_percentage = (total_paid / total_due * 100) if total_due > 0 else 0
        
        return Response({
            'student': {
                'id': student.id,
                'name': student.name,
                'email': student.email,
                'upper_id': student.upper_id,
                'assigned_class': student.assigned_class.name if student.assigned_class else None
            },
            'fee_summary': {
                'total_due': total_due,
                'total_paid': total_paid,
                'remaining_amount': overall_remaining,
                'payment_percentage': round(payment_percentage, 2),
                'is_fully_paid': overall_remaining <= 0
            },
            'fee_breakdown': fee_status,
            'recent_payments': FeePaymentSerializer(payments.order_by('-payment_date')[:5], many=True).data
        })

class StudentFeePaymentHistoryView(APIView):
    """Get payment history for a specific student"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, student_id):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            student = Student._default_manager.get(id=student_id, tenant=profile.tenant)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        payments = FeePayment._default_manager.filter(
            tenant=profile.tenant,
            student=student
        ).order_by('-payment_date')
        
        # Filtering
        payment_method = request.query_params.get('payment_method')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if payment_method:
            payments = payments.filter(payment_method=payment_method)
        if date_from:
            payments = payments.filter(payment_date__gte=date_from)
        if date_to:
            payments = payments.filter(payment_date__lte=date_to)
        
        serializer = FeePaymentSerializer(payments, many=True)
        return Response(serializer.data)

class StudentFeeReminderView(APIView):
    """Send fee reminder for overdue payments"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def post(self, request, student_id):
        profile = UserProfile._default_manager.get(user=request.user)
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can send fee reminders.'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            student = Student._default_manager.get(id=student_id, tenant=profile.tenant)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get overdue fees
        today = timezone.now().date()
        overdue_fees = FeeStructure._default_manager.filter(
            tenant=profile.tenant,
            class_obj=student.assigned_class,
            due_date__lt=today
        )
        
        # Check which fees are still unpaid
        unpaid_overdue = []
        for fee_structure in overdue_fees:
            paid_amount = FeePayment._default_manager.filter(
                tenant=profile.tenant,
                student=student,
                fee_structure=fee_structure
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
            
            if paid_amount < fee_structure.amount:
                unpaid_overdue.append({
                    'fee_type': fee_structure.fee_type,
                    'amount': fee_structure.amount,
                    'paid_amount': paid_amount,
                    'remaining': fee_structure.amount - paid_amount,
                    'due_date': fee_structure.due_date
                })
        
        if not unpaid_overdue:
            return Response({'message': 'No overdue fees found for this student.'})
        
        # Here you would typically send an email or SMS
        # For now, we'll just return the reminder details
        return Response({
            'message': 'Fee reminder prepared successfully.',
            'student': {
                'name': student.name,
                'email': student.email,
                'upper_id': student.upper_id
            },
            'overdue_fees': unpaid_overdue,
            'total_overdue': sum(fee['remaining'] for fee in unpaid_overdue)
        })

class ClassFeeSummaryView(APIView):
    """Get fee summary for all students in a class"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request, class_id):
        profile = UserProfile._default_manager.get(user=request.user)
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal']:
            return Response({'error': 'Only admins, accountants, and principals can view class fee summaries.'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            class_obj = Class._default_manager.get(id=class_id, tenant=profile.tenant)
        except Class.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        students = Student._default_manager.filter(
            tenant=profile.tenant,
            assigned_class=class_obj
        )
        
        class_summary = {
            'class_id': class_obj.id,
            'class_name': class_obj.name,
            'total_students': students.count(),
            'fee_collection_summary': {
                'total_due': 0,
                'total_collected': 0,
                'total_pending': 0,
                'collection_percentage': 0
            },
            'students': []
        }
        
        total_due = 0
        total_collected = 0
        
        for student in students:
            # Get fee structures for this class
            fee_structures = FeeStructure._default_manager.filter(
                tenant=profile.tenant,
                class_obj=class_obj
            )
            
            student_total_due = sum(fs.amount for fs in fee_structures)
            student_payments = FeePayment._default_manager.filter(
                tenant=profile.tenant,
                student=student
            )
            student_total_paid = student_payments.aggregate(total=Sum('amount_paid'))['total'] or 0
            
            student_remaining = student_total_due - student_total_paid
            student_percentage = (student_total_paid / student_total_due * 100) if student_total_due > 0 else 0
            
            class_summary['students'].append({
                'student_id': student.id,
                'name': student.name,
                'upper_id': student.upper_id,
                'email': student.email,
                'total_due': student_total_due,
                'total_paid': student_total_paid,
                'remaining': student_remaining,
                'payment_percentage': round(student_percentage, 2),
                'is_fully_paid': student_remaining <= 0
            })
            
            total_due += student_total_due
            total_collected += student_total_paid
        
        class_summary['fee_collection_summary'] = {
            'total_due': total_due,
            'total_collected': total_collected,
            'total_pending': total_due - total_collected,
            'collection_percentage': round((total_collected / total_due * 100) if total_due > 0 else 0, 2)
        }
        
        return Response(class_summary)


class ComprehensiveAnalyticsView(APIView):
    """Comprehensive analytics for admin and principal"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        # Allow admin, principal, and teacher to view analytics
        if not profile.role or profile.role.name not in ['admin', 'principal', 'teacher']:
            return Response({'error': 'Only admins, principals, and teachers can view comprehensive analytics.'}, status=status.HTTP_403_FORBIDDEN)
        
        tenant = profile.tenant
        today = timezone.now().date()
        
        # Basic statistics
        total_students = Student.objects.filter(tenant=tenant, is_active=True).count()
        total_classes = Class.objects.filter(tenant=tenant).count()
        total_teachers = UserProfile.objects.filter(tenant=tenant, role__name='teacher').count()
        total_staff = UserProfile.objects.filter(tenant=tenant).exclude(role__name='student').count()
        
        # Today's attendance
        staff_present = StaffAttendance.objects.filter(
            tenant=tenant, date=today, check_in_time__isnull=False
        ).count()
        # Count attendance for today
        student_present = Attendance.objects.filter(
            tenant=tenant,
            date=today,
            present=True
        ).count()
        
        # Fee analytics
        total_fees_due = FeeStructure.objects.filter(tenant=tenant).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_fees_collected = FeePayment.objects.filter(tenant=tenant).aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        # Class-wise analytics
        class_analytics = []
        classes = Class.objects.filter(tenant=tenant)
        
        for class_obj in classes:
            students_in_class = Student.objects.filter(
                tenant=tenant, assigned_class=class_obj, is_active=True
            )
            
            # Student count
            student_count = students_in_class.count()
            
            # Teachers assigned to this class
            teachers = UserProfile._default_manager.filter(
                tenant=tenant, assigned_classes=class_obj, role__name='teacher'
            )
            
            # Fee collection for this class
            class_fee_structures = FeeStructure._default_manager.filter(
                tenant=tenant, class_obj=class_obj
            )
            class_total_due = class_fee_structures.aggregate(total=Sum('amount'))['total'] or 0
            
            class_payments = FeePayment._default_manager.filter(
                tenant=tenant, student__assigned_class=class_obj
            )
            class_collected = class_payments.aggregate(total=Sum('amount_paid'))['total'] or 0
            
            # Attendance for this class (Attendance has only 'date', no 'created_at')
            class_attendance = Attendance.objects.filter(
                tenant=tenant, student__assigned_class=class_obj, date=today
            )
            present_today = class_attendance.filter(present=True).count()
            absent_today = class_attendance.filter(present=False).count()
            
            class_analytics.append({
                'class_id': class_obj.id,
                'class_name': class_obj.name,
                'student_count': student_count,
                'teachers': [
                    {
                        'id': teacher.id,
                        'name': teacher.user.get_full_name() or teacher.user.username,
                        'email': teacher.user.email
                    } for teacher in teachers
                ],
                'fee_summary': {
                    'total_due': float(class_total_due),
                    'collected': float(class_collected),
                    'pending': float(class_total_due - class_collected),
                    'collection_percentage': round((class_collected / class_total_due * 100) if class_total_due > 0 else 0, 2)
                },
                'attendance_today': {
                    'present': present_today,
                    'absent': absent_today,
                    'total': present_today + absent_today,
                    'percentage': round((present_today / (present_today + absent_today) * 100) if (present_today + absent_today) > 0 else 0, 2)
                }
            })
        
        # Student-wise analytics
        student_analytics = []
        students = Student._default_manager.filter(tenant=tenant, is_active=True)[:50]  # Limit for performance
        
        for student in students:
            # Fee status for this student
            student_fee_structures = FeeStructure._default_manager.filter(
                tenant=tenant, class_obj=student.assigned_class
            )
            student_total_due = student_fee_structures.aggregate(total=Sum('amount'))['total'] or 0
            
            student_payments = FeePayment._default_manager.filter(
                tenant=tenant, student=student
            )
            student_paid = student_payments.aggregate(total=Sum('amount_paid'))['total'] or 0
            
            # Attendance percentage for this student
            student_attendance = Attendance._default_manager.filter(
                tenant=tenant, student=student
            )
            total_attendance = student_attendance.count()
            present_attendance = student_attendance.filter(present=True).count()
            attendance_percentage = round((present_attendance / total_attendance * 100) if total_attendance > 0 else 0, 2)
            
            student_analytics.append({
                'student_id': student.id,
                'name': student.name,
                'upper_id': student.upper_id,
                'email': student.email,
                'class_name': student.assigned_class.name if student.assigned_class else 'Not Assigned',
                'fee_status': {
                    'total_due': float(student_total_due),
                    'paid': float(student_paid),
                    'pending': float(student_total_due - student_paid),
                    'percentage': round((student_paid / student_total_due * 100) if student_total_due > 0 else 0, 2)
                },
                'attendance_percentage': attendance_percentage,
                'admission_date': student.admission_date
            })
        
        # Teacher-wise analytics
        teacher_analytics = []
        teachers = UserProfile._default_manager.filter(tenant=tenant, role__name='teacher')
        
        for teacher in teachers:
            assigned_classes = teacher.assigned_classes.all()
            students_taught = Student._default_manager.filter(
                tenant=tenant, assigned_class__in=assigned_classes, is_active=True
            ).count()
            
            # Attendance records created by this teacher
            attendance_records = Attendance._default_manager.filter(
                tenant=tenant, student__assigned_class__in=assigned_classes
            ).count()
            
            teacher_analytics.append({
                'teacher_id': teacher.id,
                'name': teacher.user.get_full_name() or teacher.user.username,
                'email': teacher.user.email,
                'assigned_classes': [cls.name for cls in assigned_classes],
                'students_taught': students_taught,
                'attendance_records': attendance_records
            })
        
        # Monthly fee collection trends
        monthly_fees = []
        for i in range(12):
            month_date = today.replace(day=1) - timezone.timedelta(days=30*i)
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year+1, month=1, day=1) - timezone.timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month+1, day=1) - timezone.timedelta(days=1)
            
            month_fees = FeePayment._default_manager.filter(
                tenant=tenant, payment_date__range=(month_start, month_end)
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
            
            monthly_fees.append({
                'month': month_start.strftime('%Y-%m'),
                'amount': float(month_fees)
            })
        
        return Response({
            'overview': {
                'total_students': total_students,
                'total_classes': total_classes,
                'total_teachers': total_teachers,
                'total_staff': total_staff,
                'staff_present_today': staff_present,
                'student_present_today': student_present,
                'total_fees_due': float(total_fees_due),
                'total_fees_collected': float(total_fees_collected),
                'fees_pending': float(total_fees_due - total_fees_collected),
                'collection_percentage': round((total_fees_collected / total_fees_due * 100) if total_fees_due > 0 else 0, 2)
            },
            'class_analytics': class_analytics,
            'student_analytics': student_analytics,
            'teacher_analytics': teacher_analytics,
            'monthly_fee_trends': monthly_fees
        })

class EducationAnalyticsView(APIView):
    """Main analytics dashboard endpoint"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education'), HasFeaturePermissionFactory('analytics')]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            # Get basic statistics
            total_students = Student._default_manager.filter(tenant=tenant).count()
            total_classes = Class._default_manager.filter(tenant=tenant).count()
            total_teachers = UserProfile._default_manager.filter(tenant=tenant, role__name='teacher').count()
            total_staff = UserProfile._default_manager.filter(tenant=tenant).exclude(role__name='student').count()
            
            # Get today's attendance
            today = timezone.now().date()
            staff_present = StaffAttendance._default_manager.filter(
                tenant=tenant, 
                date=today, 
                check_in_time__isnull=False
            ).count()
            
            student_present = Attendance._default_manager.filter(
                tenant=tenant, 
                date=today, 
                present=True
            ).count()
            
            # Get fee collection stats
            total_fees_collected = FeePayment._default_manager.filter(tenant=tenant).aggregate(
                total=Sum('amount_paid')
            )['total'] or 0
            
            # Get recent activity (last 7 days)
            week_ago = timezone.now() - timezone.timedelta(days=7)
            recent_admissions = Student._default_manager.filter(
                tenant=tenant,
                admission_date__gte=week_ago.date()
            ).count()
            
            recent_fee_payments = FeePayment._default_manager.filter(
                tenant=tenant,
                payment_date__gte=week_ago.date()
            ).count()
            
            # Gender distribution per class
            gender_distribution = []
            classes = Class._default_manager.filter(tenant=tenant)
            for class_obj in classes:
                students = Student._default_manager.filter(tenant=tenant, assigned_class=class_obj, is_active=True)
                male_count = students.filter(gender='Male').count()
                female_count = students.filter(gender='Female').count()
                other_count = students.filter(gender='Other').count()
                total = students.count()
                
                gender_distribution.append({
                    'class_id': class_obj.id,
                    'class_name': class_obj.name,
                    'male': male_count,
                    'female': female_count,
                    'other': other_count,
                    'total': total
                })
            
            # Upcoming birthdays (today)
            today_month = today.month
            today_day = today.day
            upcoming_birthdays = []
            students = Student._default_manager.filter(tenant=tenant, is_active=True, date_of_birth__isnull=False)
            for student in students:
                if student.date_of_birth:
                    if student.date_of_birth.month == today_month and student.date_of_birth.day == today_day:
                        upcoming_birthdays.append({
                            'student_id': student.id,
                            'student_name': student.name,
                            'upper_id': student.upper_id,
                            'class_name': student.assigned_class.name if student.assigned_class else 'Not Assigned',
                            'birthday': student.date_of_birth.strftime('%Y-%m-%d'),
                            'age': today.year - student.date_of_birth.year
                        })
            
            # Student contact information with parent contacts
            student_contacts = []
            all_students = Student._default_manager.filter(tenant=tenant, is_active=True)
            for student in all_students:
                student_contacts.append({
                    'student_id': student.id,
                    'student_name': student.name,
                    'upper_id': student.upper_id,
                    'class_name': student.assigned_class.name if student.assigned_class else 'Not Assigned',
                    'student_phone': student.phone or '',
                    'parent_name': student.parent_name or '',
                    'parent_phone': student.parent_phone or '',
                    'email': student.email or ''
                })
            
            # Students per class with gender breakdown
            students_per_class = []
            for class_obj in classes:
                students = Student._default_manager.filter(tenant=tenant, assigned_class=class_obj, is_active=True)
                total_count = students.count()
                male_count = students.filter(gender='Male').count()
                female_count = students.filter(gender='Female').count()
                other_count = students.filter(gender='Other').count()
                students_per_class.append({
                    'class_name': class_obj.name,
                    'count': total_count,
                    'total': total_count,
                    'male': male_count,
                    'female': female_count,
                    'other': other_count
                })
            
            # Cast distribution per class
            cast_distribution = []
            for class_obj in classes:
                students = Student._default_manager.filter(tenant=tenant, assigned_class=class_obj, is_active=True)
                general_count = students.filter(cast='General').count()
                obc_count = students.filter(cast='OBC').count()
                sc_count = students.filter(cast='SC').count()
                st_count = students.filter(cast='ST').count()
                other_cast_count = students.filter(cast='Other').count()
                total_count = students.count()
                
                cast_distribution.append({
                    'class_id': class_obj.id,
                    'class_name': class_obj.name,
                    'general': general_count,
                    'obc': obc_count,
                    'sc': sc_count,
                    'st': st_count,
                    'other': other_cast_count,
                    'total': total_count
                })
            
            data = {
                'overview': {
                    'total_students': total_students,
                    'total_teachers': total_teachers,
                    'total_classes': total_classes,
                    'total_staff': total_staff,
                    'staff_present_today': staff_present,
                    'student_present_today': student_present,
                    'total_fees_collected': float(total_fees_collected),
                    'recent_admissions': recent_admissions,
                    'recent_fee_payments': recent_fee_payments
                },
                'gender_distribution_per_class': gender_distribution,
                'cast_distribution_per_class': cast_distribution,
                'upcoming_birthdays_today': upcoming_birthdays,
                'student_contacts': student_contacts,
                'students_per_class': students_per_class,
                'endpoints': {
                    'class_stats': '/api/education/analytics/class-stats/',
                    'monthly_report': '/api/education/analytics/monthly-report/',
                    'attendance_trends': '/api/education/analytics/attendance-trends/',
                    'staff_distribution': '/api/education/analytics/staff-distribution/',
                    'fee_collection': '/api/education/analytics/fee-collection/',
                    'class_performance': '/api/education/analytics/class-performance/'
                }
            }
            
            return Response(data)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {request.user.username}")
            return Response({'error': 'User profile not found. Please contact support.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in EducationAnalyticsView.get: {str(e)}", exc_info=True)
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Old Balance Management Views
class OldBalanceListCreateView(APIView):
    """List and create old balances (carry forward from previous years)"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def get(self, request):
        """Get old balances - filtered by academic year, class, or student"""
        profile = UserProfile._default_manager.get(user=request.user)
        balances = OldBalance._default_manager.filter(tenant=profile.tenant)
        
        # Filters
        academic_year = request.query_params.get('academic_year')
        class_name = request.query_params.get('class_name')
        student_id = request.query_params.get('student_id')
        is_settled = request.query_params.get('is_settled')
        
        if academic_year:
            balances = balances.filter(academic_year=academic_year)
        if class_name:
            balances = balances.filter(class_name=class_name)
        if student_id:
            balances = balances.filter(student_id=student_id)
        if is_settled is not None:
            balances = balances.filter(is_settled=is_settled.lower() == 'true')
        
        serializer = OldBalanceSerializer(balances.order_by('-academic_year', 'student'), many=True)
        return Response(serializer.data)
    
    @role_required('admin', 'principal', 'accountant')
    def post(self, request):
        """Create old balance entry"""
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        
        serializer = OldBalanceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OldBalanceDetailView(APIView):
    """Update or delete old balance"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def get(self, request, pk):
        """Get single old balance"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            balance = OldBalance._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = OldBalanceSerializer(balance)
            return Response(serializer.data)
        except OldBalance.DoesNotExist:
            return Response({'error': 'Old balance not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'accountant')
    def put(self, request, pk):
        """Update old balance (e.g., mark as settled)"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            balance = OldBalance._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = OldBalanceSerializer(balance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except OldBalance.DoesNotExist:
            return Response({'error': 'Old balance not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def delete(self, request, pk):
        """Delete old balance"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            balance = OldBalance._default_manager.get(id=pk, tenant=profile.tenant)
            balance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except OldBalance.DoesNotExist:
            return Response({'error': 'Old balance not found'}, status=status.HTTP_404_NOT_FOUND)

class CarryForwardBalancesView(APIView):
    """Bulk carry forward balances from one academic year to another"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def post(self, request):
        """Carry forward outstanding balances from old academic year to new one"""
        profile = UserProfile._default_manager.get(user=request.user)
        from_academic_year = request.data.get('from_academic_year')
        to_academic_year = request.data.get('to_academic_year')
        class_filter = request.data.get('class_name')  # Optional: filter by class
        
        if not from_academic_year or not to_academic_year:
            return Response(
                {'error': 'Both from_academic_year and to_academic_year are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find all unpaid installments for the old academic year
        unpaid_installments = FeeInstallment._default_manager.filter(
            tenant=profile.tenant,
            academic_year=from_academic_year,
            status__in=['PENDING', 'PARTIAL', 'OVERDUE']
        )
        
        if class_filter:
            unpaid_installments = unpaid_installments.filter(student__assigned_class__name=class_filter)
        
        created_balances = []
        for installment in unpaid_installments:
            remaining = float(installment.remaining_amount)
            if remaining > 0:
                # Check if old balance already exists for this student and year
                old_balance, created = OldBalance._default_manager.get_or_create(
                    tenant=profile.tenant,
                    student=installment.student,
                    academic_year=from_academic_year,
                    defaults={
                        'class_name': installment.student.assigned_class.name if installment.student.assigned_class else 'Unknown',
                        'balance_amount': remaining,
                        'carried_forward_to': to_academic_year,
                        'notes': f'Carried forward from {installment.fee_structure.fee_type} installments'
                    }
                )
                if not created:
                    # Update existing balance
                    old_balance.balance_amount += remaining
                    old_balance.carried_forward_to = to_academic_year
                    old_balance.save()
                created_balances.append(old_balance)
        
        serializer = OldBalanceSerializer(created_balances, many=True)
        return Response({
            'message': f'Carried forward {len(created_balances)} balances from {from_academic_year} to {to_academic_year}',
            'balances': serializer.data
        }, status=status.HTTP_201_CREATED)

class BalanceAdjustmentListCreateView(APIView):
    """List and create balance adjustments (waivers, discounts, corrections)"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def get(self, request):
        """Get balance adjustments"""
        profile = UserProfile._default_manager.get(user=request.user)
        adjustments = BalanceAdjustment._default_manager.filter(tenant=profile.tenant)
        
        # Filters
        student_id = request.query_params.get('student_id')
        academic_year = request.query_params.get('academic_year')
        adjustment_type = request.query_params.get('adjustment_type')
        
        if student_id:
            adjustments = adjustments.filter(student_id=student_id)
        if academic_year:
            adjustments = adjustments.filter(academic_year=academic_year)
        if adjustment_type:
            adjustments = adjustments.filter(adjustment_type=adjustment_type)
        
        serializer = BalanceAdjustmentSerializer(adjustments.order_by('-created_at'), many=True)
        return Response(serializer.data)
    
    @role_required('admin', 'principal', 'accountant')
    def post(self, request):
        """Create balance adjustment"""
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        data['created_by'] = profile.id
        
        serializer = BalanceAdjustmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant, created_by=profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OldBalanceSummaryView(APIView):
    """Get summary of old balances by class and academic year"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def get(self, request):
        """Get class-wise and academic year-wise old balance summary"""
        profile = UserProfile._default_manager.get(user=request.user)
        
        # Get all old balances
        balances = OldBalance._default_manager.filter(tenant=profile.tenant, is_settled=False)
        
        # Summary by academic year
        from django.db.models import Sum
        year_summary = {}
        student_years = {}  # Track unique students per year
        
        for balance in balances:
            year = balance.academic_year
            if year not in year_summary:
                year_summary[year] = {'total_amount': 0, 'student_count': 0, 'class_breakdown': {}}
                student_years[year] = set()
            
            year_summary[year]['total_amount'] += float(balance.balance_amount)
            student_years[year].add(balance.student.id)
            
            class_name = balance.class_name
            if class_name not in year_summary[year]['class_breakdown']:
                year_summary[year]['class_breakdown'][class_name] = {'amount': 0, 'count': 0}
            year_summary[year]['class_breakdown'][class_name]['amount'] += float(balance.balance_amount)
            year_summary[year]['class_breakdown'][class_name]['count'] += 1
        
        # Set student counts
        for year in year_summary:
            year_summary[year]['student_count'] = len(student_years[year])
        
        # Summary by class (current outstanding)
        class_summary = {}
        class_students = {}  # Track unique students per class
        
        for balance in balances:
            class_name = balance.class_name or 'Unknown'
            if class_name not in class_summary:
                class_summary[class_name] = {'total_amount': 0, 'student_count': 0, 'years': {}}
                class_students[class_name] = set()
            
            class_summary[class_name]['total_amount'] += float(balance.balance_amount)
            class_students[class_name].add(balance.student.id)
            year = balance.academic_year
            if year not in class_summary[class_name]['years']:
                class_summary[class_name]['years'][year] = float(balance.balance_amount)
            else:
                class_summary[class_name]['years'][year] += float(balance.balance_amount)
        
        # Set student counts
        for class_name in class_summary:
            class_summary[class_name]['student_count'] = len(class_students[class_name])
        
        return Response({
            'by_academic_year': year_summary,
            'by_class': class_summary,
            'total_outstanding': sum(float(b.balance_amount) for b in balances),
            'total_students_with_balance': len(set(b.student.id for b in balances))
        })

class BulkClassPromotionView(APIView):
    """Bulk promote students from one class to the next class"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal')
    def post(self, request):
        """
        Bulk promote students from one class to the next.
        
        Request body:
        {
            "from_class_id": 1,  # Optional: If not provided, will promote all students from all classes
            "to_class_id": 2,  # Optional: If not provided, will auto-detect next class using order
            "from_academic_year_id": 1,  # Current academic year
            "to_academic_year_id": 2,  # New academic year
            "promotion_date": "2025-04-01",  # Date of promotion
            "promote_all": false,  # If true, promote all students regardless of eligibility
            "student_ids": [1, 2, 3],  # Optional: Specific student IDs to promote
            "exclude_student_ids": [4, 5],  # Optional: Student IDs to exclude from promotion
            "notes": "Annual promotion 2025"  # Optional notes
        }
        """
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data
        
        from_class_id = data.get('from_class_id')
        to_class_id = data.get('to_class_id')
        from_academic_year_id = data.get('from_academic_year_id')
        to_academic_year_id = data.get('to_academic_year_id')
        promotion_date = data.get('promotion_date')
        promote_all = data.get('promote_all', False)
        student_ids = data.get('student_ids', [])
        exclude_student_ids = data.get('exclude_student_ids', [])
        notes = data.get('notes', '')
        
        # Validate required fields
        if not from_academic_year_id or not to_academic_year_id:
            return Response(
                {'error': 'Both from_academic_year_id and to_academic_year_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not promotion_date:
            return Response(
                {'error': 'promotion_date is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from_academic_year = AcademicYear._default_manager.get(id=from_academic_year_id, tenant=profile.tenant)
            to_academic_year = AcademicYear._default_manager.get(id=to_academic_year_id, tenant=profile.tenant)
        except AcademicYear.DoesNotExist:
            return Response(
                {'error': 'Academic year not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Parse promotion date
        from datetime import datetime
        try:
            promotion_date_obj = datetime.strptime(promotion_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid promotion_date format. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get students to promote
        students_query = Student._default_manager.filter(
            tenant=profile.tenant,
            is_active=True
        )
        
        # Filter by from_class if provided
        if from_class_id:
            try:
                from_class = Class._default_manager.get(id=from_class_id, tenant=profile.tenant)
                students_query = students_query.filter(assigned_class=from_class)
            except Class.DoesNotExist:
                return Response(
                    {'error': 'From class not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Filter by specific student IDs if provided
        if student_ids:
            students_query = students_query.filter(id__in=student_ids)
        
        # Exclude specific student IDs if provided
        if exclude_student_ids:
            students_query = students_query.exclude(id__in=exclude_student_ids)
        
        students = list(students_query)
        
        if not students:
            return Response(
                {'error': 'No students found to promote'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process promotions
        promoted_students = []
        skipped_students = []
        errors = []
        
        for student in students:
            try:
                current_class = student.assigned_class
                
                # Determine next class
                if to_class_id:
                    try:
                        next_class = Class._default_manager.get(id=to_class_id, tenant=profile.tenant)
                    except Class.DoesNotExist:
                        errors.append({
                            'student_id': student.id,
                            'student_name': student.name,
                            'error': 'To class not found'
                        })
                        continue
                elif current_class:
                    next_class = current_class.get_next_class()
                    if not next_class:
                        skipped_students.append({
                            'student_id': student.id,
                            'student_name': student.name,
                            'reason': f'No next class available for {current_class.name}'
                        })
                        continue
                else:
                    skipped_students.append({
                        'student_id': student.id,
                        'student_name': student.name,
                        'reason': 'Student has no assigned class'
                    })
                    continue
                
                # Create promotion record
                promotion, created = StudentPromotion._default_manager.get_or_create(
                    tenant=profile.tenant,
                    student=student,
                    from_academic_year=from_academic_year,
                    to_academic_year=to_academic_year,
                    defaults={
                        'from_class': current_class,
                        'to_class': next_class,
                        'promotion_type': 'PROMOTED',
                        'promotion_date': promotion_date_obj,
                        'notes': notes,
                        'promoted_by': profile
                    }
                )
                
                # Update student's assigned class
                student.assigned_class = next_class
                student.save()
                
                promoted_students.append({
                    'student_id': student.id,
                    'student_name': student.name,
                    'from_class': current_class.name if current_class else None,
                    'to_class': next_class.name,
                    'promotion_id': promotion.id
                })
                
            except Exception as e:
                errors.append({
                    'student_id': student.id,
                    'student_name': student.name,
                    'error': str(e)
                })
        
        return Response({
            'message': f'Promoted {len(promoted_students)} students successfully',
            'promoted_count': len(promoted_students),
            'skipped_count': len(skipped_students),
            'error_count': len(errors),
            'promoted_students': promoted_students,
            'skipped_students': skipped_students,
            'errors': errors
        }, status=status.HTTP_200_OK)

class ClassPromotionHistoryView(APIView):
    """View promotion history for a student or class"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'teacher')
    def get(self, request):
        """
        Get promotion history.
        Query params:
        - student_id: Filter by student ID
        - class_id: Filter by class ID
        - academic_year_id: Filter by academic year
        """
        profile = UserProfile._default_manager.get(user=request.user)
        
        promotions = StudentPromotion._default_manager.filter(tenant=profile.tenant)
        
        student_id = request.query_params.get('student_id')
        class_id = request.query_params.get('class_id')
        academic_year_id = request.query_params.get('academic_year_id')
        
        if student_id:
            promotions = promotions.filter(student_id=student_id)
        
        if class_id:
            promotions = promotions.filter(
                Q(from_class_id=class_id) | Q(to_class_id=class_id)
            )
        
        if academic_year_id:
            promotions = promotions.filter(
                Q(from_academic_year_id=academic_year_id) | Q(to_academic_year_id=academic_year_id)
            )
        
        promotions = promotions.select_related(
            'student', 'from_class', 'to_class', 
            'from_academic_year', 'to_academic_year', 'promoted_by'
        ).order_by('-promotion_date', '-created_at')
        
        result = []
        for promo in promotions:
            result.append({
                'id': promo.id,
                'student_id': promo.student.id,
                'student_name': promo.student.name,
                'from_class': promo.from_class.name if promo.from_class else None,
                'to_class': promo.to_class.name if promo.to_class else None,
                'from_academic_year': promo.from_academic_year.name if promo.from_academic_year else None,
                'to_academic_year': promo.to_academic_year.name if promo.to_academic_year else None,
                'promotion_type': promo.promotion_type,
                'promotion_date': promo.promotion_date.isoformat(),
                'notes': promo.notes,
                'promoted_by': promo.promoted_by.user.username if promo.promoted_by else None,
                'created_at': promo.created_at.isoformat()
            })
        
        return Response(result)


class TransferCertificateListCreateView(APIView):
    """List and create Transfer Certificates"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def get(self, request):
        """List all TCs with filtering"""
        profile = UserProfile._default_manager.get(user=request.user)
        tcs = TransferCertificate._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        student_id = request.query_params.get('student_id')
        class_id = request.query_params.get('class_id')
        academic_year_id = request.query_params.get('academic_year_id')
        tc_number = request.query_params.get('tc_number')
        
        if student_id:
            tcs = tcs.filter(student_id=student_id)
        if class_id:
            tcs = tcs.filter(class_obj_id=class_id)
        if academic_year_id:
            tcs = tcs.filter(academic_year_id=academic_year_id)
        if tc_number:
            tcs = tcs.filter(tc_number__icontains=tc_number)
        
        serializer = TransferCertificateSerializer(tcs.order_by('-issue_date', '-created_at'), many=True)
        return Response(serializer.data)
    
    @role_required('admin', 'principal')
    def post(self, request):
        """Create a new Transfer Certificate"""
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        
        # Auto-populate student details if student_id or student provided
        student_id = data.get('student_id') or data.get('student')
        # Also handle class_obj_id vs class_obj
        if 'class_obj_id' in data and 'class_obj' not in data:
            data['class_obj'] = data['class_obj_id']
        if student_id:
            try:
                student = Student._default_manager.get(id=student_id, tenant=profile.tenant)
                if not data.get('student_name'):
                    data['student_name'] = student.name
                if not data.get('date_of_birth'):
                    data['date_of_birth'] = student.date_of_birth
                if not data.get('admission_number'):
                    data['admission_number'] = student.upper_id or str(student.id)
                if not data.get('admission_date'):
                    data['admission_date'] = student.admission_date
                if not data.get('class_obj') and not data.get('class_obj_id'):
                    data['class_obj_id'] = student.assigned_class_id
            except Student.DoesNotExist:
                return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Set issuer if not provided
        if not data.get('issued_by') and not data.get('issued_by_id'):
            data['issued_by_id'] = profile.id
        
        serializer = TransferCertificateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            tc = serializer.save(tenant=profile.tenant)
            return Response(TransferCertificateSerializer(tc).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransferCertificateDetailView(APIView):
    """Get, update, or delete a Transfer Certificate"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant', 'teacher')
    def get(self, request, pk):
        """Get a specific TC"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            tc = TransferCertificate._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = TransferCertificateSerializer(tc)
            return Response(serializer.data)
        except TransferCertificate.DoesNotExist:
            return Response({'error': 'Transfer Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def put(self, request, pk):
        """Update a TC"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            tc = TransferCertificate._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = TransferCertificateSerializer(tc, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except TransferCertificate.DoesNotExist:
            return Response({'error': 'Transfer Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def patch(self, request, pk):
        """Update a TC (partial update)"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            tc = TransferCertificate._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = TransferCertificateSerializer(tc, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except TransferCertificate.DoesNotExist:
            return Response({'error': 'Transfer Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def delete(self, request, pk):
        """Delete a TC"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            tc = TransferCertificate._default_manager.get(id=pk, tenant=profile.tenant)
            tc.delete()
            return Response({'message': 'Transfer Certificate deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except TransferCertificate.DoesNotExist:
            return Response({'error': 'Transfer Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)


class TransferCertificatePDFView(APIView):
    """Generate PDF for Transfer Certificate"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def get(self, request, pk):
        """Generate standard TC PDF"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            tc = TransferCertificate._default_manager.get(id=pk, tenant=profile.tenant)
        except TransferCertificate.DoesNotExist:
            return Response({'error': 'Transfer Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from io import BytesIO
            
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            
            # Get tenant/school info
            tenant = profile.tenant
            school_name = getattr(tenant, 'name', '') or 'School'
            
            # Get school contact information from admin user profile
            school_address = ''
            school_phone = ''
            school_email = ''
            try:
                admin_profile = UserProfile._default_manager.filter(
                    tenant=tenant, 
                    role__name='admin'
                ).first()
                if admin_profile:
                    school_address = admin_profile.address or ''
                    school_phone = admin_profile.phone or ''
                    school_email = admin_profile.user.email if admin_profile.user else ''
            except Exception:
                pass
            
            # OPTION: Remove logo completely for cleaner PDFs (or keep it small)
            REMOVE_LOGO = True  # Set to True to remove logos completely
            
            logo_drawn = False
            FIXED_TEXT_START_X = 25 * mm  # Text starts at left margin (no logo space needed)
            logo_y_top = height - 25 * mm
            
            if not REMOVE_LOGO and tenant.logo:
                try:
                    from PIL import Image
                    import os
                    logo_path = tenant.logo.path
                    if os.path.exists(logo_path):
                        img = Image.open(logo_path)
                        # Very small logo: max 15mm to avoid text overlap
                        max_height = 15 * mm
                        max_width = 15 * mm
                        img_width, img_height = img.size
                        scale = min(max_height / img_height, max_width / img_width, 1.0)
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        from reportlab.lib.utils import ImageReader
                        logo_reader = ImageReader(img)
                        # Logo at top-left corner, very small
                        logo_x = 25 * mm
                        logo_y = logo_y_top - new_height
                        p.drawImage(logo_reader, logo_x, logo_y, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
                        logo_drawn = True
                        # Adjust text start if logo is drawn
                        FIXED_TEXT_START_X = logo_x + new_width + 5 * mm
                except Exception as e:
                    logger.warning(f"Could not load tenant logo: {e}")
            
            # Text always starts at FIXED position
            p.setFillColor(colors.black)
            text_x = FIXED_TEXT_START_X  # Fixed position for text
            p.setFont('Helvetica-Bold', 18)
            school_y = logo_y_top
            p.drawString(text_x, school_y, school_name.upper())
            
            # School contact info
            info_y = school_y - 16
            p.setFont('Helvetica', 9)
            if school_address:
                max_addr_width = width - text_x - 25 * mm
                if p.stringWidth(school_address, 'Helvetica', 9) > max_addr_width:
                    addr_lines = [school_address[i:i+50] for i in range(0, min(len(school_address), 100), 50)]
                    for line in addr_lines[:2]:
                        p.drawString(text_x, info_y, line)
                        info_y -= 11
                else:
                    p.drawString(text_x, info_y, school_address)
                    info_y -= 11
            if school_phone:
                p.drawString(text_x, info_y, f"Phone: {school_phone}")
                info_y -= 11
            if school_email:
                p.drawString(text_x, info_y, f"Email: {school_email}")
                info_y -= 11
            
            # Document title
            info_y -= 5
            p.setFont('Helvetica-Bold', 14)
            p.drawString(text_x, info_y, 'TRANSFER CERTIFICATE')
            
            y = height - 110
            
            # TC Number and Date
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y, f'TC Number: {tc.tc_number}')
            p.setFont('Helvetica', 12)
            issue_date_str = tc.issue_date.strftime('%d/%m/%Y') if tc.issue_date else 'N/A'
            p.drawRightString(width - 25 * mm, y, f'Date: {issue_date_str}')
            y -= 25
            
            # Border box for TC content
            content_y_start = y
            content_height = 40 * mm
            p.setStrokeColor(colors.black)
            p.setLineWidth(1.5)
            p.rect(20 * mm, content_height, width - 40 * mm, content_y_start - content_height, stroke=1, fill=0)
            
            y -= 15
            
            # Student Information Section
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y, 'STUDENT INFORMATION')
            y -= 20
            
            # IMPROVED: Student details with proper alignment - consistent spacing
            # Two-column layout: labels on left, values aligned consistently
            label_x = 25 * mm
            value_x = 95 * mm
            value_max_width = width - value_x - 25 * mm
            
            details = [
                ('Student Name:', tc.student_name or 'N/A'),
                ('Date of Birth:', tc.date_of_birth.strftime('%d/%m/%Y') if tc.date_of_birth else 'N/A'),
                ('Admission Number:', tc.admission_number or 'N/A'),
                ('Admission Date:', tc.admission_date.strftime('%d/%m/%Y') if tc.admission_date else 'N/A'),
                ('Class:', tc.class_obj.name if tc.class_obj else 'N/A'),
                ('Academic Year:', tc.academic_year.name if tc.academic_year else 'N/A'),
                ('Last Class Promoted:', tc.last_class_promoted or 'N/A'),
            ]
            
            p.setFont('Helvetica-Bold', 10)
            for label, value in details:
                if y < content_height + 20:
                    p.showPage()
                    y = height - 40
                # Draw label
                p.drawString(label_x, y, label)
                p.setFont('Helvetica', 10)
                # IMPROVED: Truncate value if too long - ensure it fits within boundaries
                value_str = str(value)
                value_width = p.stringWidth(value_str, 'Helvetica', 10)
                if value_width > value_max_width:
                    # Binary search for optimal truncation
                    low, high = 0, len(value_str)
                    while low < high:
                        mid = (low + high + 1) // 2
                        test_str = value_str[:mid]
                        # Account for ellipsis width
                        if p.stringWidth(test_str, 'Helvetica', 10) + p.stringWidth('...', 'Helvetica', 10) <= value_max_width:
                            low = mid
                        else:
                            high = mid - 1
                    value_str = value_str[:low] + '...' if low < len(value_str) else value_str[:low]
                    # Final safety check
                    if p.stringWidth(value_str, 'Helvetica', 10) > value_max_width:
                        value_str = value_str[:max(0, len(value_str) - 3)] + '...'
                # Ensure value doesn't exceed right margin
                final_value_x = value_x
                # Validate it fits within page boundaries
                if p.stringWidth(value_str, 'Helvetica', 10) + final_value_x > width - 25 * mm:
                    # Adjust if needed
                    final_value_x = max(value_x, width - 25 * mm - p.stringWidth(value_str, 'Helvetica', 10))
                p.drawString(final_value_x, y, value_str)
                y -= 15
                p.setFont('Helvetica-Bold', 10)
            
            y -= 10
            
            # Fees and Dues Section
            if y < content_height + 30:
                p.showPage()
                y = height - 40
            
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y, 'FEES & DUES')
            y -= 20
            
            # IMPROVED: Consistent alignment for fees & dues
            p.setFont('Helvetica-Bold', 10)
            p.drawString(25 * mm, y, 'All Dues Cleared:')
            p.setFont('Helvetica', 10)
            dues_status = 'Yes' if tc.dues_paid else 'No'
            # Ensure value aligns consistently with other fields
            p.drawString(95 * mm, y, dues_status)
            y -= 15
            
            if tc.dues_details:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(25 * mm, y, 'Dues Details:')
                y -= 12
                p.setFont('Helvetica', 9)
                dues_lines = [tc.dues_details[i:i+80] for i in range(0, min(len(tc.dues_details), 240), 80)]
                for line in dues_lines[:3]:
                    if y < content_height + 15:
                        break
                    p.drawString(25 * mm, y, line)
                    y -= 11
                y -= 5
            
            y -= 10
            
            # Transfer Details Section
            if y < content_height + 30:
                p.showPage()
                y = height - 40
            
            if tc.transferring_to_school:
                p.setFont('Helvetica-Bold', 12)
                p.drawString(25 * mm, y, 'TRANSFER DETAILS')
                y -= 20
                
                # IMPROVED: Better text truncation and alignment - ensure it fits within boundaries
                p.setFont('Helvetica-Bold', 10)
                p.drawString(25 * mm, y, 'Transferring To:')
                p.setFont('Helvetica', 10)
                school_name = str(tc.transferring_to_school)
                # Calculate max width and truncate if needed - ensure it doesn't exceed page margin
                max_school_width = width - 95 * mm - 25 * mm  # Available width from value position to right margin
                if p.stringWidth(school_name, 'Helvetica', 10) > max_school_width:
                    # Binary search for optimal truncation
                    low, high = 0, len(school_name)
                    while low < high:
                        mid = (low + high + 1) // 2
                        test_str = school_name[:mid]
                        # Account for ellipsis width
                        if p.stringWidth(test_str, 'Helvetica', 10) + p.stringWidth('...', 'Helvetica', 10) <= max_school_width:
                            low = mid
                        else:
                            high = mid - 1
                    school_name_trunc = school_name[:low] + '...' if low < len(school_name) else school_name[:low]
                    # Final safety check
                    if p.stringWidth(school_name_trunc, 'Helvetica', 10) > max_school_width:
                        school_name_trunc = school_name_trunc[:max(0, len(school_name_trunc) - 5)] + '...'
                else:
                    school_name_trunc = school_name
                # Ensure it doesn't exceed right margin
                final_x = min(95 * mm, width - 25 * mm - p.stringWidth(school_name_trunc, 'Helvetica', 10))
                p.drawString(final_x, y, school_name_trunc)
                y -= 15
                
                if tc.transferring_to_address:
                    p.setFont('Helvetica-Bold', 10)
                    p.drawString(25 * mm, y, 'Address:')
                    y -= 12
                    p.setFont('Helvetica', 9)
                    addr_lines = [tc.transferring_to_address[i:i+80] for i in range(0, min(len(tc.transferring_to_address), 240), 80)]
                    for line in addr_lines[:3]:
                        if y < content_height + 15:
                            break
                        p.drawString(25 * mm, y, line)
                        y -= 11
            
            y -= 10
            
            # Reason and Remarks
            if y < content_height + 40:
                p.showPage()
                y = height - 40
            
            if tc.reason_for_leaving:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(25 * mm, y, 'Reason for Leaving:')
                y -= 12
                p.setFont('Helvetica', 10)
                reason_trunc = str(tc.reason_for_leaving)[:80] if len(str(tc.reason_for_leaving)) > 80 else str(tc.reason_for_leaving)
                p.drawString(25 * mm, y, reason_trunc)
                y -= 20
            
            if tc.conduct_remarks:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(25 * mm, y, 'Conduct Remarks:')
                y -= 12
                p.setFont('Helvetica', 10)
                conduct_trunc = str(tc.conduct_remarks)[:90] if len(str(tc.conduct_remarks)) > 90 else str(tc.conduct_remarks)
                p.drawString(25 * mm, y, conduct_trunc)
                y -= 20
            
            if tc.remarks:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(25 * mm, y, 'Additional Remarks:')
                y -= 12
                p.setFont('Helvetica', 9)
                remarks_lines = [tc.remarks[i:i+85] for i in range(0, min(len(tc.remarks), 255), 85)]
                for line in remarks_lines[:4]:
                    if y < content_height + 15:
                        break
                    p.drawString(25 * mm, y, line)
                    y -= 11
            
            # Authority signatures section (bottom)
            p.showPage()
            y = height - 60
            
            p.setFont('Helvetica-Bold', 11)
            p.drawString(25 * mm, y, 'AUTHORITY SIGNATURES')
            y -= 25
            
            # Issued by
            if tc.issued_by:
                issuer_name = tc.issued_by.user.get_full_name() or tc.issued_by.user.username if tc.issued_by.user else 'N/A'
                p.setFont('Helvetica', 10)
                p.drawString(25 * mm, y, f'Issued By: {issuer_name}')
                y -= 20
                p.drawString(25 * mm, y, 'Signature: ___________________')
                y -= 25
            
            # Approved by
            if tc.approved_by:
                approver_name = tc.approved_by.user.get_full_name() or tc.approved_by.user.username if tc.approved_by.user else 'N/A'
                p.setFont('Helvetica', 10)
                p.drawString(25 * mm, y, f'Approved By: {approver_name}')
                y -= 20
                p.drawString(25 * mm, y, 'Signature: ___________________')
            
            # Footer
            p.setFont('Helvetica', 8)
            p.setFillColor(colors.black)
            footer_text = f"Generated on {timezone.now().strftime('%d-%m-%Y at %I:%M %p')} — {school_name.upper()}"
            p.drawCentredString(width / 2, 20 * mm, footer_text)
            
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            tc_filename = f"transfer_certificate_{tc.tc_number}_{tc.id}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{tc_filename}"'
            return response
            
        except ImportError as e:
            logger.error(f"PDF generation import error: {str(e)}", exc_info=True)
            return Response({
                'error': 'PDF generation library not installed.',
                'details': 'Install required packages: pip install reportlab Pillow'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error generating TC PDF: {str(e)}", exc_info=True)
            return Response({
                'error': f'TC PDF generation failed: {str(e)}',
                'details': 'Check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdmissionApplicationListCreateView(APIView):
    """List and create Admission Applications"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def get(self, request):
        """List all admission applications with filtering"""
        profile = UserProfile._default_manager.get(user=request.user)
        applications = AdmissionApplication._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        status_filter = request.query_params.get('status')
        class_id = request.query_params.get('class_id')
        search = request.query_params.get('search')
        
        if status_filter:
            applications = applications.filter(status=status_filter)
        if class_id:
            applications = applications.filter(desired_class_id=class_id)
        if search:
            applications = applications.filter(
                Q(applicant_name__icontains=search) | 
                Q(email__icontains=search) | 
                Q(phone__icontains=search)
            )
        
        serializer = AdmissionApplicationSerializer(applications.order_by('-created_at'), many=True)
        return Response(serializer.data)
    
    @role_required('admin', 'principal')
    def post(self, request):
        """Create a new admission application"""
        profile = UserProfile._default_manager.get(user=request.user)
        data = request.data.copy()
        data['tenant'] = profile.tenant.id
        
        serializer = AdmissionApplicationSerializer(data=data)
        if serializer.is_valid():
            application = serializer.save(tenant=profile.tenant)
            return Response(AdmissionApplicationSerializer(application).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdmissionApplicationDetailView(APIView):
    """Get, update, or delete an Admission Application"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal', 'accountant')
    def get(self, request, pk):
        """Get a specific admission application"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            application = AdmissionApplication._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = AdmissionApplicationSerializer(application)
            return Response(serializer.data)
        except AdmissionApplication.DoesNotExist:
            return Response({'error': 'Admission Application not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def put(self, request, pk):
        """Update an admission application"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            application = AdmissionApplication._default_manager.get(id=pk, tenant=profile.tenant)
            serializer = AdmissionApplicationSerializer(application, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except AdmissionApplication.DoesNotExist:
            return Response({'error': 'Admission Application not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def delete(self, request, pk):
        """Delete an admission application"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            application = AdmissionApplication._default_manager.get(id=pk, tenant=profile.tenant)
            application.delete()
            return Response({'message': 'Admission Application deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except AdmissionApplication.DoesNotExist:
            return Response({'error': 'Admission Application not found.'}, status=status.HTTP_404_NOT_FOUND)


class AdmissionApplicationApproveView(APIView):
    """Approve an admission application and optionally convert to student"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal')
    def post(self, request, pk):
        """Approve admission application and optionally create student record"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            application = AdmissionApplication._default_manager.get(id=pk, tenant=profile.tenant)
        except AdmissionApplication.DoesNotExist:
            return Response({'error': 'Admission Application not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Update status to approved
        application.status = 'approved'
        application.save()
        
        # Optionally convert to student
        create_student = request.data.get('create_student', False)
        student_data = None
        
        if create_student:
            # Get additional student data from request
            student_name = request.data.get('student_name') or application.applicant_name
            student_email = request.data.get('student_email') or application.email
            student_phone = request.data.get('student_phone') or application.phone
            upper_id = request.data.get('upper_id', '')
            admission_date = request.data.get('admission_date')
            assigned_class_id = request.data.get('assigned_class_id') or (application.desired_class.id if application.desired_class else None)
            
            if not assigned_class_id:
                return Response({'error': 'Class assignment required to create student.'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                # Create student
                student = Student._default_manager.create(
                    tenant=profile.tenant,
                    name=student_name,
                    email=student_email,
                    phone=student_phone,
                    upper_id=upper_id,
                    assigned_class_id=assigned_class_id,
                    admission_date=admission_date or timezone.now().date(),
                    is_active=True
                )
                student_data = StudentSerializer(student).data
            except Exception as e:
                logger.error(f"Error creating student from application: {str(e)}", exc_info=True)
                return Response({'error': f'Failed to create student: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        serializer = AdmissionApplicationSerializer(application)
        return Response({
            'message': 'Application approved successfully.',
            'application': serializer.data,
            'student': student_data
        }, status=status.HTTP_200_OK)


class AdmissionApplicationRejectView(APIView):
    """Reject an admission application"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    @role_required('admin', 'principal')
    def post(self, request, pk):
        """Reject admission application"""
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            application = AdmissionApplication._default_manager.get(id=pk, tenant=profile.tenant)
            application.status = 'rejected'
            # Optionally add rejection reason to notes
            rejection_reason = request.data.get('rejection_reason', '')
            if rejection_reason:
                application.notes = f"{application.notes or ''}\nRejection Reason: {rejection_reason}".strip()
            application.save()
            serializer = AdmissionApplicationSerializer(application)
            return Response({
                'message': 'Application rejected successfully.',
                'application': serializer.data
            }, status=status.HTTP_200_OK)
        except AdmissionApplication.DoesNotExist:
            return Response({'error': 'Admission Application not found.'}, status=status.HTTP_404_NOT_FOUND) 