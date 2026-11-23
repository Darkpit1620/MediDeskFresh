from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Patient, Appointment, Consultation

User = get_user_model()

class MediDeskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user('reception', password='Temporary-Only-123!', is_staff=True)
        cls.clinician = User.objects.create_user('doctor', password='Temporary-Only-123!', is_staff=True)
        cls.other = User.objects.create_user('otherdoctor', password='Temporary-Only-123!', is_staff=True)
        group = Group.objects.create(name='Clinician')
        cls.clinician.groups.add(group)
        cls.other.groups.add(group)
        cls.outsider = User.objects.create_user('outsider', password='Temporary-Only-123!')
        cls.patient = Patient.objects.create(full_name='Demo Person', date_of_birth=date(1990, 1, 1))
        cls.appointment = Appointment.objects.create(
            patient=cls.patient, clinician=cls.clinician,
            scheduled_for=timezone.now()+timedelta(days=1), reason='Fictional checkup')

    def test_public_home_and_health(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('health')).json()['status'], 'ok')

    def test_protected_pages(self):
        for route in ['dashboard', 'patient_list', 'appointment_list', 'consultation_list']:
            self.assertEqual(self.client.get(reverse(route)).status_code, 302)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse('patient_list')).status_code, 302)

    def test_reception_can_register_patient(self):
        self.client.force_login(self.staff)
        result = self.client.post(reverse('patient_create'), {
            'full_name': 'Fictional Person', 'date_of_birth': '2001-03-04',
            'phone': '000-000-000', 'email': 'demo@example.invalid',
        })
        self.assertEqual(result.status_code, 302)
        self.assertTrue(Patient.objects.filter(full_name='Fictional Person').exists())

    def test_staff_cannot_open_consultations(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('consultation_list')).status_code, 302)

    def test_clinician_booking_collision_is_rejected(self):
        duplicate = Appointment(patient=self.patient, clinician=self.clinician,
                                scheduled_for=self.appointment.scheduled_for, reason='Another visit')
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_clinician_can_create_and_sign_own_consultation(self):
        self.client.force_login(self.clinician)
        result = self.client.post(reverse('consultation_create'), {
            'appointment': self.appointment.pk, 'symptoms': 'Fictional symptoms',
            'assessment': 'Demonstration assessment', 'plan': 'Demonstration plan',
            'systolic': '120', 'diastolic': '80', 'pulse': '75',
            'temperature_c': '36.8', 'oxygen_saturation': '99',
        })
        self.assertEqual(result.status_code, 302)
        record = Consultation.objects.get(appointment=self.appointment)
        self.assertEqual(record.status, 'draft')
        self.assertEqual(self.client.get(reverse('consultation_sign',args=[record.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse('consultation_sign',args=[record.pk])).status_code, 302)
        record.refresh_from_db()
        self.assertEqual(record.status, 'signed')
        self.assertIsNotNone(record.signed_at)
        self.assertEqual(self.client.get(reverse('consultation_edit',args=[record.pk])).status_code, 403)

    def test_other_clinician_cannot_see_unassigned_records(self):
        record = Consultation.objects.create(appointment=self.appointment, clinician=self.clinician,
                                            symptoms='Fictional visit')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('consultation_detail',args=[record.pk])).status_code, 403)
        self.assertNotContains(self.client.get(reverse('consultation_list')), 'Demo Person')

    def test_invalid_vitals_are_rejected(self):
        item = Consultation(appointment=self.appointment, clinician=self.clinician,
                            symptoms='Fictional visit', oxygen_saturation=101)
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_seed_command_is_idempotent(self):
        call_command('seed_demo', verbosity=0)
        count = Patient.objects.count()
        call_command('seed_demo', verbosity=0)
        self.assertEqual(Patient.objects.count(), count)
