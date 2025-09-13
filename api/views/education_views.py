import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
from education.models import Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, ReportCard, StaffAttendance, Department
from api.models.permissions import HasFeaturePermissionFactory, role_required, role_exclude
from api.models.serializers_education import ClassSerializer, StudentSerializer, FeeStructureSerializer, FeePaymentSerializer, FeeDiscountSerializer, AttendanceSerializer, ReportCardSerializer, StaffAttendanceSerializer, DepartmentSerializer
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
        if profile.role and profile.role.name in ['admin', 'accountant']:
            students = Student._default_manager.filter(tenant=profile.tenant)  # type: ignore
        else:
            # Staff: only students in their assigned classes
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
        serializer = StudentSerializer(data=data)
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

    @role_required('admin', 'principal')
    def put(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            s = Student._default_manager.get(id=pk, tenant=profile.tenant)  # type: ignore
            serializer = StudentSerializer(s, data=request.data, partial=True)
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
            serializer = FeeSerializer(f)
            return Response(serializer.data)
        except Fee.DoesNotExist:  # type: ignore
            return Response({'error': 'Fee record not found.'}, status=status.HTTP_404_NOT_FOUND)

    # @role_required('admin', 'principal', 'accountant')
    # def put(self, request, pk):
    #     pass

    # @role_required('admin', 'principal', 'accountant')
    # def delete(self, request, pk):
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
        data['tenant'] = profile.tenant.id
        serializer = ReportCardSerializer(data=data)
        if serializer.is_valid():
            serializer.save(tenant=profile.tenant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can view fee structures.'}, status=status.HTTP_403_FORBIDDEN)
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can view admin summary.'}, status=status.HTTP_403_FORBIDDEN)
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can view class stats.'}, status=status.HTTP_403_FORBIDDEN)
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can view monthly reports.'}, status=status.HTTP_403_FORBIDDEN)
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can export class stats.'}, status=status.HTTP_403_FORBIDDEN)
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can export monthly reports.'}, status=status.HTTP_403_FORBIDDEN)
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
        if not profile.role or profile.role.name not in ['admin', 'principal']:
            return Response({'error': 'Only admins and principals can view departments.'}, status=status.HTTP_403_FORBIDDEN)
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
        if profile.role and profile.role.name in ['admin', 'accountant']:
            # Admin can see all fee payments
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

    @role_required('admin', 'principal', 'accountant')
    def delete(self, request, pk):
        profile = UserProfile._default_manager.get(user=request.user)
        try:
            payment = FeePayment._default_manager.get(id=pk, tenant=profile.tenant)
        except Exception:
            return Response({'error': 'Fee payment not found.'}, status=status.HTTP_404_NOT_FOUND)
        payment.delete()
        return Response({'message': 'Fee payment deleted.'}) 

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
        if not profile.role or profile.role.name not in ['admin', 'accountant', 'principal', 'teacher']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        fee_structures = FeeStructure._default_manager.filter(tenant=profile.tenant)
        serializer = FeeStructureSerializer(fee_structures, many=True)
        return Response(serializer.data) 

class ClassAttendanceStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)  # type: ignore
        tenant = profile.tenant
        classes = Class._default_manager.filter(tenant=tenant)  # type: ignore
        data = []
        for c in classes:
            total_students = Student._default_manager.filter(tenant=tenant, assigned_class=c).count()  # type: ignore
            present_today = Attendance._default_manager.filter(tenant=tenant, assigned_class=c, date=timezone.now().date(), present=True).count()  # type: ignore
            absent_today = Attendance._default_manager.filter(tenant=tenant, assigned_class=c, date=timezone.now().date(), present=False).count()  # type: ignore
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can export fee structures.'}, status=status.HTTP_403_FORBIDDEN)
        
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can export fee payments.'}, status=status.HTTP_403_FORBIDDEN)
        
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
        if not profile.role or profile.role.name not in ['admin', 'accountant']:
            return Response({'error': 'Only admins and accountants can export fee discounts.'}, status=status.HTTP_403_FORBIDDEN)
        
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