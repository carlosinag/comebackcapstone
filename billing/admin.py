from django.contrib import admin
from .models import ServiceType, Bill, Payment

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'patient', 'service', 'bill_date', 'total_amount', 'status')
    list_filter = ('status', 'bill_date')
    search_fields = ('bill_number', 'patient__name')
    date_hierarchy = 'bill_date'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('bill', 'amount', 'payment_date', 'payment_method', 'created_by')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('bill__bill_number', 'reference_number', 'created_by')
    date_hierarchy = 'payment_date'
