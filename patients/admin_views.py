from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Patient, UltrasoundExam
from billing.models import Bill, ServiceType
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
import json

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
            bills = bills.filter(total_amount__gte=Decimal(min_amount))
        except ValueError:
            pass

    if max_amount:
        try:
            bills = bills.filter(total_amount__lte=Decimal(max_amount))
        except ValueError:
            pass

    # Calculate totals
    total_revenue = bills.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    pending_amount = bills.filter(status='PENDING').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    
    # Get other expenses from session or default to 0
    other_expenses = Decimal(str(request.session.get('other_expenses', '0')))
    
    # Calculate net revenue
    net_revenue = total_revenue - other_expenses

    context = {
        'bills': bills.order_by('-bill_date'),
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

@staff_member_required
@require_POST
def update_expenses(request):
    try:
        expenses = Decimal(str(request.POST.get('expenses', '0')))
        request.session['other_expenses'] = str(expenses)  # Store as string in session
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
        worksheet.write(row, 1, bill.patient.name)
        worksheet.write(row, 2, bill.bill_date.strftime('%Y-%m-%d'))
        worksheet.write(row, 3, float(bill.total_amount))
        worksheet.write(row, 4, bill.status)
        worksheet.write(row, 5, bill.payment_method or 'N/A')

    # Add summary at the bottom
    summary_row = len(bills) + 3
    total_revenue = bills.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
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

@staff_member_required
@require_POST
def add_expense(request):
    try:
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '0')
        date = request.POST.get('date', '')
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

@staff_member_required
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

@staff_member_required
def get_expenses(request):
    try:
        expenses = request.session.get('expenses', [])
        return JsonResponse({
            'success': True,
            'expenses': expenses
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error retrieving expenses: {str(e)}'})

@staff_member_required
def get_total_expenses(request):
    try:
        total_expenses = request.session.get('other_expenses', '0')
        return JsonResponse({
            'success': True,
            'total_expenses': total_expenses
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error retrieving total expenses: {str(e)}'})

@staff_member_required
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
    
    paginator = Paginator(patients.order_by('-created_at'), 25)  # 25 patients per page
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

@staff_member_required
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
    
    paginator = Paginator(exams.order_by('-exam_date'), 25)  # 25 exams per page
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

@staff_member_required
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

@staff_member_required
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

@staff_member_required
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