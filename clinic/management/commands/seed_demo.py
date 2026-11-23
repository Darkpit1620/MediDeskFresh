from datetime import timedelta, date
from django.core.management.base import BaseCommand
from django.utils import timezone
from clinic.models import Patient, Appointment
class Command(BaseCommand):
    help = 'Add fictional demonstration patients and appointments (never real records)'
    def handle(self, *args, **kwargs):
        examples = [
            ('Alex Example', date(1991, 4, 10)),
            ('Jamie Sample', date(1985, 11, 2)),
            ('Taylor Demo', date(2000, 8, 18)),
        ]
        for idx, (name, birth) in enumerate(examples):
            patient, _ = Patient.objects.get_or_create(full_name=name, date_of_birth=birth)
            when = (timezone.now()+timedelta(days=idx+1)).replace(hour=8+idx, minute=0, second=0, microsecond=0)
            Appointment.objects.get_or_create(patient=patient, scheduled_for=when,
                defaults={'reason': 'Fictional demonstration visit', 'status': 'scheduled'})
        self.stdout.write(self.style.SUCCESS('Fictional demonstration records are ready.'))
