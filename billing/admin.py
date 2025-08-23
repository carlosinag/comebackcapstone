from django.contrib import admin
from .models import Bill, Payment, ServiceType, BillItem

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_price', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'patient', 'bill_date', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'bill_date', 'created_at']
    search_fields = ['bill_number', 'patient__first_name', 'patient__last_name']
    readonly_fields = ['bill_number', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('patient', 'bill_date', 'status', 'notes')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'discount', 'tax', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['bill', 'amount', 'payment_date', 'payment_method', 'change', 'created_by', 'created_at']
    list_filter = ['payment_method', 'payment_date', 'created_at']
    search_fields = ['bill__bill_number', 'reference_number', 'created_by']
    readonly_fields = ['change', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Payment Details', {
            'fields': ('bill', 'amount', 'payment_date', 'payment_method')
        }),
        ('Additional Information', {
            'fields': ('reference_number', 'created_by')
        }),
        ('Calculated Fields', {
            'fields': ('change', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, created):
        if not obj.created_by:
            obj.created_by = request.user.get_full_name()
        super().save_model(request, obj, created)

@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
    list_display = ['bill', 'service', 'exam', 'amount', 'notes']
    list_filter = ['service', 'exam__exam_date']
    search_fields = ['bill__bill_number', 'service__name']
    ordering = ['-bill__created_at']
