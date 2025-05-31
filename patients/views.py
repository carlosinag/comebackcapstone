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