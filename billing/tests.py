from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clinic.models import Appointment, Patient
from .models import Invoice, InvoiceLine, Payment, Service
from .views import csv_safe


class BillingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_superuser(username='billing_manager_demo', password='notarealpassword')
        self.staff = User.objects.create_user(username='reception_demo', password='notarealpassword', is_staff=True)
        self.bill_user = User.objects.create_user(username='billing_demo', password='notarealpassword', is_staff=True)
        self.outsider = User.objects.create_user(username='notstaff_demo', password='notarealpassword')
        group = Group.objects.create(name='Billing')
        self.bill_user.groups.add(group)
        self.patient = Patient.objects.create(full_name='Fictional Alice', date_of_birth='1990-05-05')
        self.patient2 = Patient.objects.create(full_name='Fictional Bob', date_of_birth='1995-04-04')
        self.appointment = Appointment.objects.create(
            patient=self.patient, scheduled_for=timezone.now(), reason='Fictional appointment')
        self.service = Service.objects.create(code='CONS', name='Consultation demo', price=Decimal('150.00'))

    def new_invoice(self):
        return Invoice.objects.create(patient=self.patient, appointment=self.appointment, created_by=self.manager)

    def add_line(self, invoice, price='150.00', qty=1):
        return InvoiceLine.objects.create(invoice=invoice, service=self.service,
            description=self.service.name, unit_price=Decimal(price), quantity=qty)

    def test_financial_pages_require_billing_role(self):
        urls = [reverse('billing_home'), reverse('billing_services'), reverse('billing_invoices'),
                reverse('billing_invoice_create'), reverse('billing_export')]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.outsider)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.bill_user)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_create_invoice_and_line_snapshots_price(self):
        self.client.force_login(self.bill_user)
        response = self.client.post(reverse('billing_invoice_create'), {
            'patient': self.patient.pk, 'appointment': self.appointment.pk,
            'due_on': '', 'memo': 'Demo invoice'})
        self.assertEqual(response.status_code, 302)
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.payment_status, 'Draft')
        response = self.client.post(reverse('billing_line_add', args=[invoice.pk]), {
            'service': self.service.pk, 'quantity': 2})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(invoice.total, Decimal('300.00'))
        self.service.price = Decimal('900.00')
        self.service.save()
        self.assertEqual(invoice.total, Decimal('300.00'))

    def test_mismatched_appointment_cannot_be_billed(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse('billing_invoice_create'), {
            'patient': self.patient2.pk, 'appointment': self.appointment.pk, 'memo': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Appointment must belong')
        self.assertFalse(Invoice.objects.exists())

    def test_partial_payments_and_rejection_of_overpayment(self):
        invoice = self.new_invoice()
        self.add_line(invoice)
        self.client.force_login(self.bill_user)
        result = self.client.post(reverse('billing_payment_create', args=[invoice.pk]), {
            'amount': '100.00', 'method': 'cash', 'reference': '', 'note': 'Demo'})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(invoice.balance, Decimal('50.00'))
        result = self.client.post(reverse('billing_payment_create', args=[invoice.pk]), {
            'amount': '51.00', 'method': 'cash', 'reference': '', 'note': ''})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(invoice.payment_status, 'Partially paid')

    def test_payment_reference_required_for_non_cash_methods(self):
        invoice = self.new_invoice()
        self.add_line(invoice)
        self.client.force_login(self.manager)
        result = self.client.post(reverse('billing_payment_create', args=[invoice.pk]), {
            'amount': '25', 'method': 'mpesa', 'reference': '', 'note': ''})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(Payment.objects.count(), 0)

    def test_duplicate_payment_reference_is_rejected(self):
        invoice = self.new_invoice()
        self.add_line(invoice)
        self.client.force_login(self.manager)
        args = [invoice.pk]
        data = {'amount': '20.00', 'method': 'mpesa', 'reference': 'DEMO-REF-1', 'note': ''}
        self.assertEqual(self.client.post(reverse('billing_payment_create', args=args), data).status_code, 302)
        response = self.client.post(reverse('billing_payment_create', args=args), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.count(), 1)

    def test_paid_invoice_cannot_accept_another_payment(self):
        invoice = self.new_invoice()
        self.add_line(invoice)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.post(reverse('billing_payment_create', args=[invoice.pk]), {
            'amount': '150.00', 'method': 'cash', 'reference': '', 'note': ''}).status_code, 302)
        self.assertEqual(invoice.payment_status, 'Paid')
        self.assertEqual(self.client.get(reverse('billing_payment_create', args=[invoice.pk])).status_code, 302)

    def test_invoice_model_rejects_wrong_patient(self):
        invoice = Invoice(patient=self.patient2, appointment=self.appointment, created_by=self.manager)
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_csv_formula_injection_is_escaped(self):
        self.assertEqual(csv_safe('=SUM(1,2)'), "'=SUM(1,2)")
        self.assertEqual(csv_safe('  @DANGER'), "'  @DANGER")
        self.assertEqual(csv_safe('Demo Person'), 'Demo Person')
        self.client.force_login(self.manager)
        invoice = self.new_invoice()
        self.add_line(invoice)
        content = self.client.get(reverse('billing_export')).content.decode('utf-8')
        self.assertIn(invoice.reference, content)

    def test_setup_role_idempotent(self):
        call_command('setup_billing_role', verbosity=0)
        call_command('setup_billing_role', verbosity=0)
        self.assertEqual(Group.objects.filter(name='Billing').count(), 1)
