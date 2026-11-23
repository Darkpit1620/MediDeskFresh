from django.contrib import admin
from .models import Patient, Appointment, Consultation

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'date_of_birth', 'created_at']
    search_fields = ['full_name', 'phone', 'email']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'clinician', 'scheduled_for', 'status']
    search_fields = ['patient__full_name', 'reason']
    list_filter = ['status']

@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'clinician', 'status', 'signed_at']
    readonly_fields = ['status', 'signed_at']
    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.status == 'signed':
            return False
        return super().has_change_permission(request, obj)
