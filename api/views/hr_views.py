"""Staff leave and payroll. Owners and administrators manage everything here."""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.models import Employee, LeaveRequest, Payslip

TWO = Decimal('0.01')


class IsHrAdmin(BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, 'userprofile', None)
        return bool(profile and getattr(profile.role, 'name', '') in ('admin', 'principal'))


def _tenant(request):
    return request.user.userprofile.tenant


def leave_balance(employee, year=None):
    year = year or date.today().year
    used = LeaveRequest.objects.filter(employee=employee, leave_type='PAID', status='approved', start_date__year=year).aggregate(t=Sum('days'))['t'] or 0
    return employee.paid_leave_per_year - used


class EmployeeSerializer(serializers.ModelSerializer):
    leave_balance = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['id', 'name', 'phone', 'email', 'designation', 'monthly_salary', 'join_date', 'paid_leave_per_year', 'is_active', 'leave_balance']

    def get_leave_balance(self, obj):
        return leave_balance(obj)

    def validate_monthly_salary(self, v):
        if v < 0:
            raise ValidationError('The salary cannot be negative.')
        return v


class LeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ['id', 'employee', 'employee_name', 'leave_type', 'start_date', 'end_date', 'days', 'reason', 'status', 'created_at']
        read_only_fields = ['days', 'status']

    def validate(self, data):
        if data['end_date'] < data['start_date']:
            raise ValidationError({'end_date': 'The end date is before the start date.'})
        if data['employee'].tenant_id != _tenant(self.context['request']).id:
            raise ValidationError({'employee': 'Unknown employee.'})
        return data


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model = Payslip
        fields = ['id', 'employee', 'employee_name', 'month', 'gross', 'unpaid_days', 'leave_deduction', 'other_deductions', 'bonus', 'net', 'status', 'paid_on']
        read_only_fields = fields


class EmployeeListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsHrAdmin]
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        return Employee.objects.filter(tenant=_tenant(self.request))

    def perform_create(self, serializer):
        serializer.save(tenant=_tenant(self.request))


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsHrAdmin]
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        return Employee.objects.filter(tenant=_tenant(self.request))


class LeaveListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsHrAdmin]
    serializer_class = LeaveSerializer

    def get_queryset(self):
        qs = LeaveRequest.objects.filter(tenant=_tenant(self.request)).select_related('employee')
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        return qs

    def perform_create(self, serializer):
        d = serializer.validated_data
        leave = serializer.save(tenant=_tenant(self.request), days=(d['end_date'] - d['start_date']).days + 1)
        from api.notify import notify
        notify(leave.tenant, f'Leave request: {leave.employee.name}', f'{leave.days} day(s) {leave.get_leave_type_display().lower()} from {leave.start_date}. Waiting for approval.',
               module='general', path='/hr', ref=('leave', leave.id), exclude=self.request.user)


class LeaveDecisionView(APIView):
    """POST {"decision": "approved" | "rejected"}. Paid leave cannot exceed the employee's balance for the year."""
    permission_classes = [IsAuthenticated, IsHrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        leave = LeaveRequest.objects.select_for_update().select_related('employee').filter(pk=pk, tenant=_tenant(request)).first()
        if not leave:
            return Response({'error': 'Leave request not found.'}, status=status.HTTP_404_NOT_FOUND)
        decision = request.data.get('decision')
        if decision not in ('approved', 'rejected'):
            return Response({'error': 'Decision must be approved or rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        if leave.status != 'pending':
            return Response({'error': f'This request is already {leave.status}.'}, status=status.HTTP_400_BAD_REQUEST)
        if decision == 'approved' and leave.leave_type == 'PAID':
            left = leave_balance(leave.employee, leave.start_date.year)
            if leave.days > left:
                return Response({'error': f'{leave.employee.name} has only {left} paid leave day(s) left this year. Approve it as unpaid leave instead.'},
                                status=status.HTTP_400_BAD_REQUEST)
        leave.status = decision
        leave.decided_by = request.user.userprofile
        leave.save(update_fields=['status', 'decided_by'])
        if leave.employee.user_id:
            from api.notify import notify
            notify(leave.tenant, f'Your leave was {decision}', f'{leave.days} day(s) from {leave.start_date}.', users=[leave.employee.user.user],
                   module='general', kind='success' if decision == 'approved' else 'info', path='/hr', ref=('leave_decision', leave.id))
        return Response({'status': leave.status})


def _unpaid_days_in_month(employee, first, last):
    days = 0
    for lv in LeaveRequest.objects.filter(employee=employee, leave_type='UNPAID', status='approved', start_date__lte=last, end_date__gte=first):
        days += (min(lv.end_date, last) - max(lv.start_date, first)).days + 1
    return days


class PayrollRunView(APIView):
    """POST {"month": "2026-09"}: create or refresh draft payslips for every active employee. Paid slips are left alone."""
    permission_classes = [IsAuthenticated, IsHrAdmin]

    @transaction.atomic
    def post(self, request):
        try:
            year, month = (int(x) for x in str(request.data.get('month', '')).split('-'))
            first = date(year, month, 1)
        except (ValueError, TypeError):
            return Response({'error': 'Month must look like 2026-09.'}, status=status.HTTP_400_BAD_REQUEST)
        last = date(year, month, calendar.monthrange(year, month)[1])
        for emp in Employee.objects.filter(tenant=_tenant(request), is_active=True):
            if emp.join_date and emp.join_date > last:
                continue
            slip, _ = Payslip.objects.get_or_create(tenant=_tenant(request), employee=emp, month=first)
            if slip.status == 'paid':
                continue
            unpaid = _unpaid_days_in_month(emp, first, last)
            deduction = (emp.monthly_salary / Decimal(last.day) * unpaid).quantize(TWO)
            slip.gross, slip.unpaid_days, slip.leave_deduction = emp.monthly_salary, unpaid, deduction
            slip.net = max(Decimal('0'), slip.gross - deduction - slip.other_deductions + slip.bonus)
            slip.save()
        slips = Payslip.objects.filter(tenant=_tenant(request), month=first).select_related('employee')
        return Response(PayslipSerializer(slips, many=True).data)


class PayslipListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsHrAdmin]
    serializer_class = PayslipSerializer

    def get_queryset(self):
        qs = Payslip.objects.filter(tenant=_tenant(self.request)).select_related('employee')
        if self.request.query_params.get('month'):
            qs = qs.filter(month=self.request.query_params['month'] + '-01')
        return qs


class PayslipAdjustView(APIView):
    """PATCH {"bonus", "other_deductions"} on a draft payslip."""
    permission_classes = [IsAuthenticated, IsHrAdmin]

    def patch(self, request, pk):
        slip = Payslip.objects.filter(pk=pk, tenant=_tenant(request)).first()
        if not slip:
            return Response({'error': 'Payslip not found.'}, status=status.HTTP_404_NOT_FOUND)
        if slip.status == 'paid':
            return Response({'error': 'A paid payslip cannot be changed.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            for f in ('bonus', 'other_deductions'):
                if f in request.data:
                    v = Decimal(str(request.data[f]))
                    if v < 0:
                        raise ValueError
                    setattr(slip, f, v)
        except (ValueError, ArithmeticError):
            return Response({'error': 'Amounts must be numbers of zero or more.'}, status=status.HTTP_400_BAD_REQUEST)
        slip.net = max(Decimal('0'), slip.gross - slip.leave_deduction - slip.other_deductions + slip.bonus)
        slip.save()
        return Response(PayslipSerializer(slip).data)


class PayslipPayView(APIView):
    """Mark a payslip paid and record the salary as an expense, so accounting stays in step."""
    permission_classes = [IsAuthenticated, IsHrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        slip = Payslip.objects.select_for_update().select_related('employee').filter(pk=pk, tenant=_tenant(request)).first()
        if not slip:
            return Response({'error': 'Payslip not found.'}, status=status.HTTP_404_NOT_FOUND)
        if slip.status == 'paid':
            return Response({'error': 'Already paid.'}, status=status.HTTP_400_BAD_REQUEST)
        slip.status, slip.paid_on = 'paid', date.today()
        slip.save(update_fields=['status', 'paid_on'])
        if slip.net > 0:
            from accounting.models import Expense, ExpenseCategory
            cat, _ = ExpenseCategory.objects.get_or_create(tenant=slip.tenant, name='Salaries')
            Expense.objects.create(tenant=slip.tenant, category=cat, date=slip.paid_on, vendor=slip.employee.name,
                                   description=f'Salary {slip.month:%b %Y}', amount=slip.net, payment_method='BANK',
                                   created_by=request.user.userprofile)
        return Response(PayslipSerializer(slip).data)
