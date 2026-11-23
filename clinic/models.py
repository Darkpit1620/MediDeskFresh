from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class Patient(models.Model):
    full_name = models.CharField(max_length=160)
    date_of_birth = models.DateField()
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name', 'id']

    def __str__(self):
        return self.full_name

class Appointment(models.Model):
    STATUS = [('scheduled','Scheduled'), ('checked_in','Checked in'), ('completed','Completed'), ('cancelled','Cancelled')]
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='appointments')
    clinician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='medidesk_appointments')
    scheduled_for = models.DateTimeField()
    reason = models.CharField(max_length=220)
    status = models.CharField(max_length=20, choices=STATUS, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_for', 'id']

    def clean(self):
        super().clean()
        if self.clinician_id and self.status != 'cancelled' and self.scheduled_for:
            if Appointment.objects.filter(clinician_id=self.clinician_id, scheduled_for=self.scheduled_for).exclude(status='cancelled').exclude(pk=self.pk).exists():
                raise ValidationError({'scheduled_for': 'This clinician already has an appointment at that time.'})

    def __str__(self):
        return f'{self.patient} – {self.scheduled_for:%Y-%m-%d %H:%M}'

class Consultation(models.Model):
    STATUS = [('draft','Draft'), ('signed','Signed')]
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name='consultation')
    clinician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='medidesk_consultations')
    symptoms = models.TextField()
    assessment = models.TextField(blank=True)
    plan = models.TextField(blank=True)
    systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    diastolic = models.PositiveSmallIntegerField(null=True, blank=True)
    pulse = models.PositiveSmallIntegerField(null=True, blank=True)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    oxygen_saturation = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    signed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def clean(self):
        super().clean()
        for field, low, high in [
            ('systolic',40,300), ('diastolic',20,200), ('pulse',20,250),
            ('temperature_c',30,45), ('oxygen_saturation',0,100),
        ]:
            value = getattr(self, field)
            if value is not None and not (low <= value <= high):
                raise ValidationError({field: f'Enter a value between {low} and {high}.'})
        if (self.systolic is None) != (self.diastolic is None):
            raise ValidationError('Enter both blood-pressure measurements or neither.')

    def __str__(self):
        return f'Consultation #{self.pk or "new"} – {self.appointment.patient}'
