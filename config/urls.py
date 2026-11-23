from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from clinic import views

urlpatterns = [
    path('reports/', include('insights.urls')),
    path('billing/', include('billing.urls')),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='clinic/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/new/', views.patient_create, name='patient_create'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/new/', views.appointment_create, name='appointment_create'),
    path('appointments/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    path('consultations/', views.consultation_list, name='consultation_list'),
    path('consultations/new/', views.consultation_create, name='consultation_create'),
    path('consultations/<int:pk>/', views.consultation_detail, name='consultation_detail'),
    path('consultations/<int:pk>/edit/', views.consultation_edit, name='consultation_edit'),
    path('consultations/<int:pk>/sign/', views.consultation_sign, name='consultation_sign'),
    path('api/health/', views.health, name='health'),
]
