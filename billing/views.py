from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth.models import User
from .models import Bill, Payment, ServiceType, BillItem
from .forms import BillForm, PaymentForm
from patients.models import Patient, UltrasoundExam
from patients.utils import generate_username, generate_password

@login_required
def bill_list(request):
    bills = Bill.objects.all().order_by('-created_at').select_related(
        'patient'
    ).prefetch_related(
        'items',
        'items__service',
        'items__exam'
    )

    from django.core.paginator import Paginator
    paginator = Paginator(bills, 10)  # Show 10 bills per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'billing/bill_list.html', {
        'bills': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator
    })

@login_required
def bill_detail(request, bill_number):
    bill = get_object_or_404(Bill, bill_number=bill_number)
    bill_items = bill.items.all().select_related('exam', 'service')
    payments = bill.payments.all().order_by('-payment_date')
    total_paid = sum(payment.amount for payment in payments)
    total_change = bill.get_total_change_given()
    
    if request.method == 'POST':
        payment_form = PaymentForm(request.POST)
        if payment_form.is_valid():
            try:
                with transaction.atomic():
                    # Save the payment
                    payment = payment_form.save(commit=False)
                    payment.bill = bill
                    payment.created_by = request.user.get_full_name()
                    payment.save()

                    # Check if bill is fully paid
                    new_total_paid = total_paid + payment.amount
                    if new_total_paid >= bill.total_amount and not bill.patient.user:
                        # Create user account for patient
                        patient = bill.patient
                        username = generate_username(patient.first_name, patient.last_name)
                        password = generate_password()
                        
                        # Create user account
                        user = User.objects.create_user(
                            username=username,
                            email=patient.email if patient.email else None,
                            password=password,
                            first_name=patient.first_name,
                            last_name=patient.last_name
                        )
                        
                        # Link user to patient
                        patient.user = user
                        patient.save()
                        
                        # Store credentials in session for display in template
                        request.session['new_patient_username'] = username
                        request.session['new_patient_password'] = password

                        # Add success message
                        messages.success(
                            request,
                            'Payment recorded successfully. Patient portal account created!'
                        )
                    else:
                        # Check if there's change to be given
                        if payment.change > 0:
                            messages.success(
                                request, 
                                f'Payment recorded successfully. Change to be given: ₱{payment.change}'
                            )
                        else:
                            messages.success(request, 'Payment recorded successfully.')
                    
                    return redirect('billing:bill_detail', bill_number=bill.bill_number)
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
                return redirect('billing:bill_detail', bill_number=bill.bill_number)
    else:
        payment_form = PaymentForm(initial={'created_by': request.user.get_full_name()})
    
    # Get credentials from session if available
    new_patient_username = request.session.pop('new_patient_username', None)
    new_patient_password = request.session.pop('new_patient_password', None)

    context = {
        'bill': bill,
        'bill_items': bill_items,
        'payments': payments,
        'payment_form': payment_form,
        'total_paid': total_paid,
        'total_change': total_change,
        'new_patient_username': new_patient_username,
        'new_patient_password': new_patient_password,
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
        if not form.is_valid():
            # Add form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Error in {field}: {error}')
            return render(request, 'billing/create_bill.html', {
                'form': form,
                'patient': patient,
                'exams': exams,
                'exam_date': exam_date,
                'total_amount': total_amount,
                'procedure_count': exams.count()
            })
            
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
                print(f"DEBUG: Bill created with ID={bill.id}, bill_number={bill.bill_number}")  # Debug line
                
                # Create bill items for all unbilled exams on this date
                for exam in exams:
                    BillItem.objects.create(
                        bill=bill,
                        exam=exam,
                        service=exam.procedure_type,
                        amount=exam.procedure_type.base_price,
                        notes=None  # Explicitly set notes to None
                    )
                
                messages.success(request, f'Bill created successfully with {exams.count()} procedures.')
                print(f"DEBUG: Redirecting to bill_detail with bill_number={bill.bill_number}")  # Debug line
                response = redirect('billing:bill_detail', bill_number=bill.bill_number)
                print(f"DEBUG: Redirect URL = {response['Location']}")  # Debug line
                return response
        except Exception as e:
            messages.error(request, f'Error creating bill: {str(e)}')
            # Print the full error for debugging
            import traceback
            print(f"Error creating bill: {traceback.format_exc()}")
            return redirect('billing:create_bill', exam_id=exam_id)
    else:
        # Pre-fill form with default values
        initial = {
            'bill_date': timezone.now().date(),
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
