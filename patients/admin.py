from django.contrib import admin
from .models import Patient, UltrasoundExam

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'age', 'sex', 'contact_number', 'email')
    search_fields = ('first_name', 'last_name', 'contact_number', 'email')
    list_filter = ('sex',)

@admin.register(UltrasoundExam)
class UltrasoundExamAdmin(admin.ModelAdmin):
    list_display = ('patient', 'procedure_type', 'exam_date')
    list_filter = ('procedure_type', 'exam_date')
    search_fields = ('patient__first_name', 'patient__last_name')
    date_hierarchy = 'exam_date' 