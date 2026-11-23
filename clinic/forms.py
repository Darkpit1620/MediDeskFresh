from django import forms
from django.contrib.auth import get_user_model
from .models import Patient, Appointment, Consultation

class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'field')

class PatientForm(StyledModelForm):
    class Meta:
        model = Patient
        fields = ['full_name', 'date_of_birth', 'phone', 'email']
        widgets = {'date_of_birth': forms.DateInput(attrs={'type':'date'}, format='%Y-%m-%d')}

class AppointmentForm(StyledModelForm):
    scheduled_for = forms.SplitDateTimeField(widget=forms.SplitDateTimeWidget(date_attrs={'type':'date','class':'field'},time_attrs={'type':'time','class':'field'}))
    class Meta:
        model = Appointment
        fields = ['patient', 'clinician', 'scheduled_for', 'reason', 'status']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clinician'].queryset = get_user_model().objects.filter(is_staff=True)

class ConsultationForm(StyledModelForm):
    class Meta:
        model = Consultation
        fields = ['appointment', 'symptoms', 'assessment', 'plan', 'systolic', 'diastolic', 'pulse', 'temperature_c', 'oxygen_saturation']
        widgets = {
            'symptoms': forms.Textarea(attrs={'rows':4}),
            'assessment': forms.Textarea(attrs={'rows':4}),
            'plan': forms.Textarea(attrs={'rows':4}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['appointment'].queryset = Appointment.objects.exclude(consultation__isnull=False)
        if self.instance and self.instance.pk:
            self.fields['appointment'].queryset = Appointment.objects.filter(pk=self.instance.appointment_id)
