from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Q, Subquery, OuterRef
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Patient, UltrasoundExam
from billing.models import Bill, ServiceType, Payment
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import StaffUserForm, StaffPasswordChangeForm, ServiceForm, StaffUserCreationForm
from .views import require_valid_navigation, custom_staff_member_required
import json


def get_analytics_context(start_date=None, end_date=None):
    """
    Helper function to generate analytics context data.
    When start_date/end_date are provided, most revenue and activity based
    aggregates are filtered to that range. Demographic summaries remain
    unfiltered (lifetime view).
    """
    today = timezone.now().date()

    # Weekly revenue (always current week, not affected by date filters)
    week_start = today - timedelta(days=today.weekday())
    weekly_bills = Bill.objects.filter(
        bill_date__gte=week_start,
        status__in=['PAID', 'PARTIAL']
    )
    weekly_total = weekly_bills.aggregate(Sum('total_amount'))['total_amount__sum']
    weekly_revenue = "{:,.2f}".format(weekly_total if weekly_total else 0)

    # Active patients in last 90 days
    ninety_days_ago = today - timedelta(days=90)
    active_patients_qs = UltrasoundExam.objects.filter(
        exam_date__gte=ninety_days_ago
    ).values('patient').distinct()
    active_patients_90d = active_patients_qs.count()

    # New patients this month
    month_start = today.replace(day=1)
    new_patients_month = Patient.objects.filter(created_at__date__gte=month_start).count()

    # Average procedures per patient (lifetime)
    distinct_patients_with_exam = UltrasoundExam.objects.values('patient').distinct().count()
    total_exams = UltrasoundExam.objects.count()
    avg_procs = (total_exams / distinct_patients_with_exam) if distinct_patients_with_exam else 0
    avg_procedures_per_patient = f"{avg_procs:.2f}"

    # Returning patient rate (last 6 months)
    six_months_ago = today - timedelta(days=180)
    recent_exam_counts = (
        UltrasoundExam.objects.filter(exam_date__gte=six_months_ago)
        .values('patient')
        .annotate(num=Count('id'))
    )
    num_recent_unique = recent_exam_counts.count()
    num_returning = sum(1 for r in recent_exam_counts if r['num'] >= 2)
    returning_rate = (num_returning / num_recent_unique * 100) if num_recent_unique else 0
    returning_rate_percent = f"{returning_rate:.1f}"

    # Date filters for analytics charts (applied where relevant)
    bill_date_filter = Q()
    exam_date_filter = Q()
    filter_start_date = start_date
    filter_end_date = end_date
    if filter_start_date:
        bill_date_filter &= Q(bill_date__gte=filter_start_date)
        exam_date_filter &= Q(exam_date__gte=filter_start_date)
    if filter_end_date:
        bill_date_filter &= Q(bill_date__lte=filter_end_date)
        exam_date_filter &= Q(exam_date__lte=filter_end_date)

    # Procedure distribution (respects date filter)
    procedures = UltrasoundExam.objects.filter(exam_date_filter).values('procedure_type__name').annotate(count=Count('id'))
    procedure_distribution_data = json.dumps([p['count'] for p in procedures])
    procedure_distribution_labels = json.dumps([p['procedure_type__name'] for p in procedures])

    # Findings distribution (recommendations, respects date filter)
    findings = UltrasoundExam.objects.filter(exam_date_filter).values('recommendations').annotate(count=Count('id'))
    recommendation_map = dict(UltrasoundExam.RECOMMENDATION_CHOICES)
    findings_distribution_data = json.dumps([f['count'] for f in findings])
    findings_distribution_labels = json.dumps([recommendation_map.get(f['recommendations'], f['recommendations']) for f in findings])

    # Monthly revenue (last 6 months, respects date filter when provided)
    monthly_revenue_dates = []
    monthly_revenue_values = []
    for i in range(6):
        month_date = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_start = month_date
        month_end = (month_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        month_total = (
            Bill.objects.filter(
                bill_date__gte=month_start,
                bill_date__lte=month_end,
                status__in=['PAID', 'PARTIAL']
            )
            .filter(bill_date_filter)
            .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        )
        monthly_revenue_dates.append(month_date.strftime('%Y-%m'))
        monthly_revenue_values.append(float(month_total))
    monthly_revenue_dates.reverse()
    monthly_revenue_values.reverse()
    monthly_revenue_dates = json.dumps(monthly_revenue_dates)
    monthly_revenue_values = json.dumps(monthly_revenue_values)

    # Daily procedures in selected range (or this week when no filter)
    if filter_start_date or filter_end_date:
        week_procedures_qs = UltrasoundExam.objects.filter(exam_date_filter)
    else:
        week_procedures_qs = UltrasoundExam.objects.filter(exam_date__gte=week_start)
    week_procedures = (
        week_procedures_qs
        .values('exam_date')
        .annotate(count=Count('id'))
        .order_by('exam_date')
    )
    week_procedures_dates = [entry['exam_date'].strftime('%Y-%m-%d') for entry in week_procedures]
    week_procedures_counts = [entry['count'] for entry in week_procedures]

    # Demographics
    gender_counts = Patient.objects.values('sex').annotate(count=Count('id'))
    gender_label_map = dict(Patient.GENDER_CHOICES)
    gender_distribution_labels = [gender_label_map.get(g['sex'], g['sex']) for g in gender_counts]
    gender_distribution_values = [g['count'] for g in gender_counts]

    type_counts = Patient.objects.values('patient_type').annotate(count=Count('id'))
    type_label_map = dict(Patient.PATIENT_TYPE_CHOICES)
    patient_type_labels = [type_label_map.get(t['patient_type'], t['patient_type']) for t in type_counts]
    patient_type_values = [t['count'] for t in type_counts]

    # Age buckets (computed in Python)
    age_buckets = {'0-17': 0, '18-29': 0, '30-44': 0, '45-59': 0, '60+': 0}
    for p in Patient.objects.exclude(birthday__isnull=True).only('birthday'):
        try:
            age = today.year - p.birthday.year - ((today.month, today.day) < (p.birthday.month, p.birthday.day))
            if age < 18:
                age_buckets['0-17'] += 1
            elif age < 30:
                age_buckets['18-29'] += 1
            elif age < 45:
                age_buckets['30-44'] += 1
            elif age < 60:
                age_buckets['45-59'] += 1
            else:
                age_buckets['60+'] += 1
        except Exception:
            continue
    age_bucket_labels = list(age_buckets.keys())
    age_bucket_values = list(age_buckets.values())

    # Top patients by revenue (respects date filter)
    top_revenue = (
        Bill.objects.filter(bill_date__gte=filter_start_date) if filter_start_date else Bill.objects
    )
    top_revenue = (
        top_revenue.filter(bill_date__lte=filter_end_date) if filter_end_date else top_revenue
    )
    top_revenue = (
        top_revenue.values('patient__first_name', 'patient__last_name')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')[:10]
    )
    top_patients_labels = [f"{t['patient__first_name']} {t['patient__last_name']}".strip() for t in top_revenue]
    top_patients_revenue = [float(t['total']) if t['total'] else 0 for t in top_revenue]

    # Revenue by Procedure Type (respects date filter)
    from billing.models import BillItem
    procedure_revenue = (
        BillItem.objects.filter(bill__status__in=['PAID', 'PARTIAL'])
        .filter(
            Q(bill__bill_date__gte=filter_start_date) if filter_start_date else Q(),
            Q(bill__bill_date__lte=filter_end_date) if filter_end_date else Q(),
        )
        .values('service__name')
        .annotate(total_revenue=Sum('amount'), procedure_count=Count('id'))
        .order_by('-total_revenue')
    )[:10]
    procedure_revenue_labels = [p['service__name'] for p in procedure_revenue]
    procedure_revenue_values = [float(p['total_revenue']) if p['total_revenue'] else 0 for p in procedure_revenue]
    procedure_revenue_counts = [p['procedure_count'] for p in procedure_revenue]

    # Revenue by Region (respects date filter)
    location_revenue = (
        Bill.objects.filter(status__in=['PAID', 'PARTIAL']).filter(bill_date_filter)
        .values('patient__region')
        .annotate(total_revenue=Sum('total_amount'), patient_count=Count('patient', distinct=True))
        .order_by('-total_revenue')
    )
    location_revenue_labels = [l['patient__region'] for l in location_revenue]
    location_revenue_values = [float(l['total_revenue']) if l['total_revenue'] else 0 for l in location_revenue]

    # Revenue by City (Top 10, respects date filter)
    city_revenue = (
        Bill.objects.filter(status__in=['PAID', 'PARTIAL']).filter(bill_date_filter)
        .values('patient__city')
        .annotate(total_revenue=Sum('total_amount'), patient_count=Count('patient', distinct=True))
        .order_by('-total_revenue')[:10]
    )
    city_revenue_labels = [c['patient__city'] for c in city_revenue]
    city_revenue_values = [float(c['total_revenue']) if c['total_revenue'] else 0 for c in city_revenue]

    # Revenue by Payment Method (respects date filter)
    payment_method_revenue = (
        Bill.objects.filter(status__in=['PAID', 'PARTIAL']).filter(bill_date_filter)
        .values('payments__payment_method')
        .annotate(total_revenue=Sum('total_amount'), payment_count=Count('payments'))
        .filter(payments__payment_method__isnull=False)
        .order_by('-total_revenue')
    )
    payment_method_labels = [p['payments__payment_method'] for p in payment_method_revenue]
    payment_method_values = [float(p['total_revenue']) if p['total_revenue'] else 0 for p in payment_method_revenue]

    # Revenue by Patient Type (respects date filter)
    patient_type_revenue = (
        Bill.objects.filter(status__in=['PAID', 'PARTIAL']).filter(bill_date_filter)
        .values('patient__patient_type')
        .annotate(total_revenue=Sum('total_amount'), patient_count=Count('patient', distinct=True))
        .order_by('-total_revenue')
    )
    patient_type_map = dict(Patient.PATIENT_TYPE_CHOICES)
    patient_type_revenue_labels = [patient_type_map.get(p['patient__patient_type'], p['patient__patient_type']) for p in patient_type_revenue]
    patient_type_revenue_values = [float(p['total_revenue']) if p['total_revenue'] else 0 for p in patient_type_revenue]

    # Monthly Revenue Trends (Last 12 months, respects date filter)
    monthly_trends = []
    for i in range(12):
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_revenue = (
            Bill.objects.filter(
                bill_date__year=month_date.year,
                bill_date__month=month_date.month,
                status__in=['PAID', 'PARTIAL']
            )
            .filter(bill_date_filter)
            .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        )
        monthly_trends.append({'month': month_date.strftime('%b %Y'), 'revenue': float(month_revenue)})
    monthly_trends.reverse()
    monthly_trend_labels = [m['month'] for m in monthly_trends]
    monthly_trend_values = [m['revenue'] for m in monthly_trends]

    # Summary insights for the selected period
    filtered_bills_qs = Bill.objects.filter(status__in=['PAID', 'PARTIAL']).filter(bill_date_filter)
    filtered_revenue_total_raw = filtered_bills_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    filtered_revenue_total = "{:,.2f}".format(filtered_revenue_total_raw)

    filtered_revenue_change_percent = None
    if filter_start_date and filter_end_date and filter_start_date <= filter_end_date:
        period_days = (filter_end_date - filter_start_date).days + 1
        if period_days > 0:
            prev_start = filter_start_date - timedelta(days=period_days)
            prev_end = filter_start_date - timedelta(days=1)
            previous_revenue = (
                Bill.objects.filter(
                    status__in=['PAID', 'PARTIAL'],
                    bill_date__gte=prev_start,
                    bill_date__lte=prev_end,
                )
                .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            )
            if previous_revenue:
                change = ((filtered_revenue_total_raw - previous_revenue) / previous_revenue) * 100
                filtered_revenue_change_percent = f"{change:.1f}"

    # Use already computed procedure_revenue / location_revenue for insights
    filtered_top_procedure_name = procedure_revenue_labels[0] if procedure_revenue_labels else None
    filtered_top_procedure_count = procedure_revenue_counts[0] if procedure_revenue_counts else 0
    filtered_top_region_label = location_revenue_labels[0] if location_revenue_labels else None
    filtered_top_region_revenue = (
        "{:,.2f}".format(location_revenue_values[0]) if location_revenue_values else "0.00"
    )

    has_filtered_data = bool(filtered_revenue_total_raw or week_procedures_counts or top_patients_revenue)

    return {
        'weekly_revenue': weekly_revenue,
        'active_patients_90d': active_patients_90d,
        'new_patients_month': new_patients_month,
        'avg_procedures_per_patient': avg_procedures_per_patient,
        'returning_rate_percent': returning_rate_percent,
        'procedure_distribution_data': procedure_distribution_data,
        'procedure_distribution_labels': procedure_distribution_labels,
        'findings_distribution_data': findings_distribution_data,
        'findings_distribution_labels': findings_distribution_labels,
        'monthly_revenue_dates': monthly_revenue_dates,
        'monthly_revenue_values': monthly_revenue_values,
        'week_procedures_dates': week_procedures_dates,
        'week_procedures_counts': week_procedures_counts,
        'gender_distribution_labels': gender_distribution_labels,
        'gender_distribution_values': gender_distribution_values,
        'patient_type_labels': patient_type_labels,
        'patient_type_values': patient_type_values,
        'age_bucket_labels': age_bucket_labels,
        'age_bucket_values': age_bucket_values,
        'top_patients_labels': top_patients_labels,
        'top_patients_revenue': top_patients_revenue,
        'procedure_revenue_labels': procedure_revenue_labels,
        'procedure_revenue_values': procedure_revenue_values,
        'procedure_revenue_counts': procedure_revenue_counts,
        'location_revenue_labels': location_revenue_labels,
        'location_revenue_values': location_revenue_values,
        'city_revenue_labels': city_revenue_labels,
        'city_revenue_values': city_revenue_values,
        'payment_method_labels': payment_method_labels,
        'payment_method_values': payment_method_values,
        'patient_type_revenue_labels': patient_type_revenue_labels,
        'patient_type_revenue_values': patient_type_revenue_values,
        'monthly_trend_labels': monthly_trend_labels,
        'monthly_trend_values': monthly_trend_values,
        'filter_start_date': filter_start_date,
        'filter_end_date': filter_end_date,
        'filtered_revenue_total': filtered_revenue_total,
        'filtered_revenue_change_percent': filtered_revenue_change_percent,
        'filtered_top_procedure_name': filtered_top_procedure_name,
        'filtered_top_procedure_count': filtered_top_procedure_count,
        'filtered_top_region_label': filtered_top_region_label,
        'filtered_top_region_revenue': filtered_top_region_revenue,
        'has_filtered_data': has_filtered_data,
    }

@custom_staff_member_required
@require_valid_navigation
def admin_add_user(request):
    """Admin view for adding a new staff user"""
    if request.method == 'POST':
        form = StaffUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully.')
            return redirect('admin_users')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffUserCreationForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'admin/add_user.html', context)

@custom_staff_member_required
def admin_analytics(request):
    # Read date filters from query string
    today = timezone.now().date()
    preset_param = request.GET.get('preset', '').strip()
    preset = preset_param or 'last_30'
    start_str = request.GET.get('start_date', '').strip()
    end_str = request.GET.get('end_date', '').strip()

    start_date = None
    end_date = None

    # Parse explicit dates if provided
    try:
        if start_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        if end_str:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        start_date = None
        end_date = None

    # If only one bound is provided, infer a reasonable other bound
    if start_date and not end_date:
        end_date = today
    elif end_date and not start_date:
        start_date = end_date - timedelta(days=29)

    # If no explicit dates, fall back to preset ranges
    if not start_date and not end_date:
        if preset == 'last_7':
            end_date = today
            start_date = today - timedelta(days=6)
        elif preset == 'last_30':
            end_date = today
            start_date = today - timedelta(days=29)
        elif preset == 'this_month':
            start_date = today.replace(day=1)
            end_date = today
        elif preset == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif preset == 'all':
            start_date = None
            end_date = None
        else:
            end_date = today
            start_date = today - timedelta(days=29)

    # Ensure start_date <= end_date
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    # Detect if user explicitly applied any filters (for UX messages)
    filters_applied = bool(start_str or end_str or preset_param)

    # Get analytics context with applied date filters
    analytics_context = get_analytics_context(start_date=start_date, end_date=end_date)
    analytics_context['filter_preset'] = preset
    analytics_context['filters_applied'] = filters_applied

    return render(request, 'admin/analytics.html', analytics_context)

@custom_staff_member_required
def admin_dashboard(request):
    # Get counts and recent data
    total_patients = Patient.objects.count()
    total_exams = UltrasoundExam.objects.count()
    total_revenue = Bill.objects.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    pending_bills = Bill.objects.filter(status='PENDING').count()

    # Billing status counts for chart
    paid_bills = Bill.objects.filter(status='PAID').count()
    partial_bills = Bill.objects.filter(status='PARTIAL').count()
    overdue_bills = Bill.objects.filter(status='PENDING').count()  # Assuming pending are overdue for simplicity

    # Get recent patients
    recent_patients = Patient.objects.all().order_by('-created_at')[:5]

    # Get recent bills
    recent_bills = Bill.objects.select_related('patient').order_by('-bill_date')[:5]

    # Get analytics context
    analytics_context = get_analytics_context()

    # Prepare chart data as JSON strings
    billing_data = json.dumps([paid_bills, partial_bills, overdue_bills])
    patient_data = json.dumps([analytics_context['new_patients_month'], analytics_context['active_patients_90d']])

    context = {
        'total_patients': total_patients,
        'total_exams': total_exams,
        'total_revenue': total_revenue,
        'pending_bills': pending_bills,
        'paid_bills': paid_bills,
        'partial_bills': partial_bills,
        'overdue_bills': overdue_bills,
        'billing_data': billing_data,
        'patient_data': patient_data,
        'recent_patients': recent_patients,
        'recent_bills': recent_bills,
    }
    context.update(analytics_context)

    return render(request, 'admin/dashboard.html', context)

@custom_staff_member_required
def admin_billing_report(request):
    from django.core.paginator import Paginator

    # Get filter parameters
    date_range = request.GET.get('date_range', '')
    status = request.GET.get('status', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')

    # Base queryset for totals (all bills)
    all_bills = Bill.objects.all()

    # Calculate totals (on all bills, not filtered)
    total_revenue = all_bills.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    pending_amount = all_bills.filter(status='PENDING').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')

    # Get other expenses from session or default to 0
    other_expenses = Decimal(str(request.session.get('other_expenses', '0')))

    # Calculate net revenue
    net_revenue = total_revenue - other_expenses

    # Base queryset for display (filtered)
    bills = Bill.objects.select_related('patient').prefetch_related('payments').all()

    # Apply filters
    if date_range:
        try:
            start_date, end_date = date_range.split(' - ')
            start_date = datetime.strptime(start_date, '%m/%d/%Y')
            end_date = datetime.strptime(end_date, '%m/%d/%Y')
            bills = bills.filter(bill_date__range=[start_date, end_date])
        except ValueError:
            pass

    if status:
        bills = bills.filter(status=status)

    if min_amount:
        try:
            bills = bills.filter(total_amount__gte=Decimal(min_amount))
        except ValueError:
            pass

    if max_amount:
        try:
            bills = bills.filter(total_amount__lte=Decimal(max_amount))
        except ValueError:
            pass

    # Pagination - 10 bills per page
    paginator = Paginator(bills.order_by('-bill_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'bills': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator,
        'total_revenue': total_revenue,
        'pending_amount': pending_amount,
        'other_expenses': other_expenses,
        'net_revenue': net_revenue,
        'status': status,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'today': timezone.now().date(),
    }

    return render(request, 'admin/billing_report.html', context)

@custom_staff_member_required
@require_POST
def update_expenses(request):
    try:
        expenses = Decimal(str(request.POST.get('expenses', '0')))
        request.session['other_expenses'] = str(expenses)  # Store as string in session
        return JsonResponse({'success': True})
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid expense value'})

@custom_staff_member_required
def admin_billing_export(request):
    from django.http import HttpResponse
    import xlsxwriter
    from io import BytesIO

    # Create an in-memory output file for the Excel workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Add headers
    headers = ['Bill ID', 'Patient Name', 'Date', 'Amount', 'Status', 'Payment Method']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Get filtered bills (reuse logic from admin_billing_report)
    date_range = request.GET.get('date_range', '')
    status = request.GET.get('status', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')

    bills = Bill.objects.select_related('patient').all()

    # Apply filters (same as in admin_billing_report)
    if date_range:
        try:
            start_date, end_date = date_range.split(' - ')
            start_date = datetime.strptime(start_date, '%m/%d/%Y')
            end_date = datetime.strptime(end_date, '%m/%d/%Y')
            bills = bills.filter(bill_date__range=[start_date, end_date])
        except ValueError:
            pass

    if status:
        bills = bills.filter(status=status)

    if min_amount:
        try:
            bills = bills.filter(total_amount__gte=Decimal(min_amount))
        except ValueError:
            pass

    if max_amount:
        try:
            bills = bills.filter(total_amount__lte=Decimal(max_amount))
        except ValueError:
            pass

    # Write data rows
    for row, bill in enumerate(bills, start=1):
        worksheet.write(row, 0, bill.id)
        worksheet.write(row, 1, f"{bill.patient.first_name} {bill.patient.last_name}")
        worksheet.write(row, 2, bill.bill_date.strftime('%Y-%m-%d'))
        worksheet.write(row, 3, float(bill.total_amount))
        worksheet.write(row, 4, bill.status)
        worksheet.write(row, 5, bill.payments.first().payment_method if bill.payments.exists() else 'N/A')

    # Add summary at the bottom
    summary_row = len(bills) + 3
    total_revenue = Bill.objects.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    other_expenses = Decimal(str(request.session.get('other_expenses', '0')))
    net_revenue = total_revenue - other_expenses

    # Add summary with bold format
    bold_format = workbook.add_format({'bold': True})
    worksheet.write(summary_row, 0, 'Summary', bold_format)
    worksheet.write(summary_row + 1, 0, 'Total Revenue:', bold_format)
    worksheet.write(summary_row + 1, 1, float(total_revenue))
    worksheet.write(summary_row + 2, 0, 'Other Expenses:', bold_format)
    worksheet.write(summary_row + 2, 1, float(other_expenses))
    worksheet.write(summary_row + 3, 0, 'Net Revenue:', bold_format)
    worksheet.write(summary_row + 3, 1, float(net_revenue))

    workbook.close()

    # Create the HttpResponse with Excel content type
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=billing_report.xlsx'

    return response

@custom_staff_member_required
@require_POST
def add_expense(request):
    try:
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '0')
        date = request.POST.get('date', '0')
        notes = request.POST.get('notes', '').strip()

        if not description:
            return JsonResponse({'success': False, 'error': 'Description is required'})
        
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid amount value'})
        
        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'Amount must be greater than 0'})

        if not date:
            date = timezone.now().date()
        else:
            try:
                date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date format'})

        # Store expense in session for now (simple approach)
        expenses = request.session.get('expenses', [])
        expense_id = len(expenses) + 1
        
        expense = {
            'id': expense_id,
            'description': description,
            'amount': str(amount),
            'date': date.strftime('%Y-%m-%d'),
            'notes': notes
        }
        
        expenses.append(expense)
        request.session['expenses'] = expenses
        
        # Update total expenses
        total_expenses = sum(Decimal(exp['amount']) for exp in expenses)
        request.session['other_expenses'] = str(total_expenses)

        return JsonResponse({
            'success': True,
            'expense': expense
        })
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': f'Invalid data: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error creating expense: {str(e)}'})

@custom_staff_member_required
@require_POST
def delete_expense(request):
    try:
        expense_id = request.POST.get('expense_id')
        if not expense_id:
            return JsonResponse({'success': False, 'error': 'Expense ID is required'})

        expenses = request.session.get('expenses', [])
        expenses = [exp for exp in expenses if str(exp['id']) != str(expense_id)]
        request.session['expenses'] = expenses
        
        # Update total expenses
        total_expenses = sum(Decimal(exp['amount']) for exp in expenses)
        request.session['other_expenses'] = str(total_expenses)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error deleting expense: {str(e)}'})

@custom_staff_member_required
def get_expenses(request):
    try:
        expenses = request.session.get('expenses', [])
        return JsonResponse({
            'success': True,
            'expenses': expenses
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error retrieving expenses: {str(e)}'})

@custom_staff_member_required
def get_total_expenses(request):
    try:
        total_expenses = request.session.get('other_expenses', '0')
        return JsonResponse({
            'success': True,
            'total_expenses': total_expenses
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error retrieving total expenses: {str(e)}'})

@custom_staff_member_required
def admin_patient_list(request):
    from django.core.paginator import Paginator
    
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Get all patients (including archived ones for admin)
    patients = Patient.objects.all()
    
    # Apply search filter if query is provided
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(contact_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(id_number__icontains=search_query)
        )
    
    # Calculate summary statistics
    total_patients = Patient.objects.count()
    archived_patients = Patient.objects.filter(is_archived=True).count()
    active_patients = Patient.objects.filter(is_archived=False).count()
    today_patients = Patient.objects.filter(created_at__date=timezone.now().date()).count()
    
    # Pagination - reset to page 1 if search is applied
    if search_query:
        page_number = 1  # Reset to first page when search is applied
    else:
        page_number = request.GET.get('page')
    
    paginator = Paginator(patients.order_by('-created_at'), 10)  # 10 patients per page
    page_obj = paginator.get_page(page_number)
    
    context = {
        'patients': page_obj,
        'search_query': search_query,
        'total_patients': total_patients,
        'archived_patients': archived_patients,
        'active_patients': active_patients,
        'today_patients': today_patients,
        'today': timezone.now().date(),
    }
    
    return render(request, 'admin/patient_list.html', context)

@custom_staff_member_required
def admin_prices(request):
    """Admin view for managing service prices"""
    services = ServiceType.objects.all().order_by('name')
    
    # Calculate statistics
    total_services = services.count()
    active_services = services.filter(is_active=True).count()
    
    if services.exists():
        prices = [service.base_price for service in services]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
    else:
        avg_price = 0
        min_price = 0
        max_price = 0
    
    context = {
        'services': services,
        'total_services': total_services,
        'active_services': active_services,
        'avg_price': avg_price,
        'min_price': min_price,
        'max_price': max_price,
    }
    
    return render(request, 'admin/prices.html', context)

@custom_staff_member_required
@require_POST
def update_service_price(request):
    """AJAX endpoint for updating individual service prices"""
    try:
        service_id = request.POST.get('service_id')
        new_price = request.POST.get('new_price')
        
        if not service_id or not new_price:
            return JsonResponse({'success': False, 'error': 'Service ID and price are required'})
        
        try:
            service = ServiceType.objects.get(id=service_id)
            service.base_price = Decimal(str(new_price))
            service.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Price updated successfully for {service.name}',
                'new_price': str(service.base_price)
            })
        except ServiceType.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Service not found'})
        except (ValueError, TypeError) as e:
            return JsonResponse({'success': False, 'error': f'Invalid price value: {str(e)}'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error updating price: {str(e)}'})

@custom_staff_member_required
@require_valid_navigation
def add_procedure(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Procedure added successfully.')
            return redirect('admin_prices')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ServiceForm()
    return render(request, 'admin/add_procedure_new.html', {'form': form})

@custom_staff_member_required
@require_valid_navigation
def edit_procedure(request, procedure_id):
    procedure = get_object_or_404(ServiceType, id=procedure_id)
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=procedure)
        if form.is_valid():
            form.save()
            messages.success(request, f'Procedure "{procedure.name}" updated successfully.')
            return redirect('admin_prices')
    else:
        form = ServiceForm(instance=procedure)
    return render(request, 'admin/edit_procedure.html', {'form': form, 'procedure': procedure})

@custom_staff_member_required
def admin_users(request):
    """Admin view for managing staff users"""
    # Get all staff users (is_staff=True)
    users = User.objects.filter(is_staff=True).order_by('username')
    
    # Calculate statistics
    total_staff = users.count()
    active_staff = users.filter(is_active=True).count()
    inactive_staff = users.filter(is_active=False).count()
    superusers = users.filter(is_superuser=True).count()
    
    context = {
        'users': users,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'inactive_staff': inactive_staff,
        'superusers': superusers,
    }
    
    return render(request, 'admin/users.html', context)

@custom_staff_member_required
@require_valid_navigation
def admin_edit_user(request, user_id):
    """Admin view for editing a staff user"""
    user = get_object_or_404(User, id=user_id, is_staff=True)
    
    if request.method == 'POST':
        form = StaffUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.username} updated successfully.')
            return redirect('admin_users')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffUserForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
    }
    
    return render(request, 'admin/edit_user.html', context)

@custom_staff_member_required
@require_valid_navigation
def admin_change_user_password(request, user_id):
    """Admin view for changing a staff user's password"""
    user = get_object_or_404(User, id=user_id, is_staff=True)
    
    if request.method == 'POST':
        form = StaffPasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Password for {user.username} changed successfully.')
            return redirect('admin_users')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffPasswordChangeForm(user)
    
    context = {
        'form': form,
        'user': user,
    }
    
    return render(request, 'admin/change_user_password.html', context)

@custom_staff_member_required
def admin_examinations(request):
    from django.core.paginator import Paginator
    
    # Get search query
    search_query = request.GET.get('search', '').strip()
    export = request.GET.get('export', '')

    # Get all exams
    exams = UltrasoundExam.objects.select_related('patient', 'procedure_type').all()

    # Apply search filter if query is provided
    if search_query:
        exams = exams.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(procedure_type__name__icontains=search_query) |
            Q(technician__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    # Calculate summary statistics (always show total counts, not filtered)
    all_exams = UltrasoundExam.objects.all()
    total_exams = all_exams.count()
    completed_exams = all_exams.filter(status='COMPLETED').count()
    pending_exams = all_exams.filter(status='PENDING').count()
    today_exams = all_exams.filter(exam_date=timezone.now().date()).count()

    # Handle export
    if export == 'excel':
        return admin_examinations_export(request, exams)

    # Pagination - reset to page 1 if search is applied
    if search_query:
        page_number = 1  # Reset to first page when search is applied
    else:
        page_number = request.GET.get('page')
    
    paginator = Paginator(exams.order_by('-exam_date'), 10)  # 10 exams per page
    page_obj = paginator.get_page(page_number)

    context = {
        'exams': page_obj,
        'search_query': search_query,
        'total_exams': total_exams,
        'completed_exams': completed_exams,
        'pending_exams': pending_exams,
        'today_exams': today_exams,
        'today': timezone.now().date(),
    }

    return render(request, 'admin/examinations.html', context)

@custom_staff_member_required
def admin_archive_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient.is_archived = True
    patient.archived_at = timezone.now()
    patient.save(update_fields=['is_archived', 'archived_at'])
    messages.success(request, 'Patient archived successfully.')
    return redirect('admin_patient_list')

@custom_staff_member_required
def admin_unarchive_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient.is_archived = False
    patient.archived_at = None
    patient.save(update_fields=['is_archived', 'archived_at'])
    messages.success(request, 'Patient restored from archive.')
    return redirect('admin_patient_list')

@custom_staff_member_required
def admin_examinations_export(request, exams_queryset):
    from django.http import HttpResponse
    import xlsxwriter
    from io import BytesIO

    # Create an in-memory output file for the Excel workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Add headers
    headers = ['Exam ID', 'Patient Name', 'Patient ID', 'Exam Type', 'Date', 'Status', 'Technician', 'Notes']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Write data rows
    for row, exam in enumerate(exams_queryset, start=1):
        worksheet.write(row, 0, exam.id)
        worksheet.write(row, 1, f"{exam.patient.first_name} {exam.patient.last_name}")
        worksheet.write(row, 2, exam.patient.id)
        worksheet.write(row, 3, exam.procedure_type.name if exam.procedure_type else 'N/A')
        worksheet.write(row, 4, exam.exam_date.strftime('%Y-%m-%d'))
        worksheet.write(row, 5, exam.status)
        worksheet.write(row, 6, exam.technician or 'N/A')
        worksheet.write(row, 7, exam.notes or '')

    # Add summary at the bottom
    summary_row = len(exams_queryset) + 3
    bold_format = workbook.add_format({'bold': True})
    worksheet.write(summary_row, 0, 'Summary', bold_format)
    worksheet.write(summary_row + 1, 0, 'Total Examinations:', bold_format)
    worksheet.write(summary_row + 1, 1, len(exams_queryset))
    worksheet.write(summary_row + 2, 0, 'Completed:', bold_format)
    worksheet.write(summary_row + 2, 1, exams_queryset.filter(status='COMPLETED').count())
    worksheet.write(summary_row + 3, 0, 'Pending:', bold_format)
    worksheet.write(summary_row + 3, 1, exams_queryset.filter(status='PENDING').count())

    workbook.close()

    # Create the HttpResponse with Excel content type
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=examinations_report.xlsx'

    return response