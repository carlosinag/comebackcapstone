from django.urls import path
from . import views, api
from . import admin_views

urlpatterns = [
    # Landing and authentication
    path('', views.LandingView.as_view(), name='landing'),
    path('staff-login/', views.staff_login, name='staff_login'),
    path('patient-login/', views.patient_login, name='patient_login'),
    path('patient-portal/', views.patient_portal, name='patient-portal'),
    path('patient-logout/', views.patient_logout, name='patient_logout'),
    path('patient-exam/<int:exam_id>/', views.patient_view_exam, name='patient_view_exam'),
    
    # Main site URLs
    path('home/', views.home_dashboard, name='home-dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/', views.PatientListView.as_view(), name='patient-list'),
    path('patient/new/', views.PatientCreateView.as_view(), name='patient-create'),
    path('patient/<int:pk>/', views.PatientDetailView.as_view(), name='patient-detail'),
    path('patient/<int:pk>/update/', views.PatientUpdateView.as_view(), name='patient-update'),
    path('patient/<int:pk>/delete/', views.PatientDeleteView.as_view(), name='patient-delete'),
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
    path('custom-admin/billing-report/', admin_views.admin_billing_report, name='admin_billing_report'),
    path('custom-admin/billing-export/', admin_views.admin_billing_export, name='admin_billing_export'),
    path('ultrasound-image/<int:image_id>/delete/', views.delete_ultrasound_image, name='delete-ultrasound-image'),
    path('confirm-family/<str:last_name>/', views.confirm_family_relationship, name='confirm-family'),
    path('admin/update-expenses/', admin_views.update_expenses, name='update_expenses'),
] 