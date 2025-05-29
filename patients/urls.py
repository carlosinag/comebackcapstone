from django.urls import path
from . import views

urlpatterns = [
    path('', views.PatientListView.as_view(), name='patient-list'),
    path('patient/new/', views.PatientCreateView.as_view(), name='patient-create'),
    path('patient/<int:pk>/', views.PatientDetailView.as_view(), name='patient-detail'),
    path('patient/<int:pk>/update/', views.PatientUpdateView.as_view(), name='patient-update'),
    path('patient/<int:patient_id>/exam/new/', views.UltrasoundExamCreateView.as_view(), name='exam-create'),
    path('exam/<int:pk>/', views.UltrasoundExamDetailView.as_view(), name='exam-detail'),
    path('exam/<int:pk>/update/', views.UltrasoundExamUpdateView.as_view(), name='exam-update'),
] 