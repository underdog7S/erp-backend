import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q, Count
from datetime import datetime, timedelta, date
from api.models.user import UserProfile
from api.models.permissions import role_required
from django.utils import timezone

logger = logging.getLogger(__name__)

class EmployeeAnalyticsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @role_required('admin', 'principal')
    def get(self, request):
        try:
            # Get current user's tenant
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            
            # Get all employees in the tenant
            employees = UserProfile.objects.filter(tenant=tenant).select_related('user', 'role', 'department')
            
            today = date.today()
            next_30_days = today + timedelta(days=30)
            
            # Upcoming Birthdays (next 30 days)
            upcoming_birthdays = []
            birthdays_today = []
            
            for emp in employees:
                if emp.date_of_birth:
                    # Calculate next birthday this year
                    this_year_birthday = emp.date_of_birth.replace(year=today.year)
                    
                    # If birthday already passed this year, use next year
                    if this_year_birthday < today:
                        next_birthday = emp.date_of_birth.replace(year=today.year + 1)
                        days_until = (next_birthday - today).days
                    else:
                        next_birthday = this_year_birthday
                        days_until = (next_birthday - today).days
                    
                    # Calculate age
                    age = today.year - emp.date_of_birth.year - ((today.month, today.day) < (emp.date_of_birth.month, emp.date_of_birth.day))
                    
                    emp_data = {
                        'id': emp.id,
                        'name': f"{emp.user.first_name or ''} {emp.user.last_name or ''}".strip() or emp.user.username,
                        'username': emp.user.username,
                        'email': emp.user.email,
                        'date_of_birth': emp.date_of_birth.strftime('%Y-%m-%d'),
                        'next_birthday': next_birthday.strftime('%Y-%m-%d'),
                        'days_until': days_until,
                        'age': age,
                        'job_title': emp.job_title or 'N/A',
                        'department': emp.department.name if emp.department else 'No Department',
                        'role': emp.role.name if emp.role else 'No Role',
                        'photo': emp.photo.url if emp.photo else None
                    }
                    
                    if days_until == 0:
                        birthdays_today.append(emp_data)
                    elif days_until <= 30:
                        upcoming_birthdays.append(emp_data)
            
            # Sort by days until birthday
            upcoming_birthdays.sort(key=lambda x: x['days_until'])
            
            # Work Anniversaries (next 30 days)
            upcoming_anniversaries = []
            anniversaries_today = []
            
            for emp in employees:
                if emp.joining_date:
                    # Calculate next anniversary this year
                    this_year_anniversary = emp.joining_date.replace(year=today.year)
                    
                    # If anniversary already passed this year, use next year
                    if this_year_anniversary < today:
                        next_anniversary = emp.joining_date.replace(year=today.year + 1)
                        days_until = (next_anniversary - today).days
                        years_of_service = today.year - emp.joining_date.year
                    else:
                        next_anniversary = this_year_anniversary
                        days_until = (next_anniversary - today).days
                        years_of_service = today.year - emp.joining_date.year - 1
                    
                    emp_data = {
                        'id': emp.id,
                        'name': f"{emp.user.first_name or ''} {emp.user.last_name or ''}".strip() or emp.user.username,
                        'username': emp.user.username,
                        'email': emp.user.email,
                        'joining_date': emp.joining_date.strftime('%Y-%m-%d'),
                        'next_anniversary': next_anniversary.strftime('%Y-%m-%d'),
                        'days_until': days_until,
                        'years_of_service': years_of_service,
                        'job_title': emp.job_title or 'N/A',
                        'department': emp.department.name if emp.department else 'No Department',
                        'role': emp.role.name if emp.role else 'No Role',
                        'photo': emp.photo.url if emp.photo else None
                    }
                    
                    if days_until == 0:
                        anniversaries_today.append(emp_data)
                    elif days_until <= 30:
                        upcoming_anniversaries.append(emp_data)
            
            # Sort by days until anniversary
            upcoming_anniversaries.sort(key=lambda x: x['days_until'])
            
            # Employee Statistics
            total_employees = employees.count()
            active_employees = employees.filter(user__is_active=True).count()
            inactive_employees = total_employees - active_employees
            
            # Gender Distribution
            gender_dist = employees.values('gender').annotate(count=Count('id')).order_by('-count')
            gender_stats = {
                'Male': 0,
                'Female': 0,
                'Other': 0,
                'Not Specified': 0
            }
            for item in gender_dist:
                if item['gender'] in gender_stats:
                    gender_stats[item['gender']] = item['count']
                else:
                    gender_stats['Not Specified'] += item['count']
            
            # Role Distribution
            role_dist = employees.values('role__name').annotate(count=Count('id')).order_by('-count')
            role_stats = [{'role': item['role__name'] or 'No Role', 'count': item['count']} for item in role_dist]
            
            # Department Distribution
            dept_dist = employees.values('department__name').annotate(count=Count('id')).order_by('-count')
            department_stats = [{'department': item['department__name'] or 'No Department', 'count': item['count']} for item in dept_dist]
            
            # New Hires This Month
            first_day_of_month = today.replace(day=1)
            new_hires_this_month = employees.filter(
                joining_date__gte=first_day_of_month,
                joining_date__lte=today
            ).count()
            
            # Age Distribution
            age_groups = {
                '18-25': 0,
                '26-35': 0,
                '36-45': 0,
                '46-55': 0,
                '56+': 0
            }
            for emp in employees:
                if emp.date_of_birth:
                    age = today.year - emp.date_of_birth.year - ((today.month, today.day) < (emp.date_of_birth.month, emp.date_of_birth.day))
                    if 18 <= age <= 25:
                        age_groups['18-25'] += 1
                    elif 26 <= age <= 35:
                        age_groups['26-35'] += 1
                    elif 36 <= age <= 45:
                        age_groups['36-45'] += 1
                    elif 46 <= age <= 55:
                        age_groups['46-55'] += 1
                    elif age >= 56:
                        age_groups['56+'] += 1
            
            # Years of Service Distribution
            service_years = {
                'Less than 1 year': 0,
                '1-3 years': 0,
                '4-7 years': 0,
                '8-10 years': 0,
                'More than 10 years': 0
            }
            for emp in employees:
                if emp.joining_date:
                    years = today.year - emp.joining_date.year - ((today.month, today.day) < (emp.joining_date.month, emp.joining_date.day))
                    if years < 1:
                        service_years['Less than 1 year'] += 1
                    elif 1 <= years <= 3:
                        service_years['1-3 years'] += 1
                    elif 4 <= years <= 7:
                        service_years['4-7 years'] += 1
                    elif 8 <= years <= 10:
                        service_years['8-10 years'] += 1
                    else:
                        service_years['More than 10 years'] += 1
            
            # Employee Directory - All employee details for search
            employee_directory = []
            for emp in employees:
                age = None
                if emp.date_of_birth:
                    age = today.year - emp.date_of_birth.year - ((today.month, today.day) < (emp.date_of_birth.month, emp.date_of_birth.day))
                
                years_of_service = None
                if emp.joining_date:
                    years_of_service = today.year - emp.joining_date.year - ((today.month, today.day) < (emp.joining_date.month, emp.joining_date.day))
                
                emp_detail = {
                    'id': emp.id,
                    'username': emp.user.username,
                    'email': emp.user.email,
                    'first_name': emp.user.first_name or '',
                    'last_name': emp.user.last_name or '',
                    'full_name': f"{emp.user.first_name or ''} {emp.user.last_name or ''}".strip() or emp.user.username,
                    'phone': emp.phone or 'N/A',
                    'address': emp.address or 'N/A',
                    'date_of_birth': emp.date_of_birth.strftime('%Y-%m-%d') if emp.date_of_birth else None,
                    'age': age,
                    'gender': emp.gender or 'Not Specified',
                    'emergency_contact': emp.emergency_contact or 'N/A',
                    'job_title': emp.job_title or 'N/A',
                    'joining_date': emp.joining_date.strftime('%Y-%m-%d') if emp.joining_date else None,
                    'years_of_service': years_of_service,
                    'qualifications': emp.qualifications or 'N/A',
                    'bio': emp.bio or 'N/A',
                    'linkedin': emp.linkedin or 'N/A',
                    'department': emp.department.name if emp.department else 'No Department',
                    'role': emp.role.name if emp.role else 'No Role',
                    'is_active': emp.user.is_active if emp.user else False,
                    'photo': emp.photo.url if emp.photo else None
                }
                employee_directory.append(emp_detail)
            
            return Response({
                'upcoming_birthdays': upcoming_birthdays,
                'birthdays_today': birthdays_today,
                'upcoming_anniversaries': upcoming_anniversaries,
                'anniversaries_today': anniversaries_today,
                'statistics': {
                    'total_employees': total_employees,
                    'active_employees': active_employees,
                    'inactive_employees': inactive_employees,
                    'new_hires_this_month': new_hires_this_month
                },
                'gender_distribution': gender_stats,
                'role_distribution': role_stats,
                'department_distribution': department_stats,
                'age_distribution': age_groups,
                'service_years_distribution': service_years,
                'employee_directory': employee_directory
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"EmployeeAnalyticsView error: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

