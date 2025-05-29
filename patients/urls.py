from django.urls import path
from . import views
from . import api

urlpatterns = [
    path('', views.home_dashboard, name='home-dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/', views.PatientListView.as_view(), name='patient-list'),
    path('patient/new/', views.PatientCreateView.as_view(), name='patient-create'),
    path('patient/<int:pk>/', views.PatientDetailView.as_view(), name='patient-detail'),
    path('patient/<int:pk>/update/', views.PatientUpdateView.as_view(), name='patient-update'),
    path('patient/<int:pk>/annotate/', views.ImageAnnotationView.as_view(), name='image-annotation'),
    path('patient/<int:patient_id>/exam/new/', views.UltrasoundExamCreateView.as_view(), name='exam-create'),
    path('exam/<int:pk>/', views.UltrasoundExamDetailView.as_view(), name='exam-detail'),
    path('exam/<int:pk>/update/', views.UltrasoundExamUpdateView.as_view(), name='exam-update'),
    
    # API endpoints
    path('api/exams/<int:exam_id>/annotations/', api.exam_annotations, name='exam-annotations'),
    path('patient/<int:patient_id>/upload-image/', views.exam_image_upload, name='exam-image-upload'),
] 