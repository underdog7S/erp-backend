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
    OldBalance, BalanceAdjustment
)
from api.models.permissions import HasFeaturePermissionFactory, role_required, role_exclude
from api.models.serializers_education import (
    ClassSerializer, StudentSerializer, FeeStructureSerializer, FeePaymentSerializer, 
    FeeDiscountSerializer, AttendanceSerializer, ReportCardSerializer, 
    StaffAttendanceSerializer, DepartmentSerializer, AcademicYearSerializer, 
    TermSerializer, SubjectSerializer, UnitSerializer, AssessmentTypeSerializer, 
    AssessmentSerializer, MarksEntrySerializer, FeeInstallmentPlanSerializer, 
    FeeInstallmentSerializer, OldBalanceSerializer, BalanceAdjustmentSerializer
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
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        classes = Class._default_manager.filter(tenant=profile.tenant)  # type: ignore
        serializer = ClassSerializer(classes, many=True)
        return Response(serializer.data)

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
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        if profile.role and profile.role.name == 'admin':
            attendance = Attendance._default_manager.filter(tenant=profile.tenant)  # type: ignore
        else:
            # Staff: only attendance for students in their assigned classes
            attendance = Attendance._default_manager.filter(tenant=profile.tenant, student__assigned_class__in=profile.assigned_classes.all())  # type: ignore
        serializer = AttendanceSerializer(attendance, many=True)
        return Response(serializer.data)

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
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        reportcards = ReportCard._default_manager.filter(tenant=profile.tenant)
        serializer = ReportCardSerializer(reportcards, many=True)
        return Response(serializer.data)

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
        profile = UserProfile._default_manager.get(user=request.user)
        assessment_types = AssessmentType._default_manager.filter(tenant=profile.tenant)
        serializer = AssessmentTypeSerializer(assessment_types, many=True)
        return Response(serializer.data)

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
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from io import BytesIO

            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            # Header banner with school name and logo
            tenant = profile.tenant
            school_name = getattr(tenant, 'name', '') or 'School'
            
            # Header banner (draw first)
            p.setFillColor(colors.HexColor('#1a237e'))  # Classic deep blue
            p.rect(0, height - 65, width, 65, stroke=0, fill=1)
            
            # Draw logo in top-right corner (small, 20mm max, properly positioned)
            logo_drawn = False
            if tenant.logo:
                try:
                    from PIL import Image
                    import os
                    from django.conf import settings
                    logo_path = tenant.logo.path
                    if os.path.exists(logo_path):
                        img = Image.open(logo_path)
                        # Resize logo to be small (max 20mm height for corner)
                        max_height = 20 * mm
                        img_width, img_height = img.size
                        scale = min(max_height / img_height, max_height / img_width)
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        # Convert to RGB if needed
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        from reportlab.lib.utils import ImageReader
                        logo_reader = ImageReader(img)
                        # Position in top-right corner with proper margin (avoid text overlap)
                        logo_x = width - 20 * mm - new_width
                        logo_y = height - 15 - new_height
                        p.drawImage(logo_reader, logo_x, logo_y, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
                        logo_drawn = True
                except Exception as e:
                    logger.warning(f"Could not load tenant logo: {e}")
            
            # School name and title (left side, white text on blue background)
            p.setFillColor(colors.white)  # White text for visibility on blue
            p.setFont('Helvetica-Bold', 22)
            p.drawString(20 * mm, height - 25, school_name.upper())
            p.setFont('Helvetica', 11)
            p.drawString(20 * mm, height - 40, 'OFFICIAL REPORT CARD')
            p.setFont('Helvetica-Bold', 14)
            p.drawRightString(width - 25 * mm, height - 35, 'ACADEMIC REPORT')

            y = height - 60
            p.setFillColor(colors.black)

            # Classic styled student information box - properly aligned
            y = height - 80
            p.setFillColor(colors.HexColor('#f5f5f5'))
            p.rect(20 * mm, y - 60, width - 40 * mm, 60, stroke=1, fill=1)
            # Header text with proper contrast
            p.setFillColor(colors.HexColor('#1a237e'))  # Dark blue text on light gray background
            p.setFont('Helvetica-Bold', 14)
            p.drawString(25 * mm, y - 10, 'STUDENT INFORMATION')
            y -= 20
            
            # Student details in classic two-column layout - properly aligned
            p.setFillColor(colors.black)
            label_x = 25 * mm
            value_x = 75 * mm
            label_x2 = 130 * mm
            value_x2 = 160 * mm
            
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
            
            issued_str = report_card.issued_date.strftime('%d-%m-%Y') if report_card.issued_date else report_card.generated_at.strftime('%d-%m-%Y')
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Issued Date:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x2, y, issued_str)
            
            if upper_val:
                y -= 15
                p.setFont('Helvetica-Bold', 11)
                p.drawString(25 * mm, y, 'Student ID:')
                p.setFont('Helvetica', 11)
                p.drawString(70 * mm, y, upper_val)
            
            y -= 20

            # Classic styled marks table header - properly aligned
            p.setFillColor(colors.HexColor('#1a237e'))  # Dark blue background
            p.rect(20 * mm, y - 12, width - 40 * mm, 12, stroke=0, fill=1)
            p.setFillColor(colors.white)  # White text on blue background
            p.setFont('Helvetica-Bold', 10)
            headers = ['SUBJECT', 'MARKS OBTAINED', 'MAX MARKS', 'PERCENTAGE']
            # Better column positions for proper alignment
            col_x = [25 * mm, 120 * mm, 150 * mm, 175 * mm]
            col_widths = [90 * mm, 25 * mm, 20 * mm, 20 * mm]
            for i, htxt in enumerate(headers):
                if i == 0:
                    # Left align subject
                    p.drawString(col_x[i], y - 8, htxt)
                else:
                    # Right align numbers
                    p.drawRightString(col_x[i] + col_widths[i], y - 8, htxt)
            p.setFillColor(colors.black)  # Black text for table rows
            y -= 15

            # Table rows with alternating colors - properly aligned
            from education.models import MarksEntry
            marks_entries = MarksEntry.objects.filter(
                tenant=report_card.tenant,
                student=report_card.student,
                assessment__term=report_card.term
            ).select_related('assessment', 'assessment__subject').order_by('assessment__subject__name')

            p.setFont('Helvetica', 10)
            row_num = 0
            for entry in marks_entries:
                if y < 80:
                    # New page - reset background
                    p.showPage()
                    # Redraw header on new page
                    p.setFillColor(colors.HexColor('#1a237e'))
                    p.rect(20 * mm, height - 40 - 12, width - 40 * mm, 12, stroke=0, fill=1)
                    p.setFillColor(colors.white)
                    p.setFont('Helvetica-Bold', 10)
                    for i, htxt in enumerate(headers):
                        if i == 0:
                            p.drawString(col_x[i], height - 40 - 8, htxt)
                        else:
                            p.drawRightString(col_x[i] + col_widths[i], height - 40 - 8, htxt)
                    p.setFillColor(colors.black)
                    p.setFont('Helvetica', 10)
                    y = height - 40 - 15
                    row_num = 0  # Reset row number for alternating
                
                subject_name = entry.assessment.subject.name if entry.assessment and entry.assessment.subject else 'N/A'
                percent = (float(entry.marks_obtained) / float(entry.max_marks) * 100) if entry.max_marks else 0
                
                # Alternating row background - ensure it doesn't bleed
                if row_num % 2 == 0:
                    p.setFillColor(colors.HexColor('#f9f9f9'))
                    # Ensure rectangle stays within page bounds
                    rect_y = max(y - 12, 30 * mm)  # Don't go below 30mm from bottom
                    p.rect(20 * mm, rect_y, width - 40 * mm, 12, stroke=0, fill=1)
                    p.setFillColor(colors.black)
                
                # Properly aligned values
                p.drawString(col_x[0], y, subject_name[:30])  # Left align subject
                # Right align numbers for proper alignment
                marks_str = str(int(float(entry.marks_obtained)))
                p.drawRightString(col_x[1] + col_widths[1], y, marks_str)
                max_marks_str = str(int(float(entry.max_marks)))
                p.drawRightString(col_x[2] + col_widths[2], y, max_marks_str)
                percent_str = f"{percent:.1f}%"
                p.drawRightString(col_x[3] + col_widths[3], y, percent_str)
                y -= 14
                row_num += 1

            # Classic styled summary box
            y -= 10
            p.setFillColor(colors.HexColor('#1a237e'))  # Dark blue background
            p.rect(20 * mm, y - 50, width - 40 * mm, 50, stroke=1, fill=1)
            p.setFillColor(colors.white)  # White text on blue background
            p.setFont('Helvetica-Bold', 14)
            p.drawString(25 * mm, y - 12, 'ACADEMIC SUMMARY')
            # Summary values in white on blue background
            p.setFillColor(colors.white)
            y -= 20
            
            # Summary in elegant layout (white text on blue background)
            p.setFillColor(colors.white)  # Keep white for text on blue
            summary_items = [
                ('Total Marks', f"{float(report_card.total_marks)} / {float(report_card.max_total_marks)}"),
                ('Percentage', f"{float(report_card.percentage):.2f}%"),
                ('Grade', report_card.grade),
            ]
            if report_card.rank_in_class:
                summary_items.append(('Class Rank', f"#{report_card.rank_in_class}"))
            
            x_start = 25 * mm
            item_width = (width - 50 * mm) / len(summary_items)
            for i, (label, value) in enumerate(summary_items):
                x_pos = x_start + (i * item_width)
                p.setFont('Helvetica-Bold', 10)
                p.drawString(x_pos, y, label + ':')
                p.setFont('Helvetica', 11)
                p.drawString(x_pos, y - 12, value)
            p.setFillColor(colors.black)  # Switch back to black for rest
            y -= 25

            # Attendance and Conduct in styled box
            p.setFillColor(colors.HexColor('#f5f5f5'))  # Light gray background
            p.rect(20 * mm, y - 40, width - 40 * mm, 40, stroke=1, fill=1)
            p.setFillColor(colors.HexColor('#1a237e'))  # Dark blue text on light gray (good contrast)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 10, 'ATTENDANCE & CONDUCT')
            p.setFillColor(colors.black)  # Black text for content
            y -= 18
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(25 * mm, y, 'Days Present:')
            p.setFont('Helvetica', 10)
            p.drawString(75 * mm, y, str(report_card.days_present))
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(100 * mm, y, 'Days Absent:')
            p.setFont('Helvetica', 10)
            p.drawString(150 * mm, y, str(report_card.days_absent))
            y -= 12
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(25 * mm, y, 'Attendance Percentage:')
            p.setFont('Helvetica', 10)
            p.drawString(85 * mm, y, f"{float(report_card.attendance_percentage):.2f}%")
            
            if report_card.conduct_grade:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(140 * mm, y, 'Conduct Grade:')
                p.setFont('Helvetica', 10)
                p.drawString(165 * mm, y, report_card.conduct_grade)
            y -= 22

            # Remarks in styled sections
            if report_card.teacher_remarks or report_card.principal_remarks:
                remarks_height = 0
                if report_card.teacher_remarks:
                    remarks_height += (len(report_card.teacher_remarks) // 95 + 1) * 12 + 20
                if report_card.principal_remarks:
                    remarks_height += (len(report_card.principal_remarks) // 95 + 1) * 12 + 20
                
                p.setFillColor(colors.HexColor('#fff9e6'))  # Cream background
                p.rect(20 * mm, y - remarks_height - 15, width - 40 * mm, remarks_height + 15, stroke=1, fill=1)
                p.setFillColor(colors.HexColor('#8b6914'))  # Brown text on cream (good contrast)
                p.setFont('Helvetica-Bold', 12)
                p.drawString(25 * mm, y - 10, 'REMARKS')
                p.setFillColor(colors.black)  # Black text for remarks content
                y -= 18
                
                p.setFont('Helvetica', 10)
                def wrap(text, max_chars=95):
                    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)] if text else []
                
                if report_card.teacher_remarks:
                    p.setFont('Helvetica-Bold', 10)
                    p.drawString(25 * mm, y, 'Class Teacher:')
                    y -= 12
                    p.setFont('Helvetica', 9)
                    for line in wrap(report_card.teacher_remarks):
                        p.drawString(25 * mm, y, line)
                        y -= 12
                    y -= 6
                
                if report_card.principal_remarks:
                    p.setFont('Helvetica-Bold', 10)
                    p.drawString(25 * mm, y, 'Principal:')
                    y -= 12
                    p.setFont('Helvetica', 9)
                    for line in wrap(report_card.principal_remarks):
                        p.drawString(25 * mm, y, line)
                        y -= 12
                y -= 8

            # Classic signature section
            p.setFillColor(colors.HexColor('#f5f5f5'))
            p.rect(20 * mm, 20 * mm, width - 40 * mm, 35, stroke=1, fill=1)
            
            # Signature lines with labels
            p.setStrokeColor(colors.black)
            p.setLineWidth(0.5)
            
            # Class Teacher signature
            p.line(30 * mm, 42 * mm, 75 * mm, 42 * mm)
            p.setFont('Helvetica-Bold', 9)
            p.drawString(30 * mm, 38 * mm, 'Class Teacher')
            p.setFont('Helvetica', 8)
            p.drawString(30 * mm, 33 * mm, '(Signature & Seal)')
            
            # Principal signature
            p.line(110 * mm, 42 * mm, 165 * mm, 42 * mm)
            p.setFont('Helvetica-Bold', 9)
            p.drawString(110 * mm, 38 * mm, 'Principal')
            p.setFont('Helvetica', 8)
            p.drawString(110 * mm, 33 * mm, '(Signature & Seal)')
            
            # Footer with classic styling
            p.setFont('Helvetica', 8)
            p.setFillColor(colors.HexColor('#666666'))
            footer_text = f"Generated on {report_card.generated_at.strftime('%d-%m-%Y at %I:%M %p')} — {school_name.upper()}"
            p.drawCentredString(width / 2, 20 * mm, footer_text)
            p.setFillColor(colors.HexColor('#1a237e'))
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
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
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
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="students.csv"'
            writer = csv.writer(response)
            writer.writerow(["ID", "Name", "Email", "Admission Date", "Assigned Class"])
            for s in students:
                writer.writerow([
                    s.id,
                    s.name,
                    s.email,
                    s.admission_date.strftime('%Y-%m-%d'),
                    s.assigned_class.name if s.assigned_class else ""
                ])
            return response 

class ClassFeeStructureListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        # Allow admin, accountant, principal, and teacher to view fee structures (read-only for teachers)
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal', 'teacher']:
            return Response({'error': 'You do not have permission to view fee structures.'}, status=status.HTTP_403_FORBIDDEN)
        fee_structures = FeeStructure._default_manager.filter(tenant=profile.tenant)  # type: ignore
        serializer = FeeStructureSerializer(fee_structures, many=True)
        return Response(serializer.data)

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
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
            
            # Classic header with deep blue banner (draw first)
            p.setFillColor(colors.HexColor('#1a237e'))
            p.rect(0, height - 55, width, 55, stroke=0, fill=1)
            
            # Draw logo in top-right corner (small, 18mm max, properly positioned)
            if tenant.logo:
                try:
                    from PIL import Image
                    import os
                    logo_path = tenant.logo.path
                    if os.path.exists(logo_path):
                        img = Image.open(logo_path)
                        # Resize logo to be small (max 18mm height for corner)
                        max_height = 18 * mm
                        img_width, img_height = img.size
                        scale = min(max_height / img_height, max_height / img_width)
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        from reportlab.lib.utils import ImageReader
                        logo_reader = ImageReader(img)
                        # Position in top-right corner with proper margin (avoid text overlap)
                        logo_x = width - 18 * mm - new_width
                        logo_y = height - 12 - new_height
                        p.drawImage(logo_reader, logo_x, logo_y, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
                except Exception as e:
                    logger.warning(f"Could not load tenant logo: {e}")
            
            # School name and title (left side, white text on blue background)
            p.setFillColor(colors.white)  # White text for visibility on blue
            p.setFont('Helvetica-Bold', 20)
            p.drawString(20 * mm, height - 20, school_name.upper())
            p.setFont('Helvetica', 10)
            p.drawString(20 * mm, height - 35, 'OFFICIAL FEE PAYMENT RECEIPT')
            
            y = height - 70
            p.setFillColor(colors.black)

            # Receipt number and date box
            p.setFillColor(colors.HexColor('#f5f5f5'))  # Light gray background
            p.rect(20 * mm, y - 35, width - 40 * mm, 35, stroke=1, fill=1)
            p.setFillColor(colors.HexColor('#1a237e'))  # Dark blue text on light gray (good contrast)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 8, 'RECEIPT DETAILS')
            p.setFillColor(colors.black)  # Black text for content
            y -= 18
            
            receipt_number = payment.receipt_number or f"RCP-{payment.id:08X}"
            payment_date = payment.payment_date.strftime('%d/%m/%Y')
            
            p.setFont('Helvetica-Bold', 11)
            p.drawString(25 * mm, y, 'Receipt Number:')
            p.setFont('Helvetica', 11)
            p.drawString(75 * mm, y, receipt_number)
            
            p.setFont('Helvetica-Bold', 11)
            p.drawString(130 * mm, y, 'Date:')
            p.setFont('Helvetica', 11)
            p.drawString(150 * mm, y, payment_date)
            y -= 18

            # Student information box - properly aligned
            p.setFillColor(colors.HexColor('#f9f9f9'))  # Light gray background
            p.rect(20 * mm, y - 50, width - 40 * mm, 50, stroke=1, fill=1)
            p.setFillColor(colors.HexColor('#1a237e'))  # Dark blue text on light gray (good contrast)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 8, 'STUDENT INFORMATION')
            p.setFillColor(colors.black)  # Black text for content
            y -= 18
            
            student_name = payment.student.name if payment.student else 'N/A'
            roll_number = getattr(payment.student, 'roll_number', None) or getattr(payment.student, 'admission_number', None) or 'N/A'
            class_name = payment.student.assigned_class.name if payment.student and payment.student.assigned_class else 'N/A'
            
            # Properly aligned labels and values
            label_x = 25 * mm
            value_x = 75 * mm
            label_x2 = 130 * mm
            value_x2 = 160 * mm
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Student Name:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x, y, student_name.upper())
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Roll Number:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x2, y, str(roll_number))
            y -= 15
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Class:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x, y, class_name)
            
            fee_type = payment.fee_structure.fee_type if payment.fee_structure else 'N/A'
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x2, y, 'Fee Type:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x2, y, fee_type)
            y -= 35

            # Payment details box - properly aligned
            p.setFillColor(colors.HexColor('#fff9e6'))  # Cream background
            p.rect(20 * mm, y - 60, width - 40 * mm, 60, stroke=1, fill=1)
            p.setFillColor(colors.HexColor('#8b6914'))  # Brown text on cream (good contrast)
            p.setFont('Helvetica-Bold', 12)
            p.drawString(25 * mm, y - 8, 'PAYMENT INFORMATION')
            p.setFillColor(colors.black)  # Black text for content
            y -= 18
            
            payment_method = payment.get_payment_method_display() if hasattr(payment, 'get_payment_method_display') else payment.payment_method or 'CASH'
            amount_paid = float(payment.amount_paid)
            total_fee = float(payment.fee_structure.amount) if payment.fee_structure else amount_paid
            remaining = max(0, total_fee - amount_paid)
            discount = float(payment.discount_amount) if payment.discount_amount else 0
            
            # Properly aligned labels and values
            label_x = 25 * mm
            value_x = 75 * mm
            label_x2 = 130 * mm
            value_x2 = 165 * mm
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Payment Method:')
            p.setFont('Helvetica', 10)
            p.drawString(value_x, y, payment_method.upper())
            
            if discount > 0:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(label_x2, y, 'Discount:')
                p.setFont('Helvetica', 10)
                p.drawRightString(value_x2, y, f"₹{discount:.2f}")  # Right align currency
            y -= 15
            
            p.setFont('Helvetica-Bold', 10)
            p.drawString(label_x, y, 'Amount Paid:')
            p.setFont('Helvetica', 11)
            p.setFillColor(colors.HexColor('#2e7d32'))
            p.drawRightString(value_x2, y, f"₹{amount_paid:.2f}")  # Right align currency
            p.setFillColor(colors.black)
            
            if payment.fee_structure:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(label_x2, y, 'Total Fee:')
                p.setFont('Helvetica', 10)
                p.drawRightString(value_x2, y, f"₹{total_fee:.2f}")  # Right align currency
            y -= 15
            
            if payment.fee_structure and remaining > 0:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(label_x, y, 'Remaining:')
                p.setFont('Helvetica', 10)
                p.setFillColor(colors.HexColor('#d32f2f'))
                p.drawRightString(value_x2, y, f"₹{remaining:.2f}")  # Right align currency
                p.setFillColor(colors.black)
            y -= 25

            # Notes section (if exists)
            if payment.notes:
                p.setFont('Helvetica-Bold', 10)
                p.drawString(25 * mm, y, 'Notes:')
                y -= 12
                p.setFont('Helvetica', 9)
                # Wrap notes text
                notes_lines = [payment.notes[i:i+95] for i in range(0, len(payment.notes), 95)]
                for line in notes_lines[:3]:  # Max 3 lines
                    p.drawString(25 * mm, y, line)
                    y -= 12
                y -= 8
            else:
                y -= 15

            # Total amount highlight box
            p.setFillColor(colors.HexColor('#1a237e'))  # Dark blue background
            p.rect(20 * mm, y - 35, width - 40 * mm, 35, stroke=1, fill=1)
            p.setFillColor(colors.white)  # White text on blue background
            p.setFont('Helvetica-Bold', 14)
            p.drawString(25 * mm, y - 12, 'TOTAL AMOUNT PAID:')
            p.setFont('Helvetica-Bold', 18)
            p.drawRightString(width - 25 * mm, y - 10, f"₹{amount_paid:.2f}")
            p.setFillColor(colors.black)  # Switch back to black
            y -= 45

            # Thank you message (dark blue text on white background)
            p.setFont('Helvetica', 11)
            p.setFillColor(colors.HexColor('#1a237e'))  # Dark blue text on white (good contrast)
            p.drawCentredString(width / 2, y, 'Thank you for your payment!')
            y -= 15

            # Footer
            p.setFont('Helvetica', 8)
            p.setFillColor(colors.HexColor('#666666'))
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
        except Exception:
            pass
        
        serializer = FeeInstallmentSerializer(installments, many=True)
        return Response(serializer.data)

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

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
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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