from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.db import models
from .models import Patient, UltrasoundExam
from .forms import PatientForm, UltrasoundExamForm
from django.db.models import Count, Sum
from django.db.models.functions import ExtractWeek
from django.utils import timezone
from datetime import timedelta
from billing.models import Bill
from django.contrib.auth import authenticate, login
from django.contrib.admin.views.decorators import staff_member_required

class PatientListView(ListView):
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Handle search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search_query) |
                models.Q(last_name__icontains=search_query)
            )
        
        # Handle sex filtering
        sex_filter = self.request.GET.get('sex_filter')
        if sex_filter in ['M', 'F']:
            queryset = queryset.filter(sex=sex_filter)
        
        # Handle sorting
        sort = self.request.GET.get('sort')
        if sort:
            if sort == 'age_asc':
                queryset = queryset.order_by('age')
            elif sort == 'age_desc':
                queryset = queryset.order_by('-age')
            elif sort == 'visit_asc':
                queryset = queryset.annotate(
                    last_visit=models.Max('ultrasound_exams__exam_date')
                ).order_by('last_visit')
            elif sort == 'visit_desc':
                queryset = queryset.annotate(
                    last_visit=models.Max('ultrasound_exams__exam_date')
                ).order_by('-last_visit')
        
        return queryset

class PatientDetailView(DetailView):
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exams'] = self.object.ultrasound_exams.all().order_by('-exam_date', '-exam_time')
        return context

class PatientCreateView(CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'
    success_url = reverse_lazy('patient-list')

    def form_valid(self, form):
        messages.success(self.request, 'Patient record created successfully.')
        return super().form_valid(form)

class PatientUpdateView(UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'
    
    def get_success_url(self):
        return reverse_lazy('patient-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Patient record updated successfully.')
        return super().form_valid(form)

class UltrasoundExamCreateView(CreateView):
    model = UltrasoundExam
    form_class = UltrasoundExamForm
    template_name = 'patients/ultrasound_form.html'

    def get_initial(self):
        initial = super().get_initial()
        if 'patient_id' in self.kwargs:
            initial['patient'] = get_object_or_404(Patient, pk=self.kwargs['patient_id'])
        return initial

    def get_success_url(self):
        return reverse_lazy('patient-detail', kwargs={'pk': self.object.patient.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Ultrasound examination record created successfully.')
        return super().form_valid(form)

class UltrasoundExamUpdateView(UpdateView):
    model = UltrasoundExam
    form_class = UltrasoundExamForm
    template_name = 'patients/ultrasound_form.html'

    def get_success_url(self):
        return reverse_lazy('patient-detail', kwargs={'pk': self.object.patient.pk})

    def form_valid(self, form):
        # If a new image is uploaded, delete the old one
        if 'image' in form.changed_data and self.object.image:
            self.object.image.delete(save=False)
        
        messages.success(self.request, 'Ultrasound examination record updated successfully.')
        return super().form_valid(form)

class UltrasoundExamDetailView(DetailView):
    model = UltrasoundExam
    template_name = 'patients/ultrasound_detail.html'
    context_object_name = 'exam'

class ImageAnnotationView(DetailView):
    model = Patient
    template_name = 'patients/image_annotation.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exams'] = self.object.ultrasound_exams.all().order_by('-exam_date', '-exam_time')
        return context 

@require_http_methods(["POST"])
def exam_image_upload(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    exam_id = request.POST.get('exam_id')
    image_file = request.FILES.get('image')
    
    if not exam_id or not image_file:
        messages.error(request, 'Both examination and image are required.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    try:
        exam = UltrasoundExam.objects.get(id=exam_id, patient=patient)
        
        # Delete old image if it exists
        if exam.image:
            exam.image.delete(save=False)
        
        exam.image = image_file
        exam.save()
        
        messages.success(request, 'Image uploaded successfully.')
    except UltrasoundExam.DoesNotExist:
        messages.error(request, 'Invalid examination selected.')
    except Exception as e:
        messages.error(request, f'Error uploading image: {str(e)}')
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def dashboard(request):
    # Initialize context with default values
    context = {
        'total_patients': 0,
        'total_procedures': 0,
        'weekly_revenue': "0.00",
        'procedure_distribution_data': [],
        'procedure_distribution_labels': [],
        'findings_distribution_data': [],
        'findings_distribution_labels': [],
        'monthly_revenue_dates': [],
        'monthly_revenue_values': [],
        'week_procedures_dates': [],
        'week_procedures_counts': [],
    }

    try:
        # Check if we need to create test data
        if Patient.objects.count() == 0:
            print("No patients found. Creating test data...")
            try:
                # Create test patient
                test_patient = Patient.objects.create(
                    first_name="Test",
                    last_name="Patient",
                    age=30,
                    sex='M',
                    date_of_birth="1993-01-01",
                    address="Test Address",
                    contact_number="1234567890"
                )
                print(f"Created test patient: {test_patient.first_name} {test_patient.last_name}")

                # Create test ultrasound exam
                today = timezone.now().date()
                UltrasoundExam.objects.create(
                    patient=test_patient,
                    referring_physician="Dr. Test",
                    clinical_diagnosis="Test Diagnosis",
                    medical_history="Test History",
                    procedure_type="ABD",
                    exam_date=today,
                    exam_time=timezone.now().time(),
                    technologist="Test Tech",
                    radiologist="Test Radiologist",
                    findings="Test Findings",
                    impression="Test Impression",
                    recommendations="NF",
                    technologist_signature="Test Tech",
                    radiologist_signature="Test Radiologist"
                )
                print("Created test ultrasound exam")

                # Create test bill
                Bill.objects.create(
                    patient=test_patient,
                    bill_date=today,
                    total_amount=1000.00,
                    status='PAID'
                )
                print("Created test bill")
            except Exception as e:
                print(f"Error creating test data: {str(e)}")

        # Debug: Print all patients
        print("Fetching all patients...")
        patients = Patient.objects.all()
        for patient in patients:
            print(f"Found patient: {patient.first_name} {patient.last_name} (ID: {patient.id})")
        
        # Basic counts with debug info
        total_patients = Patient.objects.count()
        print(f"Total patients count: {total_patients}")
        context['total_patients'] = total_patients

        total_procedures = UltrasoundExam.objects.count()
        print(f"Total procedures count: {total_procedures}")
        context['total_procedures'] = total_procedures

        # Weekly revenue with debug info
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        print(f"Calculating revenue from {week_start} to {today}")
        
        weekly_bills = Bill.objects.filter(
            bill_date__gte=week_start,
            status__in=['PAID', 'PARTIAL']
        )
        print(f"Found {weekly_bills.count()} bills for this week")
        
        weekly_total = weekly_bills.aggregate(Sum('total_amount'))['total_amount__sum']
        print(f"Weekly total: {weekly_total}")
        context['weekly_revenue'] = "{:,.2f}".format(weekly_total if weekly_total else 0)

        # Procedure Distribution with debug info
        print("Calculating procedure distribution...")
        procedures = UltrasoundExam.objects.values('procedure_type').annotate(count=Count('id'))
        print(f"Found {len(procedures)} different procedure types")
        context['procedure_distribution_data'] = [p['count'] for p in procedures]
        context['procedure_distribution_labels'] = [dict(UltrasoundExam.PROCEDURE_CHOICES)[p['procedure_type']] for p in procedures]

        # Findings Distribution with debug info
        print("Calculating findings distribution...")
        findings = UltrasoundExam.objects.values('recommendations').annotate(count=Count('id'))
        print(f"Found {len(findings)} different recommendation types")
        context['findings_distribution_data'] = [f['count'] for f in findings]
        context['findings_distribution_labels'] = [dict(UltrasoundExam.RECOMMENDATION_CHOICES)[f['recommendations']] for f in findings]

        # Monthly Revenue with debug info
        print("Calculating monthly revenue...")
        six_months_ago = today - timedelta(days=180)
        monthly_revenue = Bill.objects.filter(
            bill_date__gte=six_months_ago,
            status__in=['PAID', 'PARTIAL']
        ).values('bill_date').annotate(total=Sum('total_amount')).order_by('bill_date')
        print(f"Found revenue data for {len(monthly_revenue)} months")
        
        context['monthly_revenue_dates'] = [entry['bill_date'].strftime('%Y-%m-%d') for entry in monthly_revenue]
        context['monthly_revenue_values'] = [float(entry['total']) for entry in monthly_revenue]

        # Weekly Procedures with debug info
        print("Calculating weekly procedures...")
        week_procedures = UltrasoundExam.objects.filter(
            exam_date__gte=week_start
        ).values('exam_date').annotate(count=Count('id')).order_by('exam_date')
        print(f"Found procedures for {len(week_procedures)} days this week")
        
        context['week_procedures_dates'] = [entry['exam_date'].strftime('%Y-%m-%d') for entry in week_procedures]
        context['week_procedures_counts'] = [entry['count'] for entry in week_procedures]

        messages.success(request, 'Dashboard data loaded successfully')
        print("Dashboard data loaded successfully")
        
        # Debug: Print final context
        print("\nFinal context values:")
        for key, value in context.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        print(f"Dashboard Error: {str(e)}")
        import traceback
        print("Full error traceback:")
        print(traceback.format_exc())

    return render(request, 'dashboard.html', context)

def home_dashboard(request):
    # Get recent patients
    recent_patients = Patient.objects.all().order_by('-created_at')[:5]
    
    # Get recent procedures
    recent_exams = UltrasoundExam.objects.select_related('patient').order_by('-exam_date', '-exam_time')[:5]
    
    context = {
        'recent_patients': recent_patients,
        'recent_exams': recent_exams,
    }
    
    return render(request, 'home_dashboard.html', context)

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
            return redirect('admin_login')
    
    return render(request, 'admin_login.html') 