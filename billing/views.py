from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from .models import Bill, Payment, ServiceType, BillItem
from .forms import BillForm, PaymentForm
from patients.models import Patient, UltrasoundExam

@login_required
def bill_list(request):
    bills = Bill.objects.all().order_by('-created_at').select_related(
        'patient'
    ).prefetch_related(
        'items',
        'items__service',
        'items__exam'
    )
    return render(request, 'billing/bill_list.html', {'bills': bills})

@login_required
def bill_detail(request, bill_number):
    bill = get_object_or_404(Bill, bill_number=bill_number)
    bill_items = bill.items.all().select_related('exam', 'service')
    payments = bill.payments.all().order_by('-payment_date')
    total_paid = sum(payment.amount for payment in payments)
    remaining_balance = bill.total_amount - total_paid
    
    if request.method == 'POST':
        payment_form = PaymentForm(request.POST)
        if payment_form.is_valid():
            payment = payment_form.save(commit=False)
            payment.bill = bill
            payment.created_by = request.user.get_full_name()
            payment.save()
            messages.success(request, 'Payment recorded successfully.')
            return redirect('billing:bill_detail', bill_number=bill.bill_number)
    else:
        payment_form = PaymentForm(initial={'created_by': request.user.get_full_name()})
    
    context = {
        'bill': bill,
        'bill_items': bill_items,
        'payments': payments,
        'payment_form': payment_form,
        'total_paid': total_paid,
        'remaining_balance': remaining_balance,
    }
    return render(request, 'billing/bill_detail.html', context)

@login_required
def create_bill(request, exam_id):
    # Get the initial exam and check if it's already billed
    exam = get_object_or_404(UltrasoundExam, id=exam_id)
    if hasattr(exam, 'bill_item'):
        messages.info(request, 'This procedure is already billed.')
        return redirect('billing:bill_detail', bill_number=exam.bill_item.bill.bill_number)

    patient = exam.patient
    exam_date = exam.exam_date
    
    # Get ALL unbilled exams for the patient on the same date
    exams = UltrasoundExam.objects.filter(
        patient=patient,
        exam_date=exam_date,
        bill_item__isnull=True  # Only get unbilled exams
    ).order_by('exam_time')  # Order by time of procedure
    
    if not exams.exists():
        messages.warning(request, 'No unbilled procedures found for this date.')
        return redirect('patients:patient_detail', patient_id=patient.id)
    
    # Calculate total amount from all procedures
    total_amount = sum(exam.procedure_type.base_price for exam in exams)
    
    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the bill
                    bill = form.save(commit=False)
                    bill.patient = patient
                    bill.bill_date = timezone.now().date()
                    bill.subtotal = total_amount
                    
                    # Calculate final amount with discount and tax
                    discount = form.cleaned_data.get('discount', 0)
                    tax = form.cleaned_data.get('tax', 0)
                    bill.total_amount = total_amount - discount + tax
                    
                    bill.save()
                    
                    # Create bill items for all unbilled exams on this date
                    for exam in exams:
                        BillItem.objects.create(
                            bill=bill,
                            exam=exam,
                            service=exam.procedure_type,
                            amount=exam.procedure_type.base_price
                        )
                    
                    messages.success(request, f'Bill created successfully with {exams.count()} procedures.')
                    return redirect('billing:bill_detail', bill_number=bill.bill_number)
            except Exception as e:
                messages.error(request, f'Error creating bill: {str(e)}')
                return redirect('billing:create_bill', exam_id=exam_id)
    else:
        # Pre-fill form with default values
        initial = {
            'bill_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=30),
            'discount': 0,
            'tax': 0
        }
        form = BillForm(initial=initial)
    
    context = {
        'form': form,
        'patient': patient,
        'exams': exams,
        'exam_date': exam_date,
        'total_amount': total_amount,
        'procedure_count': exams.count()
    }
    
    return render(request, 'billing/create_bill.html', context)

@login_required
def patient_bills(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    bills = Bill.objects.filter(patient=patient).order_by('-created_at')
    return render(request, 'billing/patient_bills.html', {
        'patient': patient,
        'bills': bills
    })

@login_required
def cancel_bill(request, bill_number):
    bill = get_object_or_404(Bill, bill_number=bill_number)
    
    if request.method == 'POST':
        if bill.status not in ['PENDING', 'PARTIAL']:
            messages.error(request, 'Only pending or partially paid bills can be cancelled.')
        elif bill.payments.exists():
            messages.error(request, 'Cannot cancel a bill that has payments. Please refund payments first.')
        else:
            bill.status = 'CANCELLED'
            bill.save()
            messages.success(request, 'Bill cancelled successfully.')
    
    return redirect('billing:bill_detail', bill_number=bill.bill_number)
