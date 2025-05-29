from django.contrib import admin
from .models import Patient, UltrasoundExam

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'sex', 'contact_number', 'email')
    search_fields = ('name', 'contact_number', 'email')
    list_filter = ('sex',)

@admin.register(UltrasoundExam)
class UltrasoundExamAdmin(admin.ModelAdmin):
    list_display = ('patient', 'procedure_type', 'exam_date', 'radiologist')
    list_filter = ('procedure_type', 'exam_date', 'radiologist')
    search_fields = ('patient__name', 'radiologist', 'technologist')
    date_hierarchy = 'exam_date' 