from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Bill, Payment, ServiceType
from .forms import BillForm, PaymentForm
from patients.models import Patient, UltrasoundExam

@login_required
def bill_list(request):
    bills = Bill.objects.all().order_by('-created_at')
    return render(request, 'billing/bill_list.html', {'bills': bills})

@login_required
def bill_detail(request, bill_number):
    bill = get_object_or_404(Bill, bill_number=bill_number)
    payments = bill.payments.all().order_by('-payment_date')
    total_paid = sum(payment.amount for payment in payments)
    remaining_balance = bill.total_amount - total_paid
    
    if request.method == 'POST':
        payment_form = PaymentForm(request.POST)
        if payment_form.is_valid():
            payment = payment_form.save(commit=False)
            payment.bill = bill
            payment.save()
            messages.success(request, 'Payment recorded successfully.')
            return redirect('billing:bill_detail', bill_number=bill.bill_number)
    else:
        payment_form = PaymentForm(initial={'created_by': request.user.get_full_name()})
    
    context = {
        'bill': bill,
        'payments': payments,
        'payment_form': payment_form,
        'total_paid': total_paid,
        'remaining_balance': remaining_balance,
    }
    return render(request, 'billing/bill_detail.html', context)

@login_required
def create_bill(request, exam_id):
    exam = get_object_or_404(UltrasoundExam, id=exam_id)
    
    if hasattr(exam, 'bill'):
        messages.warning(request, 'A bill already exists for this examination.')
        return redirect('bill_detail', bill_number=exam.bill.bill_number)
    
    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.patient = exam.patient
            bill.exam = exam
            bill.save()
            messages.success(request, 'Bill created successfully.')
            return redirect('billing:bill_detail', bill_number=bill.bill_number)
    else:
        # Pre-fill form with default service if available
        initial = {}
        default_service = ServiceType.objects.filter(is_active=True).first()
        if default_service:
            initial['service'] = default_service
            initial['subtotal'] = default_service.base_price
        
        form = BillForm(initial=initial)
    
    return render(request, 'billing/create_bill.html', {
        'form': form,
        'exam': exam,
        'patient': exam.patient
    })

@login_required
def patient_bills(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    bills = Bill.objects.filter(patient=patient).order_by('-created_at')
    return render(request, 'billing/patient_bills.html', {
        'patient': patient,
        'bills': bills
    })
