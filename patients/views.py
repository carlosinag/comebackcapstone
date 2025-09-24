from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.db import models, transaction
from .models import Patient, UltrasoundExam, UltrasoundImage, FamilyGroup, Appointment
from .forms import PatientForm, UltrasoundExamForm, PatientPasswordChangeForm, PatientProfileForm, PatientUserForm, AppointmentForm, AppointmentUpdateForm
from django.db.models import Count, Sum
from django.db.models.functions import ExtractWeek
from django.utils import timezone
from datetime import timedelta
from billing.models import Bill, ServiceType
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import REDIRECT_FIELD_NAME
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from functools import wraps

def custom_staff_member_required(view_func):
    """
    Custom decorator that requires staff membership and redirects to forbidden page
    instead of Django admin login.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('forbidden')
        if not request.user.is_staff:
            return redirect('forbidden')
        return view_func(request, *args, **kwargs)
    return wrapper

class CustomStaffRequiredMixin(AccessMixin):
    """
    Custom mixin that requires staff membership and redirects to forbidden page
    instead of Django admin login.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('forbidden')
        if not request.user.is_staff:
            return redirect('forbidden')
        return super().dispatch(request, *args, **kwargs)

def require_valid_navigation(view_func):
    """
    Decorator to ensure views are accessed through proper navigation flow.
    Redirects to forbidden page if accessed directly via URL.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if request has proper referrer
        referer = request.META.get('HTTP_REFERER', '')
        
        # Allow POST requests (form submissions)
        if request.method == 'POST':
            return view_func(request, *args, **kwargs)
        
        # Allow if referrer is from the same domain and a valid page
        if referer and referer.startswith(request.build_absolute_uri('/')):
            # Check if referrer is from a valid page
            valid_referrer_patterns = [
                '/patients/',
                '/patient/',
                '/custom-admin/',
                '/patient-portal/',
                '/patient-appointments/',
                '/staff/appointments/',
                '/home/',
                '/dashboard/',
            ]
            
            for pattern in valid_referrer_patterns:
                if pattern in referer:
                    return view_func(request, *args, **kwargs)
        
        # If no valid referrer, redirect to forbidden page
        return redirect('forbidden')
    
    return wrapper

class PatientListView(CustomStaffRequiredMixin, ListView):
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_archived=False)
        
        # Handle search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search_query) |
                models.Q(last_name__icontains=search_query) |
                models.Q(contact_number__icontains=search_query) |
                models.Q(email__icontains=search_query) |
                models.Q(id_number__icontains=search_query)
            )
        
        # Handle sex filtering
        sex_filter = self.request.GET.get('sex_filter')
        if sex_filter in ['M', 'F']:
            queryset = queryset.filter(sex=sex_filter)

        # Patient type filter
        patient_type = self.request.GET.get('patient_type')
        if patient_type in dict(Patient.PATIENT_TYPE_CHOICES):
            queryset = queryset.filter(patient_type=patient_type)

        # Patient status filter (in/out)
        patient_status = self.request.GET.get('patient_status')
        if patient_status in dict(Patient.PATIENT_STATUS_CHOICES):
            queryset = queryset.filter(patient_status=patient_status)

        # Location filters
        region = self.request.GET.get('region')
        province = self.request.GET.get('province')
        city = self.request.GET.get('city')
        barangay = self.request.GET.get('barangay')
        if region:
            queryset = queryset.filter(region=region)
        if province:
            queryset = queryset.filter(province=province)
        if city:
            queryset = queryset.filter(city=city)
        if barangay:
            queryset = queryset.filter(barangay=barangay)

        # Created date range filters
        from django.utils.dateparse import parse_date
        created_start = self.request.GET.get('created_start')
        created_end = self.request.GET.get('created_end')
        if created_start:
            start_date = parse_date(created_start)
            if start_date:
                queryset = queryset.filter(created_at__date__gte=start_date)
        if created_end:
            end_date = parse_date(created_end)
            if end_date:
                queryset = queryset.filter(created_at__date__lte=end_date)

        # Age range filters -> convert to birthday range
        age_min = self.request.GET.get('age_min')
        age_max = self.request.GET.get('age_max')
        if age_min or age_max:
            today = timezone.now().date()
            if age_min:
                try:
                    age_min_int = int(age_min)
                    # birthdate <= today - age_min years
                    cutoff = today.replace(year=today.year - age_min_int)
                    queryset = queryset.filter(birthday__lte=cutoff)
                except Exception:
                    pass
            if age_max:
                try:
                    age_max_int = int(age_max)
                    # birthdate >= today - age_max years
                    cutoff = today.replace(year=today.year - age_max_int)
                    queryset = queryset.filter(birthday__gte=cutoff)
                except Exception:
                    pass

        # Last visit date range and has_visits
        queryset = queryset.annotate(last_visit=models.Max('ultrasound_exams__exam_date'))
        last_visit_start = self.request.GET.get('last_visit_start')
        last_visit_end = self.request.GET.get('last_visit_end')
        has_visits = self.request.GET.get('has_visits')  # 'yes' | 'no'
        if last_visit_start:
            start_lv = parse_date(last_visit_start)
            if start_lv:
                queryset = queryset.filter(last_visit__gte=start_lv)
        if last_visit_end:
            end_lv = parse_date(last_visit_end)
            if end_lv:
                queryset = queryset.filter(last_visit__lte=end_lv)
        if has_visits == 'yes':
            queryset = queryset.filter(last_visit__isnull=False)
        elif has_visits == 'no':
            queryset = queryset.filter(last_visit__isnull=True)
        
        # Handle sorting
        sort = self.request.GET.get('sort')
        if sort:
            if sort == 'age_asc':
                queryset = queryset.order_by('age')
            elif sort == 'age_desc':
                queryset = queryset.order_by('-age')
            elif sort == 'visit_asc':
                queryset = queryset.order_by('last_visit')
            elif sort == 'visit_desc':
                queryset = queryset.order_by('-last_visit')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # expose options and current selections
        context['patient_type_choices'] = Patient.PATIENT_TYPE_CHOICES
        context['patient_status_choices'] = Patient.PATIENT_STATUS_CHOICES
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'sex_filter': self.request.GET.get('sex_filter', ''),
            'patient_type': self.request.GET.get('patient_type', ''),
            'patient_status': self.request.GET.get('patient_status', ''),
            'region': self.request.GET.get('region', ''),
            'province': self.request.GET.get('province', ''),
            'city': self.request.GET.get('city', ''),
            'barangay': self.request.GET.get('barangay', ''),
            'created_start': self.request.GET.get('created_start', ''),
            'created_end': self.request.GET.get('created_end', ''),
            'age_min': self.request.GET.get('age_min', ''),
            'age_max': self.request.GET.get('age_max', ''),
            'last_visit_start': self.request.GET.get('last_visit_start', ''),
            'last_visit_end': self.request.GET.get('last_visit_end', ''),
            'has_visits': self.request.GET.get('has_visits', ''),
            'sort': self.request.GET.get('sort', ''),
        }
        return context

class PatientDetailView(CustomStaffRequiredMixin, DetailView):
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all ultrasound exams for this patient
        context['exams'] = self.object.ultrasound_exams.all().order_by('-exam_date', '-exam_time')
        return context

class PatientCreateView(CustomStaffRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'
    success_url = reverse_lazy('patient-list')

    def form_valid(self, form):
        messages.success(self.request, 'Patient record created successfully.')
        return super().form_valid(form)

@method_decorator(custom_staff_member_required, name='dispatch')
@method_decorator(require_valid_navigation, name='dispatch')
class PatientUpdateView(UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'
    
    def get_success_url(self):
        return reverse_lazy('patient-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Patient record updated successfully.')
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        patient = self.get_object()
        if patient.is_archived:
            messages.warning(request, 'Cannot edit an archived patient. Please unarchive first.')
            return redirect('patient-detail', pk=patient.pk)
        return super().dispatch(request, *args, **kwargs)

@method_decorator(custom_staff_member_required, name='dispatch')
@method_decorator(require_valid_navigation, name='dispatch')
class PatientDeleteView(LoginRequiredMixin, DeleteView):
    model = Patient
    template_name = 'patients/patient_confirm_delete.html'
    success_url = reverse_lazy('patient-list')
    
    def get(self, request, *args, **kwargs):
        patient = self.get_object()
        if patient.is_archived:
            messages.info(request, 'Patient is already archived.')
            return redirect('patient-detail', pk=patient.pk)
        return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        try:
            # Get the patient
            patient = self.get_object()
            
            # Archive the patient instead of deleting
            patient.is_archived = True
            patient.archived_at = timezone.now()
            patient.save(update_fields=['is_archived', 'archived_at'])
            messages.success(request, 'Patient moved to archive.')
            return HttpResponseRedirect(self.success_url)
        except Exception as e:
            messages.error(request, f'Error deleting patient: {str(e)}')
            return HttpResponseRedirect(self.get_success_url())

@method_decorator(staff_member_required, name='dispatch')
class ArchivedPatientListView(ListView):
    model = Patient
    template_name = 'patients/archived_patient_list.html'
    context_object_name = 'patients'
    ordering = ['-archived_at']

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_archived=True)
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search_query) |
                models.Q(last_name__icontains=search_query)
            )
        return queryset

@custom_staff_member_required
def unarchive_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient.is_archived = False
    patient.archived_at = None
    patient.save(update_fields=['is_archived', 'archived_at'])
    messages.success(request, 'Patient restored from archive.')
    return redirect('archived-patient-list')

@method_decorator(staff_member_required, name='dispatch')
@method_decorator(require_valid_navigation, name='dispatch')
class UltrasoundExamCreateView(CreateView):
    model = UltrasoundExam
    form_class = UltrasoundExamForm
    template_name = 'patients/ultrasound_form.html'

    def get_initial(self):
        initial = super().get_initial()
        if 'patient_id' in self.kwargs:
            initial['patient'] = get_object_or_404(Patient, pk=self.kwargs['patient_id'])
        return initial

    def dispatch(self, request, *args, **kwargs):
        if 'patient_id' in kwargs:
            patient = get_object_or_404(Patient, pk=kwargs['patient_id'])
            if patient.is_archived:
                messages.warning(request, 'Cannot add an exam to an archived patient. Please unarchive first.')
                return redirect('patient-detail', pk=patient.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            # Prevent creating exams for archived patients via form submission
            selected_patient = form.cleaned_data.get('patient')
            if selected_patient and selected_patient.is_archived:
                messages.warning(self.request, 'Cannot add an exam to an archived patient. Please unarchive first.')
                return self.form_invalid(form)
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

@method_decorator(staff_member_required, name='dispatch')
@method_decorator(require_valid_navigation, name='dispatch')
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

class UltrasoundExamDetailView(CustomStaffRequiredMixin, DetailView):
    model = UltrasoundExam
    template_name = 'patients/ultrasound_detail.html'
    context_object_name = 'exam'

class ImageAnnotationView(CustomStaffRequiredMixin, DetailView):
    model = Patient
    template_name = 'patients/image_annotation.html'
    context_object_name = 'patient'

    def get_object(self, queryset=None):
        if 'image_id' in self.kwargs:
            # If image_id is provided, get the patient through the image
            image = get_object_or_404(UltrasoundImage, id=self.kwargs['image_id'])
            self.specific_image = image
            return image.exam.patient
        return super().get_object(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, 'specific_image'):
            # If we're annotating a specific image, only show that exam
            context['exams'] = [self.specific_image.exam]
            context['specific_image_id'] = self.specific_image.id
        else:
            # Otherwise show all exams
            context['exams'] = self.object.ultrasound_exams.all().order_by('-exam_date', '-exam_time')
        
        # Add active procedure types to context
        context['procedure_types'] = ServiceType.objects.filter(is_active=True)
        return context

@custom_staff_member_required
@require_valid_navigation
@require_http_methods(["POST"])
def exam_image_upload(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    exam_id = request.POST.get('exam_id')
    image_files = request.FILES.getlist('images[]')
    
    if patient.is_archived:
        messages.error(request, 'Cannot upload images for an archived patient. Please unarchive first.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    if not exam_id or not image_files:
        messages.error(request, 'Both examination and images are required.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    try:
        exam = UltrasoundExam.objects.get(id=exam_id, patient=patient)
        
        # Create UltrasoundImage instances for each uploaded file
        for image_file in image_files:
            UltrasoundImage.objects.create(
                exam=exam,
                image=image_file
            )
        
        messages.success(request, f'{len(image_files)} image(s) uploaded successfully.')
    except UltrasoundExam.DoesNotExist:
        messages.error(request, 'Invalid examination selected.')
    except Exception as e:
        messages.error(request, f'Error uploading images: {str(e)}')
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

@custom_staff_member_required
@require_http_methods(["POST"])
def delete_ultrasound_image(request, image_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=403)
    
    try:
        image = get_object_or_404(UltrasoundImage, pk=image_id)
        image.delete()
        return JsonResponse({'success': True, 'message': 'Image deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@custom_staff_member_required
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

        # Advanced KPIs
        ninety_days_ago = today - timedelta(days=90)
        six_months_ago = today - timedelta(days=180)
        month_start = today.replace(day=1)

        # Active patients in last 90 days
        active_patients_qs = UltrasoundExam.objects.filter(
            exam_date__gte=ninety_days_ago
        ).values('patient').distinct()
        context['active_patients_90d'] = active_patients_qs.count()

        # New patients this month
        context['new_patients_month'] = Patient.objects.filter(created_at__date__gte=month_start).count()

        # Average procedures per patient (lifetime)
        total_exams = UltrasoundExam.objects.count()
        distinct_patients_with_exam = UltrasoundExam.objects.values('patient').distinct().count()
        avg_procs = (total_exams / distinct_patients_with_exam) if distinct_patients_with_exam else 0
        context['avg_procedures_per_patient'] = f"{avg_procs:.2f}"

        # Returning patient rate (last 6 months)
        recent_exam_counts = (
            UltrasoundExam.objects.filter(exam_date__gte=six_months_ago)
            .values('patient')
            .annotate(num_exams=Count('id'))
        )
        num_recent_unique = recent_exam_counts.count()
        num_returning = sum(1 for r in recent_exam_counts if r['num_exams'] >= 2)
        returning_rate = (num_returning / num_recent_unique * 100) if num_recent_unique else 0
        context['returning_rate_percent'] = f"{returning_rate:.1f}"

        # Procedure Distribution
        procedures = UltrasoundExam.objects.values(
            'procedure_type__name'
        ).annotate(count=Count('id'))
        
        context['procedure_distribution_data'] = [p['count'] for p in procedures]
        context['procedure_distribution_labels'] = [p['procedure_type__name'] for p in procedures]

        # Findings Distribution
        findings = UltrasoundExam.objects.values('recommendations').annotate(count=Count('id'))
        context['findings_distribution_data'] = [f['count'] for f in findings]
        
        # Safe mapping of recommendations with fallback
        recommendation_map = dict(UltrasoundExam.RECOMMENDATION_CHOICES)
        context['findings_distribution_labels'] = [
            recommendation_map.get(f['recommendations'], f['recommendations']) 
            for f in findings
        ]

        # Monthly Revenue
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

        # Demographics: Gender distribution
        gender_counts = Patient.objects.values('sex').annotate(count=Count('id'))
        gender_label_map = dict(Patient.GENDER_CHOICES)
        context['gender_distribution_labels'] = [gender_label_map.get(g['sex'], g['sex']) for g in gender_counts]
        context['gender_distribution_values'] = [g['count'] for g in gender_counts]

        # Demographics: Patient type distribution
        type_counts = Patient.objects.values('patient_type').annotate(count=Count('id'))
        type_label_map = dict(Patient.PATIENT_TYPE_CHOICES)
        context['patient_type_labels'] = [type_label_map.get(t['patient_type'], t['patient_type']) for t in type_counts]
        context['patient_type_values'] = [t['count'] for t in type_counts]

        # Age buckets (computed in Python for simplicity)
        age_buckets = {'0-17': 0, '18-29': 0, '30-44': 0, '45-59': 0, '60+': 0}
        for p in Patient.objects.exclude(birthday__isnull=True).only('birthday'):
            try:
                age = today.year - p.birthday.year - ((today.month, today.day) < (p.birthday.month, p.birthday.day))
                if age is None:
                    continue
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
        context['age_bucket_labels'] = list(age_buckets.keys())
        context['age_bucket_values'] = list(age_buckets.values())

        # Procedures per patient distribution (histogram data)
        per_patient_counts = (
            UltrasoundExam.objects.values('patient').annotate(num=Count('id')).values_list('num', flat=True)
        )
        context['procedures_per_patient_counts'] = list(per_patient_counts)

        # Top patients by revenue
        top_revenue = (
            Bill.objects.values('patient__first_name', 'patient__last_name')
            .annotate(total=Sum('total_amount'))
            .order_by('-total')[:10]
        )
        context['top_patients_labels'] = [f"{t['patient__first_name']} {t['patient__last_name']}".strip() for t in top_revenue]
        context['top_patients_revenue'] = [float(t['total']) if t['total'] else 0 for t in top_revenue]

        # Revenue by Procedure Type
        from billing.models import BillItem
        procedure_revenue = (
            BillItem.objects.filter(
                bill__status__in=['PAID', 'PARTIAL']
            )
            .values('service__name')
            .annotate(
                total_revenue=Sum('amount'),
                procedure_count=Count('id')
            )
            .order_by('-total_revenue')
        )
        
        context['procedure_revenue_labels'] = [p['service__name'] for p in procedure_revenue]
        context['procedure_revenue_values'] = [float(p['total_revenue']) if p['total_revenue'] else 0 for p in procedure_revenue]
        context['procedure_revenue_counts'] = [p['procedure_count'] for p in procedure_revenue]

        # Revenue by Location (Region)
        location_revenue = (
            Bill.objects.filter(
                status__in=['PAID', 'PARTIAL']
            )
            .values('patient__region')
            .annotate(
                total_revenue=Sum('total_amount'),
                patient_count=Count('patient', distinct=True)
            )
            .order_by('-total_revenue')
        )
        context['location_revenue_labels'] = [l['patient__region'] for l in location_revenue]
        context['location_revenue_values'] = [float(l['total_revenue']) if l['total_revenue'] else 0 for l in location_revenue]
        context['location_patient_counts'] = [l['patient_count'] for l in location_revenue]

        # Revenue by City
        city_revenue = (
            Bill.objects.filter(
                status__in=['PAID', 'PARTIAL']
            )
            .values('patient__city')
            .annotate(
                total_revenue=Sum('total_amount'),
                patient_count=Count('patient', distinct=True)
            )
            .order_by('-total_revenue')[:10]  # Top 10 cities
        )
        context['city_revenue_labels'] = [c['patient__city'] for c in city_revenue]
        context['city_revenue_values'] = [float(c['total_revenue']) if c['total_revenue'] else 0 for c in city_revenue]
        context['city_patient_counts'] = [c['patient_count'] for c in city_revenue]

        # Revenue by Payment Method
        payment_method_revenue = (
            Bill.objects.filter(
                status__in=['PAID', 'PARTIAL']
            )
            .values('payments__payment_method')
            .annotate(
                total_revenue=Sum('total_amount'),
                payment_count=Count('payments')
            )
            .filter(payments__payment_method__isnull=False)
            .order_by('-total_revenue')
        )
        context['payment_method_labels'] = [p['payments__payment_method'] for p in payment_method_revenue]
        context['payment_method_values'] = [float(p['total_revenue']) if p['total_revenue'] else 0 for p in payment_method_revenue]
        context['payment_method_counts'] = [p['payment_count'] for p in payment_method_revenue]

        # Revenue by Patient Type
        patient_type_revenue = (
            Bill.objects.filter(
                status__in=['PAID', 'PARTIAL']
            )
            .values('patient__patient_type')
            .annotate(
                total_revenue=Sum('total_amount'),
                patient_count=Count('patient', distinct=True)
            )
            .order_by('-total_revenue')
        )
        patient_type_map = dict(Patient.PATIENT_TYPE_CHOICES)
        context['patient_type_revenue_labels'] = [patient_type_map.get(p['patient__patient_type'], p['patient__patient_type']) for p in patient_type_revenue]
        context['patient_type_revenue_values'] = [float(p['total_revenue']) if p['total_revenue'] else 0 for p in patient_type_revenue]
        context['patient_type_revenue_counts'] = [p['patient_count'] for p in patient_type_revenue]

        # Monthly Revenue Trends (Last 12 months)
        monthly_trends = []
        for i in range(12):
            month_date = today.replace(day=1) - timedelta(days=30*i)
            month_revenue = Bill.objects.filter(
                bill_date__year=month_date.year,
                bill_date__month=month_date.month,
                status__in=['PAID', 'PARTIAL']
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            monthly_trends.append({
                'month': month_date.strftime('%b %Y'),
                'revenue': float(month_revenue)
            })
        monthly_trends.reverse()
        context['monthly_trend_labels'] = [m['month'] for m in monthly_trends]
        context['monthly_trend_values'] = [m['revenue'] for m in monthly_trends]

        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return render(request, 'dashboard.html', {'error': str(e)})

@custom_staff_member_required
def home_dashboard(request):
    from django.db.models import Sum, Count
    from datetime import timedelta
    from billing.models import Bill
    from .models import Appointment
    import json
    from collections import defaultdict
    
    # Get search parameter
    patient_search = request.GET.get('patient_search', '')
    
    # Query for patients based on search
    if patient_search:
        searched_patients = Patient.objects.filter(is_archived=False).filter(
            models.Q(first_name__icontains=patient_search) |
            models.Q(last_name__icontains=patient_search) |
            models.Q(contact_number__icontains=patient_search) |
            models.Q(id_number__icontains=patient_search)
        ).order_by('-created_at')[:10]  # Show more results for search
    else:
        searched_patients = None

    # Calculate KPIs
    today = timezone.now().date()
    
    # Basic counts
    total_patients = Patient.objects.filter(is_archived=False).count()
    total_procedures = UltrasoundExam.objects.count()
    
    # Revenue calculations
    total_revenue = Bill.objects.filter(status='PAID').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    pending_bills = Bill.objects.filter(status='PENDING').count()
    
    # Appointment counts
    pending_appointments = Appointment.objects.filter(status='PENDING').count()
    today_appointments = Appointment.objects.filter(appointment_date=today).count()
    
    # Advanced KPIs
    ninety_days_ago = today - timedelta(days=90)
    six_months_ago = today - timedelta(days=180)
    month_start = today.replace(day=1)

    # Active patients in last 90 days
    active_patients_qs = UltrasoundExam.objects.filter(
        exam_date__gte=ninety_days_ago
    ).values('patient').distinct()
    active_patients_90d = active_patients_qs.count()

    # New patients this month
    new_patients_month = Patient.objects.filter(
        is_archived=False,
        created_at__date__gte=month_start
    ).count()

    # Average procedures per patient (lifetime)
    distinct_patients_with_exam = UltrasoundExam.objects.values('patient').distinct().count()
    avg_procs = (total_procedures / distinct_patients_with_exam) if distinct_patients_with_exam else 0
    avg_procedures_per_patient = f"{avg_procs:.2f}"

    # Returning patient rate (last 6 months)
    recent_exam_counts = (
        UltrasoundExam.objects.filter(exam_date__gte=six_months_ago)
        .values('patient')
        .annotate(num_exams=Count('id'))
    )
    num_recent_unique = recent_exam_counts.count()
    num_returning = sum(1 for r in recent_exam_counts if r['num_exams'] >= 2)
    returning_rate = (num_returning / num_recent_unique * 100) if num_recent_unique else 0
    returning_rate_percent = f"{returning_rate:.1f}"

    # Chart Data
    # Monthly Revenue Data (Last 6 months)
    monthly_revenue_data = []
    monthly_revenue_labels = []
    for i in range(6):
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_revenue = Bill.objects.filter(
            bill_date__year=month_date.year,
            bill_date__month=month_date.month,
            status__in=['PAID', 'PARTIAL']
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        monthly_revenue_data.append(float(month_revenue))
        monthly_revenue_labels.append(month_date.strftime('%b %Y'))
    
    monthly_revenue_data.reverse()
    monthly_revenue_labels.reverse()

    # Procedure Distribution Data
    procedure_data = []
    procedure_labels = []
    procedures = UltrasoundExam.objects.values('procedure_type__name').annotate(count=Count('id')).order_by('-count')[:8]
    for proc in procedures:
        procedure_data.append(proc['count'])
        procedure_labels.append(proc['procedure_type__name'] or 'Unknown')

    # Monthly Activity Data (Last 6 months)
    activity_labels = []
    activity_procedures = []
    activity_patients = []
    
    for i in range(6):
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_procedures = UltrasoundExam.objects.filter(
            exam_date__year=month_date.year,
            exam_date__month=month_date.month
        ).count()
        month_patients = Patient.objects.filter(
            is_archived=False,
            created_at__year=month_date.year,
            created_at__month=month_date.month
        ).count()
        
        activity_labels.append(month_date.strftime('%b'))
        activity_procedures.append(month_procedures)
        activity_patients.append(month_patients)
    
    activity_labels.reverse()
    activity_procedures.reverse()
    activity_patients.reverse()
    
    context = {
        'searched_patients': searched_patients,
        'search_term': patient_search,
        'total_patients': total_patients,
        'total_procedures': total_procedures,
        'total_revenue': f"{total_revenue:,.2f}",
        'pending_bills': pending_bills,
        'active_patients_90d': active_patients_90d,
        'new_patients_month': new_patients_month,
        'avg_procedures_per_patient': avg_procedures_per_patient,
        'returning_rate_percent': returning_rate_percent,
        'pending_appointments': pending_appointments,
        'today_appointments': today_appointments,
        # Chart data
        'monthly_revenue_labels': json.dumps(monthly_revenue_labels),
        'monthly_revenue_data': json.dumps(monthly_revenue_data),
        'procedure_labels': json.dumps(procedure_labels),
        'procedure_data': json.dumps(procedure_data),
        'activity_labels': json.dumps(activity_labels),
        'activity_procedures': json.dumps(activity_procedures),
        'activity_patients': json.dumps(activity_patients),
    }
    
    return render(request, 'home_dashboard.html', context)

@custom_staff_member_required
@require_valid_navigation
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
            messages.success(request, f'Welcome back, {user.username}! You have been successfully logged in.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
            return redirect('admin_login')
    
    return render(request, 'admin_login.html')

@custom_staff_member_required
def confirm_family_relationship(request, last_name):
    # This feature has been removed. Redirect back to patient creation.
    messages.info(request, 'Family confirmation step is no longer required.')
    return redirect('patient-create')

@custom_staff_member_required
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

@custom_staff_member_required
def generate_report(request, exam_id):
    exam = get_object_or_404(UltrasoundExam, id=exam_id)
    
    # Create a new Word document
    doc = Document()
    
    # Add letterhead
    doc.add_heading('ULTRASOUND EXAMINATION REPORT', 0)
    
    # Add patient information
    doc.add_heading('Patient Information:', level=2)
    doc.add_paragraph(f'Name: {exam.patient.first_name} {exam.patient.last_name}')
    doc.add_paragraph(f'Age: {exam.patient.age}')
    doc.add_paragraph(f'Sex: {exam.patient.get_sex_display()}')
    
    # Add examination details
    doc.add_heading('Examination Details:', level=2)
    doc.add_paragraph(f'Date: {exam.exam_date}')
    doc.add_paragraph(f'Time: {exam.exam_time}')
    doc.add_paragraph(f'Procedure: {exam.procedure_type.name} ULTRASOUND')
    doc.add_paragraph(f'REQUESTING PHYSICIAN: {exam.referring_physician}')
    doc.add_paragraph(f'WARD: {exam.patient.get_patient_status_display()}')
    
    # Add findings
    doc.add_heading('RADIOLOGICAL FINDINGS:', level=2)
    doc.add_paragraph(exam.findings)
    
    # Add impression
    doc.add_heading('IMPRESSION:', level=2)
    doc.add_paragraph(exam.impression)
    
    # Add recommendations
    doc.add_heading('RECOMMENDATIONS:', level=2)
    doc.add_paragraph(f'Follow-up Duration: {exam.followup_duration or "-"}')
    doc.add_paragraph(f'Specialist Referral: {exam.specialist_referral or "-"}')
    
    # Save the document
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename=ultrasound_report_{exam.id}.docx'
    doc.save(response)
    
    return response

class LandingView(TemplateView):
    template_name = 'landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Active service types for pricing list
            context['service_types'] = ServiceType.objects.filter(is_active=True).order_by('name')
        except Exception:
            context['service_types'] = []
        return context

def patient_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and hasattr(user, 'patient'):
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}! You have been successfully logged in.')
            return redirect('patient-portal')
        else:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'patient_login.html')
    
    return render(request, 'patient_login.html')

@login_required
def patient_portal(request):
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    patient = request.user.patient
    context = {
        'patient': patient,
        'recent_exams': patient.ultrasound_exams.order_by('-exam_date', '-exam_time')[:5]
    }
    return render(request, 'patients/patient_portal.html', context)

def patient_logout(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('landing')

def staff_logout(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('staff_login')

def staff_login(request):
    # Clear all messages
    storage = messages.get_messages(request)
    storage.used = True
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff and not user.is_superuser:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}! You have been successfully logged in.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home-dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
            return redirect('staff_login')
    
    return render(request, 'staff_login.html')

@login_required
def patient_view_exam(request, exam_id):
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    exam = get_object_or_404(UltrasoundExam, id=exam_id)
    
    # Security check: ensure the patient can only view their own exams
    if exam.patient != request.user.patient:
        messages.error(request, 'Access denied. You can only view your own examinations.')
        return redirect('patient-portal')
    
    context = {
        'exam': exam,
        'patient': request.user.patient
    }
    return render(request, 'patients/patient_exam_detail.html', context)

@custom_staff_member_required
def download_ultrasound_docx(request, pk):
    exam = get_object_or_404(UltrasoundExam, pk=pk)
    
    # Create a new document
    doc = Document()
    
    # Set font to Courier New and remove any default paragraph spacing
    style = doc.styles['Normal']
    style.font.name = 'Courier New'
    style.font.size = Pt(12)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.0
    
    # Add content with exact spacing using tabs
    doc.add_paragraph(f"CASE NUMBER\t:\t{str(exam.id).zfill(3)}\t\tDATE: {exam.exam_date.strftime('%B %d, %Y').upper()}")
    doc.add_paragraph(f"NAME OF PATIENT\t:\t{exam.patient.last_name}, {exam.patient.first_name}")
    doc.add_paragraph(f"AGE\t\t:\t{exam.patient.age}")
    doc.add_paragraph(f"GENDER\t\t:\t{exam.patient.get_sex_display()}")
    doc.add_paragraph(f"MARITAL STATUS\t:\t{exam.patient.get_marital_status_display() or ''}")
    doc.add_paragraph(f"EXAMINATION PERFORMED:\t{exam.procedure_type.name} ULTRASOUND")
    doc.add_paragraph(f"\t\tO.R.\t\t\tAMOUNT PAID:")
    doc.add_paragraph(f"REQUESTING PHYSICIAN:\t\t\t\tWARD: {exam.patient.get_patient_status_display()}")
    doc.add_paragraph()
    doc.add_paragraph("RADIOLOGICAL FINDINGS:")
    doc.add_paragraph()
    doc.add_paragraph(exam.findings)
    
    if exam.procedure_type.name == 'OBSTETRIC':
        doc.add_paragraph()
        doc.add_paragraph(f"FETAL HEART RATE - {exam.fetal_heart_rate} bpm")
        doc.add_paragraph("ADEQUATE AMNIOTIC FLUID")
        doc.add_paragraph("ANTERIOR PLACENTA, GRADE I")
        doc.add_paragraph(f"FETAL SEX --- {exam.fetal_sex or 'UNDETERMINED'}")
        doc.add_paragraph(f"EDD ---- {exam.edd.strftime('%m/%d/%Y') if exam.edd else ''}")
        doc.add_paragraph(f"EFW ---- {exam.estimated_fetal_weight or ''} gms")
    
    doc.add_paragraph()
    doc.add_paragraph("IMPRESSION:")
    doc.add_paragraph()
    doc.add_paragraph(exam.impression)
    
    # Create the response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename=ultrasound_report_{exam.exam_date.strftime("%Y%m%d")}_{exam.patient.last_name}.docx'
    
    # Save the document
    doc.save(response)
    
    return response 

@login_required
def patient_settings(request):
    """Patient settings page."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    patient = request.user.patient
    context = {
        'patient': patient,
    }
    return render(request, 'patients/patient_settings.html', context)

@login_required
def patient_change_password(request):
    """Allow patients to change their password."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    if request.method == 'POST':
        form = PatientPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('patient-settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientPasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'patient': request.user.patient,
    }
    return render(request, 'patients/patient_change_password.html', context)

@login_required
def patient_update_profile(request):
    """Allow patients to update their profile information."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    patient = request.user.patient
    user = request.user
    
    if request.method == 'POST':
        profile_form = PatientProfileForm(request.POST, instance=patient)
        user_form = PatientUserForm(request.POST, instance=user)
        
        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()
            user_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('patient-settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        profile_form = PatientProfileForm(instance=patient)
        user_form = PatientUserForm(instance=user)
    
    context = {
        'profile_form': profile_form,
        'user_form': user_form,
        'patient': patient,
    }
    return render(request, 'patients/patient_update_profile.html', context)

@login_required
def patient_download_exam(request, exam_id):
    """Allow patients to download their examination report."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    exam = get_object_or_404(UltrasoundExam, id=exam_id)
    
    # Security check: ensure the patient can only download their own exams
    if exam.patient != request.user.patient:
        messages.error(request, 'Access denied. You can only download your own examinations.')
        return redirect('patient-portal')
    
    # Create a new document
    doc = Document()
    
    # Set font to Arial and formatting
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.15
    
    # Add clinic header
    doc.add_heading('ULTRASOUND EXAMINATION REPORT', 0)
    doc.add_paragraph('MSRA Services')
    doc.add_paragraph('Patient Portal Report')
    doc.add_paragraph()
    
    # Add patient information
    doc.add_heading('PATIENT INFORMATION', level=1)
    doc.add_paragraph(f'Name: {exam.patient.last_name}, {exam.patient.first_name}')
    doc.add_paragraph(f'Age: {exam.patient.age} years old')
    doc.add_paragraph(f'Sex: {exam.patient.get_sex_display()}')
    doc.add_paragraph(f'Contact Number: {exam.patient.contact_number}')
    doc.add_paragraph()
    
    # Add examination details
    doc.add_heading('EXAMINATION DETAILS', level=1)
    doc.add_paragraph(f'Examination Date: {exam.exam_date.strftime("%B %d, %Y")}')
    doc.add_paragraph(f'Examination Time: {exam.exam_time.strftime("%I:%M %p")}')
    doc.add_paragraph(f'Procedure Type: {exam.procedure_type.name} ULTRASOUND')
    doc.add_paragraph(f'Referring Physician: {exam.referring_physician}')
    doc.add_paragraph()
    
    # Add clinical findings
    if exam.findings:
        doc.add_heading('RADIOLOGICAL FINDINGS', level=1)
        doc.add_paragraph(exam.findings)
        doc.add_paragraph()
    
    # Add impression
    if exam.impression:
        doc.add_heading('IMPRESSION', level=1)
        doc.add_paragraph(exam.impression)
        doc.add_paragraph()
    
    # Add recommendations
    doc.add_heading('RECOMMENDATIONS', level=1)
    doc.add_paragraph(f'Recommendation: {exam.get_recommendations_display()}')
    if exam.followup_duration:
        doc.add_paragraph(f'Follow-up Duration: {exam.followup_duration}')
    if exam.specialist_referral:
        doc.add_paragraph(f'Specialist Referral: {exam.specialist_referral}')
    doc.add_paragraph()
    
    # Add images information
    if exam.images.exists():
        doc.add_heading('IMAGES', level=1)
        doc.add_paragraph(f'Total Images: {exam.images.count()}')
        annotated_count = exam.images.filter(annotated_image__isnull=False).count()
        if annotated_count > 0:
            doc.add_paragraph(f'Annotated Images: {annotated_count}')
        doc.add_paragraph()
    
    # Add medical disclaimer
    doc.add_heading('MEDICAL DISCLAIMER', level=1)
    disclaimer_text = """
    The information provided in this ultrasound examination report is intended for educational and informational purposes only. This report represents a preliminary analysis and should not be considered as a final medical diagnosis.

    IMPORTANT NOTICE:
    • The final diagnosis and treatment recommendations must be provided by your attending physician or qualified healthcare provider.
    • This report should be reviewed in conjunction with your complete medical history and other diagnostic tests.
    • Please consult with your healthcare provider for proper interpretation and medical decision-making.
    • For medical emergencies, contact emergency services immediately or visit the nearest emergency department.

    This report was generated from the patient portal and is for your personal medical records.
    """
    doc.add_paragraph(disclaimer_text)
    
    # Add footer
    doc.add_paragraph()
    doc.add_paragraph(f'Report Generated: {timezone.now().strftime("%B %d, %Y at %I:%M %p")}')
    doc.add_paragraph('MSRA Services - Patient Portal')
    
    # Create the response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename=ultrasound_report_{exam.patient.last_name}_{exam.exam_date.strftime("%Y%m%d")}.docx'
    
    # Save the document
    doc.save(response)
    
    return response 

@login_required
def patient_appointments(request):
    """Patient appointments page."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    patient = request.user.patient
    appointments = patient.appointments.all().order_by('appointment_date', 'appointment_time')
    
    context = {
        'patient': patient,
        'appointments': appointments,
    }
    return render(request, 'patients/patient_appointments.html', context)

@login_required
def patient_bills(request):
    """Patient bills page: list bills and statuses for the logged-in patient."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')

    patient = request.user.patient
    bills = (
        Bill.objects.filter(patient=patient)
        .order_by('-bill_date')
    )

    context = {
        'patient': patient,
        'bills': bills,
    }
    return render(request, 'patients/patient_bills.html', context)

@login_required
def patient_bill_detail(request, bill_number):
    """Patient bill detail: show items, related exam info, and payment history."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')

    patient = request.user.patient
    bill = get_object_or_404(Bill, bill_number=bill_number, patient=patient)

    bill_items = bill.items.all().select_related('exam', 'service')
    payments = bill.payments.all().order_by('-payment_date')

    total_paid = sum(payment.amount for payment in payments)
    remaining_balance = float(bill.total_amount) - float(total_paid)
    if remaining_balance < 0:
        remaining_balance = 0

    context = {
        'patient': patient,
        'bill': bill,
        'bill_items': bill_items,
        'payments': payments,
        'total_paid': total_paid,
        'remaining_balance': remaining_balance,
    }
    return render(request, 'patients/patient_bill_detail.html', context)

@login_required
def patient_book_appointment(request):
    """Allow patients to book new appointments."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = request.user.patient
            appointment.save()
            messages.success(request, 'Appointment booked successfully! We will contact you to confirm.')
            return redirect('patient-appointments')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AppointmentForm()
    
    context = {
        'form': form,
        'patient': request.user.patient,
    }
    return render(request, 'patients/patient_book_appointment.html', context)

@login_required
def patient_update_appointment(request, appointment_id):
    """Allow patients to update their appointments."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check: ensure the patient can only update their own appointments
    if appointment.patient != request.user.patient:
        messages.error(request, 'Access denied. You can only update your own appointments.')
        return redirect('patient-appointments')
    
    if request.method == 'POST':
        form = AppointmentUpdateForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated successfully!')
            return redirect('patient-appointments')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AppointmentUpdateForm(instance=appointment)
    
    context = {
        'form': form,
        'appointment': appointment,
        'patient': request.user.patient,
    }
    return render(request, 'patients/patient_update_appointment.html', context)

@login_required
def patient_cancel_appointment(request, appointment_id):
    """Allow patients to cancel their appointments."""
    if not hasattr(request.user, 'patient'):
        messages.error(request, 'Access denied. This portal is for patients only.')
        return redirect('landing')
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check: ensure the patient can only cancel their own appointments
    if appointment.patient != request.user.patient:
        messages.error(request, 'Access denied. You can only cancel your own appointments.')
        return redirect('patient-appointments')
    
    if request.method == 'POST':
        appointment.status = 'CANCELLED'
        appointment.save()
        messages.success(request, 'Appointment cancelled successfully.')
        return redirect('patient-appointments')
    
    context = {
        'appointment': appointment,
        'patient': request.user.patient,
    }
    return render(request, 'patients/patient_cancel_appointment.html', context) 

@custom_staff_member_required
def staff_appointments(request):
    """Staff view to manage all appointments."""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
    # Base queryset
    appointments = Appointment.objects.select_related('patient').order_by('appointment_date', 'appointment_time')
    
    # Apply filters
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)
    
    # Get statistics
    total_appointments = Appointment.objects.count()
    pending_appointments = Appointment.objects.filter(status='PENDING').count()
    confirmed_appointments = Appointment.objects.filter(status='CONFIRMED').count()
    today_appointments = Appointment.objects.filter(appointment_date=timezone.now().date()).count()
    
    context = {
        'appointments': appointments,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'confirmed_appointments': confirmed_appointments,
        'today_appointments': today_appointments,
        'status_filter': status_filter,
        'date_filter': date_filter,
    }
    return render(request, 'patients/staff_appointments.html', context)

@custom_staff_member_required
def staff_appointment_detail(request, appointment_id):
    """Staff view to see appointment details and manage status."""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED']:
            appointment.status = new_status
            appointment.save()
            messages.success(request, f'Appointment status updated to {new_status}.')
            return redirect('staff-appointments')
    
    context = {
        'appointment': appointment,
    }
    return render(request, 'patients/staff_appointment_detail.html', context)

@custom_staff_member_required
def staff_confirm_appointment(request, appointment_id):
    """Staff view to confirm an appointment."""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        appointment.status = 'CONFIRMED'
        appointment.save()
        messages.success(request, f'Appointment for {appointment.patient.first_name} {appointment.patient.last_name} has been confirmed.')
        return redirect('staff-appointments')
    
    context = {
        'appointment': appointment,
    }
    return render(request, 'patients/staff_confirm_appointment.html', context)

@custom_staff_member_required
def staff_cancel_appointment(request, appointment_id):
    """Staff view to cancel an appointment."""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        appointment.status = 'CANCELLED'
        appointment.save()
        messages.success(request, f'Appointment for {appointment.patient.first_name} {appointment.patient.last_name} has been cancelled.')
        return redirect('staff-appointments')
    
    context = {
        'appointment': appointment,
    }
    return render(request, 'patients/staff_cancel_appointment.html', context)

@custom_staff_member_required
def staff_complete_appointment(request, appointment_id):
    """Staff view to mark an appointment as completed."""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        appointment.status = 'COMPLETED'
        appointment.save()
        messages.success(request, f'Appointment for {appointment.patient.first_name} {appointment.patient.last_name} has been marked as completed.')
        return redirect('staff-appointments')
    
    context = {
        'appointment': appointment,
    }
    return render(request, 'patients/staff_complete_appointment.html', context)

def forbidden_page(request):
    """Custom forbidden page for invalid navigation attempts"""
    return render(request, 'forbidden.html') 