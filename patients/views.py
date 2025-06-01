from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.db import models, transaction
from .models import Patient, UltrasoundExam, UltrasoundImage, FamilyGroup
from .forms import PatientForm, UltrasoundExamForm
from django.db.models import Count, Sum
from django.db.models.functions import ExtractWeek
from django.utils import timezone
from datetime import timedelta
from billing.models import Bill
from django.contrib.auth import authenticate, login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin

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
        # Check for potential family members with the same last name
        last_name = form.cleaned_data['last_name']
        potential_family_members = Patient.objects.filter(last_name=last_name)
        
        if potential_family_members.exists():
            # Store form data in session
            form_data = form.cleaned_data
            # Convert date objects to string for session storage
            form_data['date_of_birth'] = form_data['date_of_birth'].strftime('%Y-%m-%d')
            self.request.session['pending_patient_data'] = form_data
            # Redirect to family confirmation page
            return redirect('confirm-family', last_name=last_name)
        
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

class PatientDeleteView(LoginRequiredMixin, DeleteView):
    model = Patient
    template_name = 'patients/patient_confirm_delete.html'
    success_url = reverse_lazy('patient-list')
    
    def delete(self, request, *args, **kwargs):
        try:
            # Get the patient
            patient = self.get_object()
            
            # If patient is part of a family group and is the last member
            if patient.family_group and patient.family_group.family_members.count() == 1:
                patient.family_group.delete()
            
            # Delete the patient
            patient.delete()
            messages.success(request, 'Patient record deleted successfully.')
            return HttpResponseRedirect(self.success_url)
        except Exception as e:
            messages.error(request, f'Error deleting patient: {str(e)}')
            return HttpResponseRedirect(self.get_success_url())

class UltrasoundExamCreateView(CreateView):
    model = UltrasoundExam
    form_class = UltrasoundExamForm
    template_name = 'patients/ultrasound_form.html'

    def get_initial(self):
        initial = super().get_initial()
        if 'patient_id' in self.kwargs:
            initial['patient'] = get_object_or_404(Patient, pk=self.kwargs['patient_id'])
        return initial

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Save the exam first
                self.object = form.save()
                
                # Handle multiple image uploads
                files = self.request.FILES.getlist('images[]')
                for file in files:
                    UltrasoundImage.objects.create(
                        exam=self.object,
                        image=file
                    )
                
                messages.success(self.request, 'Ultrasound examination record created successfully.')
                return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f'Error saving examination: {str(e)}')
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('patient-detail', kwargs={'pk': self.object.patient.pk})

class UltrasoundExamUpdateView(UpdateView):
    model = UltrasoundExam
    form_class = UltrasoundExamForm
    template_name = 'patients/ultrasound_form.html'

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Save the exam first
                self.object = form.save()
                
                # Handle multiple image uploads
                files = self.request.FILES.getlist('images[]')
                for file in files:
                    UltrasoundImage.objects.create(
                        exam=self.object,
                        image=file
                    )
                
                messages.success(self.request, 'Ultrasound examination record updated successfully.')
                return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f'Error updating examination: {str(e)}')
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('patient-detail', kwargs={'pk': self.object.patient.pk})

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
        
        # Create a new UltrasoundImage instance
        ultrasound_image = UltrasoundImage.objects.create(
            exam=exam,
            image=image_file
        )
        
        messages.success(request, 'Image uploaded successfully.')
    except UltrasoundExam.DoesNotExist:
        messages.error(request, 'Invalid examination selected.')
    except Exception as e:
        messages.error(request, f'Error uploading image: {str(e)}')
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

@require_http_methods(["POST"])
def delete_ultrasound_image(request, image_id):
    image = get_object_or_404(UltrasoundImage, pk=image_id)
    exam = image.exam
    if request.user.is_authenticated:
        image.delete()
        messages.success(request, 'Image deleted successfully.')
    return HttpResponseRedirect(reverse_lazy('exam-update', kwargs={'pk': exam.pk}))

def dashboard(request):
    try:
        today = timezone.now().date()
        
        # Get total counts
        context = {
            'total_patients': Patient.objects.count(),
            'total_procedures': UltrasoundExam.objects.count(),
        }
        
        # Calculate weekly revenue
        week_start = today - timedelta(days=today.weekday())
        weekly_bills = Bill.objects.filter(
            bill_date__gte=week_start,
            status__in=['PAID', 'PARTIAL']
        )
        weekly_total = weekly_bills.aggregate(Sum('total_amount'))['total_amount__sum']
        context['weekly_revenue'] = "{:,.2f}".format(weekly_total if weekly_total else 0)

        # Procedure Distribution
        procedures = UltrasoundExam.objects.values(
            'procedure_type__name'
        ).annotate(count=Count('id'))
        
        context['procedure_distribution_data'] = [p['count'] for p in procedures]
        context['procedure_distribution_labels'] = [p['procedure_type__name'] for p in procedures]

        # Findings Distribution
        findings = UltrasoundExam.objects.values('recommendations').annotate(count=Count('id'))
        context['findings_distribution_data'] = [f['count'] for f in findings]
        context['findings_distribution_labels'] = [dict(UltrasoundExam.RECOMMENDATION_CHOICES)[f['recommendations']] for f in findings]

        # Monthly Revenue
        six_months_ago = today - timedelta(days=180)
        monthly_revenue = Bill.objects.filter(
            bill_date__gte=six_months_ago,
            status__in=['PAID', 'PARTIAL']
        ).values('bill_date').annotate(
            total=Sum('total_amount')
        ).order_by('bill_date')
        
        context['monthly_revenue_dates'] = [entry['bill_date'].strftime('%Y-%m-%d') for entry in monthly_revenue]
        context['monthly_revenue_values'] = [float(entry['total']) for entry in monthly_revenue]

        # Weekly Procedures
        week_procedures = UltrasoundExam.objects.filter(
            exam_date__gte=week_start
        ).values('exam_date').annotate(
            count=Count('id')
        ).order_by('exam_date')
        
        context['week_procedures_dates'] = [entry['exam_date'].strftime('%Y-%m-%d') for entry in week_procedures]
        context['week_procedures_counts'] = [entry['count'] for entry in week_procedures]

        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return render(request, 'dashboard.html', {'error': str(e)})

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
    # Clear all messages
    storage = messages.get_messages(request)
    storage.used = True
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
            return redirect('admin_login')
    
    return render(request, 'admin_login.html')

def confirm_family_relationship(request, last_name):
    if request.method == 'POST':
        is_family = request.POST.get('is_family') == 'yes'
        family_member_id = request.POST.get('family_member_id')
        
        # Get the pending patient data from session
        patient_data = request.session.get('pending_patient_data')
        if not patient_data:
            messages.error(request, 'Patient data not found. Please try registering again.')
            return redirect('patient-create')
        
        try:
            # Convert string date back to date object
            patient_data['date_of_birth'] = timezone.datetime.strptime(
                patient_data['date_of_birth'], 
                '%Y-%m-%d'
            ).date()
            
            # Create the new patient
            new_patient = Patient.objects.create(**patient_data)
            
            if is_family and family_member_id:
                # Get or create family group
                existing_patient = Patient.objects.get(id=family_member_id)
                if existing_patient.family_group:
                    new_patient.family_group = existing_patient.family_group
                else:
                    family_group = FamilyGroup.objects.create(
                        name=f"{last_name} Family"
                    )
                    existing_patient.family_group = family_group
                    existing_patient.save()
                    new_patient.family_group = family_group
                new_patient.save()
            
            # Clear session data
            if 'pending_patient_data' in request.session:
                del request.session['pending_patient_data']
            
            messages.success(request, 'Patient record created successfully.')
            return redirect('patient-detail', pk=new_patient.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating patient: {str(e)}')
            return redirect('patient-create')
    
    # GET request - show confirmation page
    potential_family_members = Patient.objects.filter(last_name=last_name)
    return render(request, 'patients/confirm_family.html', {
        'potential_family_members': potential_family_members,
        'last_name': last_name
    })

def family_medical_history(request, family_group_id):
    family_group = get_object_or_404(FamilyGroup, id=family_group_id)
    family_members = family_group.family_members.all()
    
    # Get all exams for all family members
    all_exams = UltrasoundExam.objects.filter(
        patient__in=family_members
    ).select_related('patient', 'procedure_type').order_by('-exam_date')
    
    # Group exams by procedure type
    exams_by_procedure = {}
    for exam in all_exams:
        procedure_name = exam.procedure_type.name
        if procedure_name not in exams_by_procedure:
            exams_by_procedure[procedure_name] = []
        exams_by_procedure[procedure_name].append(exam)
    
    # Calculate statistics and patterns
    procedure_stats = {}
    for procedure_name, exams in exams_by_procedure.items():
        stats = {
            'total_exams': len(exams),
            'members_affected': len(set(exam.patient.id for exam in exams)),
            'common_findings': get_common_findings(exams),
            'latest_exam': {
                'exam_date': exams[0].exam_date.strftime('%Y-%m-%d') if exams else None
            },
            'recommendations': get_recommendation_stats(exams)
        }
        procedure_stats[procedure_name] = stats
    
    context = {
        'family_group': family_group,
        'family_members': family_members,
        'exams_by_procedure': exams_by_procedure,
        'procedure_stats': procedure_stats,
        'total_exams': all_exams.count(),
    }
    
    return render(request, 'patients/family_medical_history.html', context)

def get_common_findings(exams):
    # Extract common words/phrases from findings and impressions
    all_findings = ' '.join([
        f"{exam.findings} {exam.impression}" for exam in exams
    ]).lower()
    
    # You could implement more sophisticated text analysis here
    # For now, we'll just count common medical terms
    common_terms = [
        'mass', 'cyst', 'nodule', 'lesion', 'normal', 'abnormal',
        'inflammation', 'enlarged', 'reduced', 'calcification'
    ]
    
    findings_count = {}
    for term in common_terms:
        count = all_findings.count(term)
        if count > 0:
            findings_count[term] = count
    
    # Sort by frequency
    return dict(sorted(findings_count.items(), key=lambda x: x[1], reverse=True))

def get_recommendation_stats(exams):
    recommendations = {}
    for exam in exams:
        rec = exam.get_recommendations_display()
        recommendations[rec] = recommendations.get(rec, 0) + 1
    return recommendations 