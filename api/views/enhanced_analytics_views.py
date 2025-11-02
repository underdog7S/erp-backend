"""
Enhanced Analytics Views
Provides cross-module analytics, time-series trends, comparisons, and forecasting
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from datetime import timedelta, datetime
from api.models.user import UserProfile
import calendar

# Import models from different modules
try:
    from education.models import Student, Class, FeePayment, Attendance, StaffAttendance
except ImportError:
    Student = Class = FeePayment = Attendance = StaffAttendance = None

try:
    from pharmacy.models import Sale as PharmacySale, Medicine, MedicineBatch, Customer as PharmacyCustomer
except ImportError:
    PharmacySale = Medicine = MedicineBatch = PharmacyCustomer = None

try:
    from retail.models import Sale as RetailSale, Product, Inventory, Customer as RetailCustomer
except ImportError:
    RetailSale = Product = Inventory = RetailCustomer = None

try:
    from hotel.models import Booking, Room
except ImportError:
    Booking = Room = None

try:
    from restaurant.models import Order
except ImportError:
    Order = None

try:
    from salon.models import Appointment
except ImportError:
    Appointment = None


class EnhancedDashboardAnalyticsView(APIView):
    """
    Cross-module enhanced analytics dashboard
    Aggregates data from all modules for comprehensive insights
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            today = timezone.now().date()
            month_start = today.replace(day=1)
            
            # Get tenant's industry to focus on relevant modules
            industry = tenant.industry.lower() if tenant.industry else None
            
            analytics = {
                'overview': {},
                'revenue': {},
                'transactions': {},
                'customers': {},
                'inventory': {},
                'trends': {},
                'module_specific': {}
            }
            
            # Overall revenue aggregation
            total_revenue = 0
            module_revenues = {}
            
            # Education module revenue (fees)
            if FeePayment:
                fee_revenue = FeePayment._default_manager.filter(
                    tenant=tenant
                ).aggregate(total=Sum('amount_paid'))['total'] or 0
                total_revenue += float(fee_revenue)
                module_revenues['education'] = float(fee_revenue)
            
            # Pharmacy module revenue
            if PharmacySale:
                pharmacy_revenue = PharmacySale.objects.filter(
                    tenant=tenant
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                total_revenue += float(pharmacy_revenue)
                module_revenues['pharmacy'] = float(pharmacy_revenue)
            
            # Retail module revenue
            if RetailSale:
                retail_revenue = RetailSale.objects.filter(
                    tenant=tenant
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                total_revenue += float(retail_revenue)
                module_revenues['retail'] = float(retail_revenue)
            
            # Hotel module revenue
            if Booking:
                hotel_revenue = Booking.objects.filter(
                    tenant=tenant,
                    status='completed'
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                total_revenue += float(hotel_revenue)
                module_revenues['hotel'] = float(hotel_revenue)
            
            # Restaurant module revenue
            if Order:
                restaurant_revenue = Order.objects.filter(
                    tenant=tenant,
                    status='completed'
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                total_revenue += float(restaurant_revenue)
                module_revenues['restaurant'] = float(restaurant_revenue)
            
            analytics['revenue'] = {
                'total_revenue': total_revenue,
                'by_module': module_revenues,
                'currency': 'INR'
            }
            
            # Overall transaction counts
            transaction_counts = {}
            
            if FeePayment:
                transaction_counts['education_payments'] = FeePayment._default_manager.filter(
                    tenant=tenant
                ).count()
            
            if PharmacySale:
                transaction_counts['pharmacy_sales'] = PharmacySale.objects.filter(
                    tenant=tenant
                ).count()
            
            if RetailSale:
                transaction_counts['retail_sales'] = RetailSale.objects.filter(
                    tenant=tenant
                ).count()
            
            if Booking:
                transaction_counts['hotel_bookings'] = Booking.objects.filter(
                    tenant=tenant
                ).count()
            
            if Order:
                transaction_counts['restaurant_orders'] = Order.objects.filter(
                    tenant=tenant
                ).count()
            
            analytics['transactions'] = {
                'total': sum(transaction_counts.values()),
                'by_module': transaction_counts
            }
            
            # Customer counts
            customer_counts = {}
            
            if Student:
                customer_counts['students'] = Student._default_manager.filter(
                    tenant=tenant, is_active=True
                ).count()
            
            if PharmacyCustomer:
                customer_counts['pharmacy_customers'] = PharmacyCustomer.objects.filter(
                    tenant=tenant
                ).count()
            
            if RetailCustomer:
                customer_counts['retail_customers'] = RetailCustomer.objects.filter(
                    tenant=tenant
                ).count()
            
            analytics['customers'] = {
                'total': sum(customer_counts.values()),
                'by_module': customer_counts
            }
            
            # Today's stats
            today_stats = {
                'revenue': 0,
                'transactions': 0
            }
            
            if FeePayment:
                today_fees = FeePayment._default_manager.filter(
                    tenant=tenant, payment_date=today
                ).aggregate(total=Sum('amount_paid'))['total'] or 0
                today_stats['revenue'] += float(today_fees)
                today_stats['transactions'] += FeePayment._default_manager.filter(
                    tenant=tenant, payment_date=today
                ).count()
            
            if PharmacySale:
                today_pharmacy = PharmacySale.objects.filter(
                    tenant=tenant, sale_date__date=today
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                today_stats['revenue'] += float(today_pharmacy)
                today_stats['transactions'] += PharmacySale.objects.filter(
                    tenant=tenant, sale_date__date=today
                ).count()
            
            if RetailSale:
                today_retail = RetailSale.objects.filter(
                    tenant=tenant, sale_date__date=today
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                today_stats['revenue'] += float(today_retail)
                today_stats['transactions'] += RetailSale.objects.filter(
                    tenant=tenant, sale_date__date=today
                ).count()
            
            analytics['overview'] = {
                'today': today_stats,
                'month_start': month_start.isoformat(),
                'industry': industry
            }
            
            # Module-specific stats based on industry
            if industry == 'education' and Student:
                analytics['module_specific']['education'] = {
                    'total_students': Student._default_manager.filter(tenant=tenant, is_active=True).count(),
                    'total_classes': Class.objects.filter(tenant=tenant).count() if Class else 0,
                    'total_teachers': UserProfile._default_manager.filter(
                        tenant=tenant, role__name='teacher'
                    ).count()
                }
            
            elif industry == 'pharmacy' and Medicine:
                analytics['module_specific']['pharmacy'] = {
                    'total_medicines': Medicine.objects.filter(tenant=tenant).count(),
                    'low_stock_count': MedicineBatch.objects.filter(
                        tenant=tenant, quantity_available__lte=10
                    ).count() if MedicineBatch else 0
                }
            
            elif industry == 'retail' and Product:
                analytics['module_specific']['retail'] = {
                    'total_products': Product.objects.filter(tenant=tenant).count(),
                    'low_stock_count': Inventory.objects.filter(
                        tenant=tenant, quantity_available__lte=10
                    ).count() if Inventory else 0
                }
            
            return Response(analytics)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TimeSeriesTrendsView(APIView):
    """
    Time-series trend analytics
    Returns daily, weekly, monthly trends for revenue and transactions
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            period = request.query_params.get('period', 'month')  # day, week, month, year
            days = int(request.query_params.get('days', 30))
            
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            trends = {
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'daily': [],
                'weekly': [],
                'monthly': []
            }
            
            # Daily trends
            daily_revenue = {}
            daily_transactions = {}
            
            current_date = start_date
            while current_date <= end_date:
                daily_revenue[current_date.isoformat()] = 0
                daily_transactions[current_date.isoformat()] = 0
                current_date += timedelta(days=1)
            
            # Education fees daily
            if FeePayment:
                fee_payments = FeePayment._default_manager.filter(
                    tenant=tenant,
                    payment_date__gte=start_date,
                    payment_date__lte=end_date
                ).values('payment_date').annotate(
                    revenue=Sum('amount_paid'),
                    count=Count('id')
                )
                
                for payment in fee_payments:
                    date_str = payment['payment_date'].isoformat()
                    if date_str in daily_revenue:
                        daily_revenue[date_str] += float(payment['revenue'] or 0)
                        daily_transactions[date_str] += payment['count']
            
            # Pharmacy sales daily
            if PharmacySale:
                pharmacy_sales = PharmacySale.objects.filter(
                    tenant=tenant,
                    sale_date__date__gte=start_date,
                    sale_date__date__lte=end_date
                ).annotate(date=TruncDate('sale_date')).values('date').annotate(
                    revenue=Sum('total_amount'),
                    count=Count('id')
                )
                
                for sale in pharmacy_sales:
                    date_str = sale['date'].isoformat()
                    if date_str in daily_revenue:
                        daily_revenue[date_str] += float(sale['revenue'] or 0)
                        daily_transactions[date_str] += sale['count']
            
            # Retail sales daily
            if RetailSale:
                retail_sales = RetailSale.objects.filter(
                    tenant=tenant,
                    sale_date__date__gte=start_date,
                    sale_date__date__lte=end_date
                ).annotate(date=TruncDate('sale_date')).values('date').annotate(
                    revenue=Sum('total_amount'),
                    count=Count('id')
                )
                
                for sale in retail_sales:
                    date_str = sale['date'].isoformat()
                    if date_str in daily_revenue:
                        daily_revenue[date_str] += float(sale['revenue'] or 0)
                        daily_transactions[date_str] += sale['count']
            
            # Format daily trends
            for date_str in sorted(daily_revenue.keys()):
                trends['daily'].append({
                    'date': date_str,
                    'revenue': daily_revenue[date_str],
                    'transactions': daily_transactions[date_str]
                })
            
            # Weekly trends (group by week)
            weekly_data = {}
            for day_data in trends['daily']:
                date_obj = datetime.fromisoformat(day_data['date']).date()
                week_start = date_obj - timedelta(days=date_obj.weekday())
                week_key = week_start.isoformat()
                
                if week_key not in weekly_data:
                    weekly_data[week_key] = {'revenue': 0, 'transactions': 0}
                
                weekly_data[week_key]['revenue'] += day_data['revenue']
                weekly_data[week_key]['transactions'] += day_data['transactions']
            
            for week_key in sorted(weekly_data.keys()):
                trends['weekly'].append({
                    'week_start': week_key,
                    'revenue': weekly_data[week_key]['revenue'],
                    'transactions': weekly_data[week_key]['transactions']
                })
            
            # Monthly trends
            monthly_data = {}
            for day_data in trends['daily']:
                date_obj = datetime.fromisoformat(day_data['date']).date()
                month_key = f"{date_obj.year}-{date_obj.month:02d}"
                
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'revenue': 0, 'transactions': 0}
                
                monthly_data[month_key]['revenue'] += day_data['revenue']
                monthly_data[month_key]['transactions'] += day_data['transactions']
            
            for month_key in sorted(monthly_data.keys()):
                trends['monthly'].append({
                    'month': month_key,
                    'revenue': monthly_data[month_key]['revenue'],
                    'transactions': monthly_data[month_key]['transactions']
                })
            
            return Response(trends)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ComparisonAnalyticsView(APIView):
    """
    Comparison analytics - This period vs previous period
    Compares current month vs last month, this week vs last week, etc.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            period = request.query_params.get('period', 'month')  # month, week, year
            
            today = timezone.now().date()
            
            comparisons = {
                'period': period,
                'current': {},
                'previous': {},
                'change': {}
            }
            
            # Determine date ranges based on period
            if period == 'month':
                current_start = today.replace(day=1)
                current_end = today
                
                # Previous month
                if today.month == 1:
                    previous_start = today.replace(year=today.year-1, month=12, day=1)
                    previous_end = (today.replace(day=1) - timedelta(days=1))
                else:
                    previous_start = today.replace(month=today.month-1, day=1)
                    previous_end = (today.replace(day=1) - timedelta(days=1))
            
            elif period == 'week':
                current_start = today - timedelta(days=today.weekday())
                current_end = today
                
                previous_start = current_start - timedelta(days=7)
                previous_end = current_start - timedelta(days=1)
            
            else:  # year
                current_start = today.replace(month=1, day=1)
                current_end = today
                
                previous_start = today.replace(year=today.year-1, month=1, day=1)
                previous_end = today.replace(year=today.year-1, month=12, day=31)
            
            # Calculate current period stats
            current_revenue = 0
            current_transactions = 0
            
            # Education
            if FeePayment:
                current_fees = FeePayment._default_manager.filter(
                    tenant=tenant,
                    payment_date__gte=current_start,
                    payment_date__lte=current_end
                ).aggregate(
                    revenue=Sum('amount_paid'),
                    count=Count('id')
                )
                current_revenue += float(current_fees['revenue'] or 0)
                current_transactions += current_fees['count'] or 0
            
            # Pharmacy
            if PharmacySale:
                current_pharmacy = PharmacySale.objects.filter(
                    tenant=tenant,
                    sale_date__date__gte=current_start,
                    sale_date__date__lte=current_end
                ).aggregate(
                    revenue=Sum('total_amount'),
                    count=Count('id')
                )
                current_revenue += float(current_pharmacy['revenue'] or 0)
                current_transactions += current_pharmacy['count'] or 0
            
            # Retail
            if RetailSale:
                current_retail = RetailSale.objects.filter(
                    tenant=tenant,
                    sale_date__date__gte=current_start,
                    sale_date__date__lte=current_end
                ).aggregate(
                    revenue=Sum('total_amount'),
                    count=Count('id')
                )
                current_revenue += float(current_retail['revenue'] or 0)
                current_transactions += current_retail['count'] or 0
            
            comparisons['current'] = {
                'revenue': current_revenue,
                'transactions': current_transactions,
                'start_date': current_start.isoformat(),
                'end_date': current_end.isoformat()
            }
            
            # Calculate previous period stats
            previous_revenue = 0
            previous_transactions = 0
            
            # Education
            if FeePayment:
                previous_fees = FeePayment._default_manager.filter(
                    tenant=tenant,
                    payment_date__gte=previous_start,
                    payment_date__lte=previous_end
                ).aggregate(
                    revenue=Sum('amount_paid'),
                    count=Count('id')
                )
                previous_revenue += float(previous_fees['revenue'] or 0)
                previous_transactions += previous_fees['count'] or 0
            
            # Pharmacy
            if PharmacySale:
                previous_pharmacy = PharmacySale.objects.filter(
                    tenant=tenant,
                    sale_date__date__gte=previous_start,
                    sale_date__date__lte=previous_end
                ).aggregate(
                    revenue=Sum('total_amount'),
                    count=Count('id')
                )
                previous_revenue += float(previous_pharmacy['revenue'] or 0)
                previous_transactions += previous_pharmacy['count'] or 0
            
            # Retail
            if RetailSale:
                previous_retail = RetailSale.objects.filter(
                    tenant=tenant,
                    sale_date__date__gte=previous_start,
                    sale_date__date__lte=previous_end
                ).aggregate(
                    revenue=Sum('total_amount'),
                    count=Count('id')
                )
                previous_revenue += float(previous_retail['revenue'] or 0)
                previous_transactions += previous_retail['count'] or 0
            
            comparisons['previous'] = {
                'revenue': previous_revenue,
                'transactions': previous_transactions,
                'start_date': previous_start.isoformat(),
                'end_date': previous_end.isoformat()
            }
            
            # Calculate change percentages
            revenue_change = 0
            transaction_change = 0
            
            if previous_revenue > 0:
                revenue_change = ((current_revenue - previous_revenue) / previous_revenue) * 100
            
            if previous_transactions > 0:
                transaction_change = ((current_transactions - previous_transactions) / previous_transactions) * 100
            
            comparisons['change'] = {
                'revenue_percentage': round(revenue_change, 2),
                'revenue_amount': round(current_revenue - previous_revenue, 2),
                'transactions_percentage': round(transaction_change, 2),
                'transactions_amount': current_transactions - previous_transactions,
                'is_increase': revenue_change > 0
            }
            
            return Response(comparisons)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RevenueForecastingView(APIView):
    """
    Revenue forecasting based on historical data
    Uses simple linear regression or moving average
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            forecast_days = int(request.query_params.get('days', 30))  # Forecast for next N days
            historical_days = int(request.query_params.get('historical_days', 90))  # Use last N days for calculation
            
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=historical_days)
            
            # Get historical daily revenue
            daily_revenue = {}
            current_date = start_date
            while current_date <= end_date:
                daily_revenue[current_date.isoformat()] = 0
                current_date += timedelta(days=1)
            
            # Collect historical data
            if FeePayment:
                fees = FeePayment._default_manager.filter(
                    tenant=tenant,
                    payment_date__gte=start_date,
                    payment_date__lte=end_date
                ).values('payment_date').annotate(
                    revenue=Sum('amount_paid')
                )
                
                for fee in fees:
                    date_str = fee['payment_date'].isoformat()
                    if date_str in daily_revenue:
                        daily_revenue[date_str] += float(fee['revenue'] or 0)
            
            if PharmacySale:
                sales = PharmacySale.objects.filter(
                    tenant=tenant,
                    sale_date__date__gte=start_date,
                    sale_date__date__lte=end_date
                ).annotate(date=TruncDate('sale_date')).values('date').annotate(
                    revenue=Sum('total_amount')
                )
                
                for sale in sales:
                    date_str = sale['date'].isoformat()
                    if date_str in daily_revenue:
                        daily_revenue[date_str] += float(sale['revenue'] or 0)
            
            if RetailSale:
                sales = RetailSale.objects.filter(
                    tenant=tenant,
                    sale_date__date__gte=start_date,
                    sale_date__date__lte=end_date
                ).annotate(date=TruncDate('sale_date')).values('date').annotate(
                    revenue=Sum('total_amount')
                )
                
                for sale in sales:
                    date_str = sale['date'].isoformat()
                    if date_str in daily_revenue:
                        daily_revenue[date_str] += float(sale['revenue'] or 0)
            
            # Calculate average daily revenue (simple forecasting)
            revenue_values = [v for v in daily_revenue.values() if v > 0]
            
            if not revenue_values:
                return Response({
                    'forecast': [],
                    'average_daily_revenue': 0,
                    'projected_total': 0,
                    'method': 'insufficient_data'
                })
            
            average_daily = sum(revenue_values) / len(revenue_values) if revenue_values else 0
            
            # Generate forecast
            forecast = []
            forecast_start = end_date + timedelta(days=1)
            
            for i in range(forecast_days):
                forecast_date = forecast_start + timedelta(days=i)
                forecast.append({
                    'date': forecast_date.isoformat(),
                    'projected_revenue': round(average_daily, 2)
                })
            
            # Additional forecasting methods could be added:
            # - Moving average (last 7 days, 30 days)
            # - Linear regression
            # - Seasonal adjustments
            
            return Response({
                'forecast': forecast,
                'average_daily_revenue': round(average_daily, 2),
                'projected_total': round(average_daily * forecast_days, 2),
                'historical_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': historical_days
                },
                'forecast_period': {
                    'start_date': forecast_start.isoformat(),
                    'end_date': (forecast_start + timedelta(days=forecast_days-1)).isoformat(),
                    'days': forecast_days
                },
                'method': 'simple_average'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

