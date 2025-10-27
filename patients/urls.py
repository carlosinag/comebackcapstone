from django.urls import path
from . import views, api
from . import admin_views

urlpatterns = [
    # Landing and authentication
    path('', views.LandingView.as_view(), name='landing'),
    path('staff-login/', views.staff_login, name='staff_login'),
    path('staff-logout/', views.staff_logout, name='staff_logout'),
    path('patient-login/', views.patient_login, name='patient_login'),
    path('patient-register/', views.patient_register, name='patient_register'),
    path('patient-portal/', views.patient_portal, name='patient-portal'),
    path('patient-logout/', views.patient_logout, name='patient_logout'),
    path('patient-exam/<int:exam_id>/', views.patient_view_exam, name='patient_view_exam'),
    path('patient-exam/<int:exam_id>/download/', views.patient_download_exam, name='patient-download-exam'),
    
    # Patient settings
    path('patient-settings/', views.patient_settings, name='patient-settings'),
    path('patient-settings/password/', views.patient_change_password, name='patient-change-password'),
    path('patient-settings/profile/', views.patient_update_profile, name='patient-update-profile'),
    
    # Patient appointments
    path('patient-appointments/', views.patient_appointments, name='patient-appointments'),
    path('patient-appointments/book/', views.patient_book_appointment, name='patient-book-appointment'),
    path('patient-appointments/<int:appointment_id>/update/', views.patient_update_appointment, name='patient-update-appointment'),
    path('patient-appointments/<int:appointment_id>/cancel/', views.patient_cancel_appointment, name='patient-cancel-appointment'),
    
    # Patient billing
    path('patient-bills/', views.patient_bills, name='patient-bills'),
    path('patient-bills/<str:bill_number>/', views.patient_bill_detail, name='patient-bill-detail'),
    
    # Staff appointment management
    path('staff/appointments/', views.staff_appointments, name='staff-appointments'),
    path('staff/appointments/<int:appointment_id>/', views.staff_appointment_detail, name='staff-appointment-detail'),
    path('staff/appointments/<int:appointment_id>/confirm/', views.staff_confirm_appointment, name='staff-confirm-appointment'),
    path('staff/appointments/<int:appointment_id>/cancel/', views.staff_cancel_appointment, name='staff-cancel-appointment'),
    path('staff/appointments/<int:appointment_id>/complete/', views.staff_complete_appointment, name='staff-complete-appointment'),
    
    # Main site URLs
    path('home/', views.home_dashboard, name='home-dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/', views.PatientListView.as_view(), name='patient-list'),
    path('patients/archived/', views.ArchivedPatientListView.as_view(), name='archived-patient-list'),
    path('custom-admin/patients/archived/', views.ArchivedPatientListView.as_view(template_name='admin/archived_patient_list.html'), name='admin-archived-patient-list'),
    path('patient/new/', views.PatientCreateView.as_view(), name='patient-create'),
    path('patient/<int:pk>/', views.PatientDetailView.as_view(), name='patient-detail'),
    path('patient/<int:pk>/update/', views.PatientUpdateView.as_view(), name='patient-update'),
    path('patient/<int:pk>/delete/', views.PatientDeleteView.as_view(), name='patient-delete'),
    path('patient/<int:pk>/unarchive/', views.unarchive_patient, name='patient-unarchive'),
    path('patient/<int:pk>/annotate/', views.ImageAnnotationView.as_view(), name='image-annotation'),
    path('patient/<int:patient_id>/exam/new/', views.UltrasoundExamCreateView.as_view(), name='exam-create'),
    path('family/<int:family_group_id>/medical-history/', views.family_medical_history, name='family-medical-history'),
    path('exam/<int:pk>/', views.UltrasoundExamDetailView.as_view(), name='exam-detail'),
    path('exam/<int:pk>/update/', views.UltrasoundExamUpdateView.as_view(), name='exam-update'),
    path('image/<int:image_id>/annotate/', views.ImageAnnotationView.as_view(), name='image-specific-annotation'),
    path('exam/<int:pk>/download-docx/', views.download_ultrasound_docx, name='download-ultrasound-docx'),
    
    # API endpoints
    path('api/exams/<int:exam_id>/annotations/', api.exam_annotations, name='exam-annotations'),
    path('api/exams/<int:exam_id>/save-preview/', api.save_annotation_preview, name='save-annotation-preview'),
    path('patient/<int:patient_id>/upload-image/', views.exam_image_upload, name='exam-image-upload'),
    
    # Custom admin interface
    path('custom-admin/login/', views.admin_login, name='admin_login'),
    path('custom-admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('custom-admin/analytics/', admin_views.admin_analytics, name='admin_analytics'),
    path('custom-admin/patients/', admin_views.admin_patient_list, name='admin_patient_list'),
    path('custom-admin/billing-report/', admin_views.admin_billing_report, name='admin_billing_report'),
    path('custom-admin/billing-export/', admin_views.admin_billing_export, name='admin_billing_export'),
    path('custom-admin/examinations/', admin_views.admin_examinations, name='admin_examinations'),
    path('ultrasound-image/<int:image_id>/delete/', views.delete_ultrasound_image, name='delete-ultrasound-image'),
    path('custom-admin/update-expenses/', admin_views.update_expenses, name='update_expenses'),
    path('custom-admin/add-expense/', admin_views.add_expense, name='add_expense'),
    path('custom-admin/delete-expense/', admin_views.delete_expense, name='delete_expense'),
    path('custom-admin/get-expenses/', admin_views.get_expenses, name='get_expenses'),
    path('custom-admin/get-total-expenses/', admin_views.get_total_expenses, name='get_total_expenses'),
    path('custom-admin/prices/', admin_views.admin_prices, name='admin_prices'),
    path('custom-admin/add-procedure/', admin_views.add_procedure, name='add_service'),
    path('custom-admin/edit-procedure/<int:procedure_id>/', admin_views.edit_procedure, name='edit_procedure'),
    path('custom-admin/update-service-price/', admin_views.update_service_price, name='update_service_price'),
    path('custom-admin/users/', admin_views.admin_users, name='admin_users'),
    path('custom-admin/users/add/', admin_views.admin_add_user, name='admin_add_user'),
    path('custom-admin/users/<int:user_id>/edit/', admin_views.admin_edit_user, name='admin_edit_user'),
    path('custom-admin/users/<int:user_id>/change-password/', admin_views.admin_change_user_password, name='admin_change_user_password'),
    path('custom-admin/patients/<int:pk>/archive/', admin_views.admin_archive_patient, name='admin_archive_patient'),
    path('custom-admin/patients/<int:pk>/unarchive/', admin_views.admin_unarchive_patient, name='admin_unarchive_patient'),

    # Forbidden page for invalid navigation
    path('forbidden/', views.forbidden_page, name='forbidden'),
]
