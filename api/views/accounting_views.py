"""Accounting: expenses, and profit & loss / GST summaries built from every module's sales."""
import csv
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.http import HttpResponse
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.models import Expense, ExpenseCategory
from api.models.permissions import role_required

ZERO = Decimal('0')


def _profile(request):
    return request.user.userprofile


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name']

    def validate_name(self, name):
        name = name.strip()
        if ExpenseCategory.objects.filter(tenant=_profile(self.context['request']).tenant, name__iexact=name).exists():
            raise ValidationError('You already have a category with this name.')
        return name


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'category', 'category_name', 'date', 'vendor', 'description', 'amount', 'gst_amount',
                  'payment_method', 'invoice_number', 'created_at']

    def validate(self, data):
        request = self.context['request']
        cat = data.get('category')
        if cat and cat.tenant_id != _profile(request).tenant_id:
            raise ValidationError({'category': 'Unknown category.'})
        amount, gst = data.get('amount', getattr(self.instance, 'amount', ZERO)), data.get('gst_amount', getattr(self.instance, 'gst_amount', ZERO))
        if amount is not None and amount <= 0:
            raise ValidationError({'amount': 'The amount must be above zero.'})
        if gst is not None and (gst < 0 or gst > amount):
            raise ValidationError({'gst_amount': 'GST cannot be negative or more than the total amount.'})
        return data


class AdminOnly:
    """Accounting is for owners and administrators."""

    @staticmethod
    def check(request):
        role = getattr(_profile(request).role, 'name', '')
        return role in ('admin', 'principal', 'accountant')


class CategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    def get_queryset(self):
        return ExpenseCategory.objects.filter(tenant=_profile(self.request).tenant)

    def perform_create(self, serializer):
        if not AdminOnly.check(self.request):
            raise ValidationError('Only an administrator can add categories.')
        serializer.save(tenant=_profile(self.request).tenant)


class ExpenseListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        if not AdminOnly.check(self.request):
            return Expense.objects.none()
        qs = Expense.objects.filter(tenant=_profile(self.request).tenant).select_related('category')
        p = self.request.query_params
        if p.get('date_from'):
            qs = qs.filter(date__gte=p['date_from'])
        if p.get('date_to'):
            qs = qs.filter(date__lte=p['date_to'])
        if p.get('category'):
            qs = qs.filter(category_id=p['category'])
        return qs

    def perform_create(self, serializer):
        if not AdminOnly.check(self.request):
            raise ValidationError('Only an administrator can record expenses.')
        serializer.save(tenant=_profile(self.request).tenant, created_by=_profile(self.request))


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        if not AdminOnly.check(self.request):
            return Expense.objects.none()
        return Expense.objects.filter(tenant=_profile(self.request).tenant)


def _sum(qs, field):
    return qs.aggregate(t=Sum(field))['t'] or ZERO


def income_sources(tenant, start, end):
    """Sales per module in the period: list of {source, revenue, tax}. Revenue includes the GST charged."""
    out = []

    def add(label, revenue, tax):
        if revenue or tax:
            out.append({'source': label, 'revenue': revenue, 'tax': tax})

    from pharmacy.models import Sale as PSale
    from retail.models import Sale as RSale
    q = PSale.objects.filter(tenant=tenant, sale_date__date__range=(start, end), payment_status='PAID')
    add('Pharmacy sales', _sum(q, 'total_amount'), _sum(q, 'tax_amount'))
    q = RSale.objects.filter(tenant=tenant, sale_date__date__range=(start, end), payment_status='PAID')
    add('Retail sales', _sum(q, 'total_amount'), _sum(q, 'tax_amount'))
    from restaurant.models import Order
    q = Order.objects.filter(tenant=tenant, status='paid', created_at__date__range=(start, end))
    add('Restaurant orders', _sum(q, 'total_amount'), _sum(q, 'tax_amount'))
    from salon.models import Appointment
    q = Appointment.objects.filter(tenant=tenant, status='completed', start_time__date__range=(start, end))
    revenue = _sum(q, 'total_amount') or _sum(q, 'price')
    add('Salon services', revenue, _sum(q, 'tax_amount'))
    from hotel.models import Booking
    q = Booking.objects.filter(tenant=tenant, status='checked_out', check_out__date__range=(start, end))
    add('Hotel stays', _sum(q, 'total_amount'), _sum(q, 'tax_amount'))
    from manufacturing.models import SalesOrder
    q = SalesOrder.objects.filter(tenant=tenant, order_date__range=(start, end)).exclude(status__in=['DRAFT', 'CANCELLED'])
    add('Manufacturing sales', _sum(q, 'total_amount'), _sum(q, 'tax_amount'))
    from education.models import FeePayment
    q = FeePayment.objects.filter(tenant=tenant, payment_date__range=(start, end))
    add('School fees', _sum(q, 'amount_paid'), ZERO)
    return out


def _period(request):
    today = date.today()
    try:
        start = date.fromisoformat(request.query_params.get('date_from') or today.replace(day=1).isoformat())
        end = date.fromisoformat(request.query_params.get('date_to') or today.isoformat())
    except ValueError:
        raise ValidationError('Dates must look like 2026-04-01.')
    if end < start:
        raise ValidationError('The end date is before the start date.')
    return start, end


class ReportView(APIView):
    """?date_from=&date_to= -> profit and loss and GST summary. Add &export=csv to download."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not AdminOnly.check(request):
            return Response({'error': 'Only an administrator can see accounting reports.'}, status=status.HTTP_403_FORBIDDEN)
        tenant = _profile(request).tenant
        start, end = _period(request)
        income = income_sources(tenant, start, end)
        exp = Expense.objects.filter(tenant=tenant, date__range=(start, end))
        by_cat = [{'category': e['category__name'], 'amount': e['t']} for e in
                  exp.values('category__name').annotate(t=Sum('amount')).order_by('-t')]
        revenue = sum((i['revenue'] for i in income), ZERO)
        output_tax = sum((i['tax'] for i in income), ZERO)
        expenses = _sum(exp, 'amount')
        input_tax = _sum(exp, 'gst_amount')
        # Profit is worked out on amounts excluding GST: the tax collected is owed on, not earned.
        net_revenue = revenue - output_tax
        net_expenses = expenses - input_tax
        data = {
            'period': {'from': start, 'to': end},
            'income': income, 'expenses_by_category': by_cat,
            'totals': {'revenue': revenue, 'output_tax': output_tax, 'expenses': expenses, 'input_tax': input_tax,
                       'net_revenue': net_revenue, 'net_expenses': net_expenses, 'profit': net_revenue - net_expenses},
            'gst': {'collected': output_tax, 'paid_on_purchases': input_tax, 'payable': output_tax - input_tax},
        }
        if request.query_params.get('export') == 'csv':
            resp = HttpResponse(content_type='text/csv')
            resp['Content-Disposition'] = f'attachment; filename="report_{start}_{end}.csv"'
            w = csv.writer(resp)
            w.writerow(['Section', 'Item', 'Amount', 'GST'])
            for i in income:
                w.writerow(['Income', i['source'], i['revenue'], i['tax']])
            for e in by_cat:
                w.writerow(['Expense', e['category'], e['amount'], ''])
            t = data['totals']
            w.writerow(['Total', 'Revenue (incl. GST)', t['revenue'], t['output_tax']])
            w.writerow(['Total', 'Expenses (incl. GST)', t['expenses'], t['input_tax']])
            w.writerow(['Total', 'Profit (excl. GST)', t['profit'], ''])
            w.writerow(['GST', 'Payable (collected minus paid)', data['gst']['payable'], ''])
            return resp
        return Response(data)
