"""
Advanced Reporting System - Custom Report Builder and Comparative Analysis
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
from education.models import (
    ReportTemplate, ReportField, ReportCard, MarksEntry, Attendance, 
    Student, Class, AcademicYear, Term, Subject, FeePayment
)
from api.models.permissions import HasFeaturePermissionFactory, role_required
from api.models.serializers_education import (
    ReportTemplateSerializer, ReportFieldSerializer, ReportDataSerializer
)
from django.db.models import Q, Count, Sum, Avg, Max, Min, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================
# REPORT FIELD MANAGEMENT
# ============================================

class ReportFieldListCreateView(APIView):
    """List and create report fields"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            fields = ReportField.objects.filter(tenant=profile.tenant, is_active=True)
            serializer = ReportFieldSerializer(fields, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            serializer = ReportFieldSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class ReportFieldDetailView(APIView):
    """Get, update, delete report field"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            field = ReportField.objects.get(id=pk, tenant=profile.tenant)
            serializer = ReportFieldSerializer(field)
            return Response(serializer.data)
        except ReportField.DoesNotExist:
            return Response({'error': 'Report field not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            field = ReportField.objects.get(id=pk, tenant=profile.tenant)
            serializer = ReportFieldSerializer(field, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ReportField.DoesNotExist:
            return Response({'error': 'Report field not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal')
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            field = ReportField.objects.get(id=pk, tenant=profile.tenant)
            field.is_active = False
            field.save()
            return Response({'message': 'Report field deleted.'}, status=status.HTTP_204_NO_CONTENT)
        except ReportField.DoesNotExist:
            return Response({'error': 'Report field not found.'}, status=status.HTTP_404_NOT_FOUND)


# ============================================
# REPORT TEMPLATE MANAGEMENT
# ============================================

class ReportTemplateListCreateView(APIView):
    """List and create report templates"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            templates = ReportTemplate.objects.filter(
                tenant=profile.tenant,
                is_active=True
            ).filter(
                Q(is_public=True) | Q(created_by=profile)
            )
            serializer = ReportTemplateSerializer(templates, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            data = request.data.copy()
            data['created_by'] = profile.id
            serializer = ReportTemplateSerializer(data=data)
            if serializer.is_valid():
                serializer.save(tenant=profile.tenant, created_by=profile)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class ReportTemplateDetailView(APIView):
    """Get, update, delete report template"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def get(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            template = ReportTemplate.objects.get(
                id=pk,
                tenant=profile.tenant,
                is_active=True
            )
            # Check if user has access
            if not template.is_public and template.created_by != profile:
                return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = ReportTemplateSerializer(template)
            return Response(serializer.data)
        except ReportTemplate.DoesNotExist:
            return Response({'error': 'Report template not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def put(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            template = ReportTemplate.objects.get(id=pk, tenant=profile.tenant)
            
            # Check permissions
            if template.created_by != profile and profile.role.name not in ['admin', 'principal']:
                return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = ReportTemplateSerializer(template, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ReportTemplate.DoesNotExist:
            return Response({'error': 'Report template not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    @role_required('admin', 'principal', 'teacher')
    def delete(self, request, pk):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            template = ReportTemplate.objects.get(id=pk, tenant=profile.tenant)
            
            # Check permissions
            if template.created_by != profile and profile.role.name not in ['admin', 'principal']:
                return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
            
            template.is_active = False
            template.save()
            return Response({'message': 'Report template deleted.'}, status=status.HTTP_204_NO_CONTENT)
        except ReportTemplate.DoesNotExist:
            return Response({'error': 'Report template not found.'}, status=status.HTTP_404_NOT_FOUND)


# ============================================
# CUSTOM REPORT BUILDER - DATA GENERATION
# ============================================

class CustomReportBuilderView(APIView):
    """Generate custom reports based on drag-and-drop configuration"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            # Validate request data
            serializer = ReportDataSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            fields = data.get('fields', [])
            filters = data.get('filters', {})
            group_by = data.get('group_by', [])
            sort_by = data.get('sort_by', [])
            limit = data.get('limit', 1000)
            
            # Get report fields configuration
            report_fields = ReportField.objects.filter(
                tenant=tenant,
                field_key__in=fields,
                is_active=True
            )
            
            if not report_fields.exists():
                return Response({
                    'error': 'No valid report fields found.',
                    'details': f'Fields: {fields}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Build query based on data sources
            data_source = report_fields.first().data_source
            queryset = self._get_base_queryset(data_source, tenant, filters)
            
            # Apply grouping
            if group_by:
                queryset = self._apply_grouping(queryset, report_fields, group_by)
            
            # Apply sorting
            if sort_by:
                queryset = self._apply_sorting(queryset, sort_by)
            
            # Limit results
            queryset = queryset[:limit]
            
            # Extract data
            report_data = []
            for item in queryset:
                row = {}
                for field in report_fields:
                    field_key = field.field_key
                    if field.aggregate_type:
                        # For grouped/aggregated data
                        row[field_key] = self._get_aggregate_value(item, field)
                    else:
                        # For individual record data
                        row[field_key] = self._get_field_value(item, field)
                report_data.append(row)
            
            # Get field metadata for frontend
            field_metadata = []
            for field in report_fields:
                field_metadata.append({
                    'key': field.field_key,
                    'name': field.display_name or field.name,
                    'type': field.field_type,
                    'format': field.format_string
                })
            
            return Response({
                'data': report_data,
                'fields': field_metadata,
                'total': len(report_data),
                'grouped': len(group_by) > 0
            })
            
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error generating custom report: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate report: {str(e)}',
                'details': 'Check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_base_queryset(self, data_source, tenant, filters):
        """Get base queryset based on data source"""
        if data_source == 'ReportCard':
            queryset = ReportCard.objects.filter(tenant=tenant)
        elif data_source == 'MarksEntry':
            queryset = MarksEntry.objects.filter(tenant=tenant)
        elif data_source == 'Attendance':
            queryset = Attendance.objects.filter(tenant=tenant)
        elif data_source == 'Student':
            queryset = Student.objects.filter(tenant=tenant)
        elif data_source == 'FeePayment':
            queryset = FeePayment.objects.filter(tenant=tenant)
        else:
            queryset = ReportCard.objects.filter(tenant=tenant)  # Default
        
        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters, data_source)
        
        return queryset.select_related('student', 'class_obj', 'academic_year', 'term')
    
    def _apply_filters(self, queryset, filters, data_source):
        """Apply filters to queryset"""
        for key, value in filters.items():
            if value is None or value == '':
                continue
            
            # Handle common filter keys
            if key == 'academic_year_id' and hasattr(queryset.model, 'academic_year'):
                queryset = queryset.filter(academic_year_id=value)
            elif key == 'term_id' and hasattr(queryset.model, 'term'):
                queryset = queryset.filter(term_id=value)
            elif key == 'class_id' and hasattr(queryset.model, 'class_obj'):
                queryset = queryset.filter(class_obj_id=value)
            elif key == 'student_id' and hasattr(queryset.model, 'student'):
                queryset = queryset.filter(student_id=value)
            elif key == 'date_from' and hasattr(queryset.model, 'date'):
                queryset = queryset.filter(date__gte=value)
            elif key == 'date_to' and hasattr(queryset.model, 'date'):
                queryset = queryset.filter(date__lte=value)
            else:
                # Try direct field filter
                if hasattr(queryset.model, key):
                    queryset = queryset.filter(**{key: value})
        
        return queryset
    
    def _apply_grouping(self, queryset, report_fields, group_by):
        """Apply grouping and aggregation"""
        from django.db.models import Count, Sum, Avg, Max, Min
        
        # Build group by fields
        group_fields = []
        for field_name in group_by:
            if hasattr(queryset.model, field_name):
                group_fields.append(field_name)
        
        if not group_fields:
            return queryset
        
        # Build annotations for aggregate fields
        annotations = {}
        for field in report_fields:
            if field.aggregate_type:
                data_field = field.data_field
                if hasattr(queryset.model, data_field):
                    if field.aggregate_type == 'sum':
                        annotations[field.field_key] = Sum(data_field)
                    elif field.aggregate_type == 'avg':
                        annotations[field.field_key] = Avg(data_field)
                    elif field.aggregate_type == 'max':
                        annotations[field.field_key] = Max(data_field)
                    elif field.aggregate_type == 'min':
                        annotations[field.field_key] = Min(data_field)
                    elif field.aggregate_type == 'count':
                        annotations[field.field_key] = Count('id')
        
        # Apply grouping
        queryset = queryset.values(*group_fields)
        if annotations:
            queryset = queryset.annotate(**annotations)
        
        return queryset
    
    def _apply_sorting(self, queryset, sort_by):
        """Apply sorting"""
        order_fields = []
        for field_name in sort_by:
            if field_name.startswith('-'):
                order_fields.append(field_name)
            else:
                order_fields.append(field_name)
        
        if order_fields:
            queryset = queryset.order_by(*order_fields)
        
        return queryset
    
    def _get_field_value(self, item, field):
        """Get field value from item"""
        try:
            if hasattr(item, field.data_field):
                value = getattr(item, field.data_field)
                # Format value based on field type
                if field.format_string and value is not None:
                    try:
                        if field.field_type == 'percentage':
                            return f"{float(value):.2f}%"
                        elif field.field_type == 'number':
                            return float(value)
                        return value
                    except (ValueError, TypeError):
                        return value
                return value
            return None
        except Exception:
            return None
    
    def _get_aggregate_value(self, item, field):
        """Get aggregate value from grouped item"""
        field_key = field.field_key
        if hasattr(item, field_key):
            value = getattr(item, field_key)
            if field.format_string:
                try:
                    if field.field_type == 'percentage':
                        return f"{float(value):.2f}%"
                    return float(value)
                except (ValueError, TypeError):
                    return value
            return value
        return None


# ============================================
# COMPARATIVE ANALYSIS
# ============================================

class ComparativeAnalysisView(APIView):
    """Compare performance across classes, terms, academic years"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('education')]
    
    def post(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            # Get comparison parameters
            comparison_type = request.data.get('comparison_type', 'classes')  # classes, terms, academic_years
            metric = request.data.get('metric', 'percentage')  # percentage, total_marks, attendance, etc.
            filters = request.data.get('filters', {})
            
            # Get comparison groups
            if comparison_type == 'classes':
                groups = request.data.get('class_ids', [])
                if not groups:
                    # Get all classes if not specified
                    groups = list(Class.objects.filter(tenant=tenant).values_list('id', flat=True))
                
                comparison_data = self._compare_classes(tenant, groups, metric, filters)
                
            elif comparison_type == 'terms':
                groups = request.data.get('term_ids', [])
                academic_year_id = filters.get('academic_year_id')
                if not groups and academic_year_id:
                    groups = list(Term.objects.filter(
                        tenant=tenant,
                        academic_year_id=academic_year_id
                    ).values_list('id', flat=True))
                
                comparison_data = self._compare_terms(tenant, groups, metric, filters)
                
            elif comparison_type == 'academic_years':
                groups = request.data.get('academic_year_ids', [])
                if not groups:
                    groups = list(AcademicYear.objects.filter(tenant=tenant).values_list('id', flat=True))
                
                comparison_data = self._compare_academic_years(tenant, groups, metric, filters)
            else:
                return Response({
                    'error': 'Invalid comparison type.',
                    'details': 'Must be: classes, terms, or academic_years'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'comparison_type': comparison_type,
                'metric': metric,
                'data': comparison_data,
                'summary': self._generate_comparison_summary(comparison_data, metric)
            })
            
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error generating comparative analysis: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate comparison: {str(e)}',
                'details': 'Check server logs for more information.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _compare_classes(self, tenant, class_ids, metric, filters):
        """Compare performance across classes"""
        queryset = ReportCard.objects.filter(tenant=tenant, class_obj_id__in=class_ids)
        
        # Apply filters
        if filters.get('academic_year_id'):
            queryset = queryset.filter(academic_year_id=filters['academic_year_id'])
        if filters.get('term_id'):
            queryset = queryset.filter(term_id=filters['term_id'])
        
        # Aggregate by class
        if metric == 'percentage':
            results = queryset.values('class_obj__name', 'class_obj_id').annotate(
                avg_percentage=Avg('percentage'),
                max_percentage=Max('percentage'),
                min_percentage=Min('percentage'),
                student_count=Count('student', distinct=True)
            )
        elif metric == 'total_marks':
            results = queryset.values('class_obj__name', 'class_obj_id').annotate(
                avg_total_marks=Avg('total_marks'),
                max_total_marks=Max('total_marks'),
                min_total_marks=Min('total_marks'),
                student_count=Count('student', distinct=True)
            )
        elif metric == 'attendance':
            results = queryset.values('class_obj__name', 'class_obj_id').annotate(
                avg_attendance=Avg('attendance_percentage'),
                max_attendance=Max('attendance_percentage'),
                min_attendance=Min('attendance_percentage'),
                student_count=Count('student', distinct=True)
            )
        else:
            results = queryset.values('class_obj__name', 'class_obj_id').annotate(
                student_count=Count('student', distinct=True)
            )
        
        return list(results)
    
    def _compare_terms(self, tenant, term_ids, metric, filters):
        """Compare performance across terms"""
        queryset = ReportCard.objects.filter(tenant=tenant, term_id__in=term_ids)
        
        # Apply filters
        if filters.get('academic_year_id'):
            queryset = queryset.filter(academic_year_id=filters['academic_year_id'])
        if filters.get('class_id'):
            queryset = queryset.filter(class_obj_id=filters['class_id'])
        
        # Aggregate by term
        if metric == 'percentage':
            results = queryset.values('term__name', 'term_id', 'term__order').annotate(
                avg_percentage=Avg('percentage'),
                max_percentage=Max('percentage'),
                min_percentage=Min('percentage'),
                student_count=Count('student', distinct=True)
            ).order_by('term__order')
        elif metric == 'total_marks':
            results = queryset.values('term__name', 'term_id', 'term__order').annotate(
                avg_total_marks=Avg('total_marks'),
                max_total_marks=Max('total_marks'),
                min_total_marks=Min('total_marks'),
                student_count=Count('student', distinct=True)
            ).order_by('term__order')
        elif metric == 'attendance':
            results = queryset.values('term__name', 'term_id', 'term__order').annotate(
                avg_attendance=Avg('attendance_percentage'),
                max_attendance=Max('attendance_percentage'),
                min_attendance=Min('attendance_percentage'),
                student_count=Count('student', distinct=True)
            ).order_by('term__order')
        else:
            results = queryset.values('term__name', 'term_id', 'term__order').annotate(
                student_count=Count('student', distinct=True)
            ).order_by('term__order')
        
        return list(results)
    
    def _compare_academic_years(self, tenant, academic_year_ids, metric, filters):
        """Compare performance across academic years"""
        queryset = ReportCard.objects.filter(tenant=tenant, academic_year_id__in=academic_year_ids)
        
        # Apply filters
        if filters.get('class_id'):
            queryset = queryset.filter(class_obj_id=filters['class_id'])
        if filters.get('term_id'):
            queryset = queryset.filter(term_id=filters['term_id'])
        
        # Aggregate by academic year
        if metric == 'percentage':
            results = queryset.values('academic_year__name', 'academic_year_id').annotate(
                avg_percentage=Avg('percentage'),
                max_percentage=Max('percentage'),
                min_percentage=Min('percentage'),
                student_count=Count('student', distinct=True)
            )
        elif metric == 'total_marks':
            results = queryset.values('academic_year__name', 'academic_year_id').annotate(
                avg_total_marks=Avg('total_marks'),
                max_total_marks=Max('total_marks'),
                min_total_marks=Min('total_marks'),
                student_count=Count('student', distinct=True)
            )
        elif metric == 'attendance':
            results = queryset.values('academic_year__name', 'academic_year_id').annotate(
                avg_attendance=Avg('attendance_percentage'),
                max_attendance=Max('attendance_percentage'),
                min_attendance=Min('attendance_percentage'),
                student_count=Count('student', distinct=True)
            )
        else:
            results = queryset.values('academic_year__name', 'academic_year_id').annotate(
                student_count=Count('student', distinct=True)
            )
        
        return list(results)
    
    def _generate_comparison_summary(self, comparison_data, metric):
        """Generate summary statistics for comparison"""
        if not comparison_data:
            return {}
        
        # Extract values based on metric
        if metric == 'percentage':
            values = [item.get('avg_percentage', 0) for item in comparison_data if item.get('avg_percentage')]
        elif metric == 'total_marks':
            values = [item.get('avg_total_marks', 0) for item in comparison_data if item.get('avg_total_marks')]
        elif metric == 'attendance':
            values = [item.get('avg_attendance', 0) for item in comparison_data if item.get('avg_attendance')]
        else:
            values = []
        
        if not values:
            return {}
        
        return {
            'average': sum(values) / len(values) if values else 0,
            'maximum': max(values) if values else 0,
            'minimum': min(values) if values else 0,
            'total_groups': len(comparison_data)
        }
