from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/<str:bill_number>/', views.bill_detail, name='bill_detail'),
    path('create-bill/<int:exam_id>/', views.create_bill, name='create_bill'),
    path('patient/<int:patient_id>/bills/', views.patient_bills, name='patient_bills'),
] 