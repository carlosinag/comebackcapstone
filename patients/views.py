from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from .models import Patient, UltrasoundExam
from .forms import PatientForm, UltrasoundExamForm

class PatientListView(ListView):
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    ordering = ['-created_at']

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