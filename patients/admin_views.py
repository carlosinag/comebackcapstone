from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Patient, UltrasoundExam
from billing.models import Bill
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@staff_member_required
def admin_dashboard(request):
    # Get counts and recent data
    total_patients = Patient.objects.count()
    total_exams = UltrasoundExam.objects.count()
    total_revenue = Bill.objects.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    pending_bills = Bill.objects.filter(status='PENDING').count()

    # Get recent patients
    recent_patients = Patient.objects.all().order_by('-created_at')[:5]
    
    # Get recent bills
    recent_bills = Bill.objects.select_related('patient').order_by('-bill_date')[:5]

    context = {
        'total_patients': total_patients,
        'total_exams': total_exams,
        'total_revenue': total_revenue,
        'pending_bills': pending_bills,
        'recent_patients': recent_patients,
        'recent_bills': recent_bills,
    }

    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def admin_billing_report(request):
    # Get filter parameters
    date_range = request.GET.get('date_range', '')
    status = request.GET.get('status', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')

    # Base queryset
    bills = Bill.objects.select_related('patient').all()

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
            bills = bills.filter(total_amount__gte=float(min_amount))
        except ValueError:
            pass

    if max_amount:
        try:
            bills = bills.filter(total_amount__lte=float(max_amount))
        except ValueError:
            pass

    # Calculate totals
    total_revenue = bills.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    pending_amount = bills.filter(status='PENDING').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Get other expenses from session or default to 0
    other_expenses = request.session.get('other_expenses', 0)
    
    # Calculate net revenue
    net_revenue = total_revenue - float(other_expenses)

    context = {
        'bills': bills.order_by('-bill_date'),
        'total_revenue': total_revenue,
        'pending_amount': pending_amount,
        'other_expenses': other_expenses,
        'net_revenue': net_revenue,
        'status': status,
        'min_amount': min_amount,
        'max_amount': max_amount,
    }

    return render(request, 'admin/billing_report.html', context)

@staff_member_required
@require_POST
def update_expenses(request):
    try:
        expenses = float(request.POST.get('expenses', 0))
        request.session['other_expenses'] = expenses
        return JsonResponse({'success': True})
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid expense value'})

@staff_member_required
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
            bills = bills.filter(total_amount__gte=float(min_amount))
        except ValueError:
            pass

    if max_amount:
        try:
            bills = bills.filter(total_amount__lte=float(max_amount))
        except ValueError:
            pass

    # Write data rows
    for row, bill in enumerate(bills, start=1):
        worksheet.write(row, 0, bill.id)
        worksheet.write(row, 1, bill.patient.name)
        worksheet.write(row, 2, bill.bill_date.strftime('%Y-%m-%d'))
        worksheet.write(row, 3, float(bill.total_amount))
        worksheet.write(row, 4, bill.status)
        worksheet.write(row, 5, bill.payment_method or 'N/A')

    # Add summary at the bottom
    summary_row = len(bills) + 3
    total_revenue = bills.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    other_expenses = float(request.session.get('other_expenses', 0))
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