from django.contrib import admin
from django.utils import timezone
from .models import *

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'first_name', 'last_name', 'birthday', 'sex', 'contact_number', 'email',
        'is_archived', 'archived_at'
    )
    search_fields = ('first_name', 'last_name', 'contact_number', 'email')
    list_filter = ('sex', 'is_archived')

    actions = ['archive_selected', 'unarchive_selected']

    # Hide default delete action in actions dropdown
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    # Remove delete permission to prevent hard deletes
    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Archive selected patients")
    def archive_selected(self, request, queryset):
        updated = queryset.update(is_archived=True, archived_at=timezone.now())
        self.message_user(request, f"Archived {updated} patient(s).")

    @admin.action(description="Unarchive selected patients")
    def unarchive_selected(self, request, queryset):
        updated = queryset.update(is_archived=False, archived_at=None)
        self.message_user(request, f"Unarchived {updated} patient(s).")

    # Intercept deletes in admin to archive instead
    def delete_model(self, request, obj):
        obj.is_archived = True
        obj.archived_at = timezone.now()
        obj.save(update_fields=['is_archived', 'archived_at'])
        self.message_user(request, "Patient archived (not deleted).")

    def delete_queryset(self, request, queryset):
        updated = queryset.update(is_archived=True, archived_at=timezone.now())
        self.message_user(request, f"Archived {updated} patient(s) (not deleted).")

@admin.register(UltrasoundExam)
class UltrasoundExamAdmin(admin.ModelAdmin):
    list_display = ('patient', 'procedure_type', 'exam_date')
    list_filter = ('procedure_type', 'exam_date')
    search_fields = ('patient__first_name', 'patient__last_name')
    date_hierarchy = 'exam_date' 

admin.site.register(Appointment)
admin.site.register(UltrasoundImage)