"""Regression tests for read-only, permission-restricted clinic analytics."""
import csv
from datetime import date, datetime, time
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import Invoice, InvoiceLine, Payment, Service
from clinic.models import Appointment, Consultation, Patient
from .services import last_six_months, month_snapshot, next_month, parse_month, previous_month


class ClinicReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first = timezone.localdate().replace(day=1)
        cls.prev = previous_month(cls.first)
        cls.bill_user = get_user_model().objects.create_user(
            username='report_billing', password='a-strong-demo-password', is_staff=True)
        cls.staff_user = get_user_model().objects.create_user(
            username='report_general', password='another-strong-password', is_staff=True)
        cls.clinician = get_user_model().objects.create_user(
            username='report_clinician', password='clinician-password-123', is_staff=True)
        cls.superuser = get_user_model().objects.create_superuser(
            username='report_super', email='super@example.test', password='super-password-123')
        bill_group, _ = Group.objects.get_or_create(name='Billing')
        cls.bill_user.groups.add(bill_group)
        clinician_group, _ = Group.objects.get_or_create(name='Clinician')
        cls.clinician.groups.add(clinician_group)
        cls.patient = Patient.objects.create(full_name='CONFIDENTIAL TEST PATIENT',
                                             date_of_birth=date(2000, 1, 1))
        appointment_time = timezone.make_aware(
            datetime.combine(cls.first, time(10, 0)), timezone.get_current_timezone())
        cls.appointment = Appointment.objects.create(patient=cls.patient,
            clinician=cls.clinician, scheduled_for=appointment_time,
            reason='Demo', status='completed')
        cls.consultation = Consultation.objects.create(
            appointment=cls.appointment, clinician=cls.clinician,
            symptoms='Fictional visit', status='signed')
        cls.service = Service.objects.create(code='DEMO-RPT', name='Demo consultation', price=Decimal('100.00'))
        cls.invoice = Invoice.objects.create(patient=cls.patient, issued_on=cls.first,
                                             appointment=cls.appointment, created_by=cls.bill_user)
        InvoiceLine.objects.create(invoice=cls.invoice, service=cls.service,
                                   description='Demo consultation', unit_price=Decimal('100.00'), quantity=2)
        cls.payment = Payment.objects.create(invoice=cls.invoice, amount=Decimal('50.00'),
                                              method='cash', recorded_by=cls.bill_user)

    def test_only_billing_members_and_superusers_see_reports(self):
        for path in ('reports_home', 'reports_monthly_csv', 'reports_trends_csv'):
            url = reverse(path)
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(self.staff_user)
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(self.clinician)
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(self.bill_user)
            self.assertEqual(self.client.get(url).status_code, 200)
            self.client.force_login(self.superuser)
            self.assertEqual(self.client.get(url).status_code, 200)
            self.client.logout()

    def test_monthly_figures_do_not_confuse_billed_with_received(self):
        row = month_snapshot(self.first)
        self.assertEqual(row['appointments'], 1)
        self.assertEqual(row['new_patients'], 1)
        self.assertEqual(row['consultations'], 1)
        self.assertEqual(row['invoice_count'], 1)
        self.assertEqual(row['billed'], Decimal('200.00'))
        self.assertEqual(row['cash_received'], Decimal('50.00'))
        self.assertEqual(row['outstanding_now'], Decimal('150.00'))
        self.assertIn(('Completed', 1), row['appointment_statuses'])
        self.assertIn(('Signed', 1), row['consultation_statuses'])

    def test_cash_month_differs_from_invoice_month(self):
        # Move the payment timestamp into the prior month; it no longer counts as
        # cash received this month but still decreases today's outstanding balance.
        previous_date = timezone.make_aware(
            datetime.combine(self.prev, time(12, 0)), timezone.get_current_timezone())
        Payment.objects.filter(pk=self.payment.pk).update(recorded_at=previous_date)
        current = month_snapshot(self.first)
        prior = month_snapshot(self.prev)
        self.assertEqual(current['billed'], Decimal('200.00'))
        self.assertEqual(current['cash_received'], Decimal('0.00'))
        self.assertEqual(prior['cash_received'], Decimal('50.00'))
        self.assertEqual(current['outstanding_now'], Decimal('150.00'))

    def test_current_outstanding_covers_all_invoice_months(self):
        old_invoice = Invoice.objects.create(
            patient=self.patient, issued_on=self.prev, created_by=self.bill_user)
        InvoiceLine.objects.create(invoice=old_invoice, service=self.service,
            description='Earlier demo service', unit_price=Decimal('75.00'), quantity=1)
        current = month_snapshot(self.first)
        self.assertEqual(current['billed'], Decimal('200.00'))
        self.assertEqual(current['outstanding_now'], Decimal('225.00'))

    def test_no_financial_rows_yield_zeroes(self):
        InvoiceLine.objects.all().delete()
        Payment.objects.all().delete()
        row = month_snapshot(self.first)
        self.assertEqual(row['billed'], Decimal('0.00'))
        self.assertEqual(row['cash_received'], Decimal('0.00'))
        self.assertEqual(row['outstanding_now'], Decimal('0.00'))

    def test_csv_has_summary_only_no_patient_names(self):
        self.client.force_login(self.bill_user)
        for path in ('reports_monthly_csv', 'reports_trends_csv'):
            response = self.client.get(reverse(path), {'month': self.first.strftime('%Y-%m')})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response['Content-Type'].startswith('text/csv'))
            self.assertIn('attachment', response['Content-Disposition'])
            self.assertNotIn('CONFIDENTIAL TEST PATIENT', response.content.decode('utf-8'))
        monthly_rows = list(csv.reader(StringIO(
            self.client.get(reverse('reports_monthly_csv')).content.decode('utf-8'))))
        self.assertTrue(any(row[0] == 'Invoice line totals issued in month'
                            and Decimal(row[1]) == Decimal('200.00') for row in monthly_rows if len(row) > 1))

    def test_filter_bad_month_returns_warning_not_server_error(self):
        self.client.force_login(self.bill_user)
        for bad in ('2099-13', '2026-2', 'not-a-month', '0000-01', '2001-01anything'):
            response = self.client.get(reverse('reports_home'), {'month': bad})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'requested month was invalid')

    def test_six_months_includes_five_previous_months(self):
        trend = last_six_months(self.first)
        self.assertEqual(len(trend), 6)
        self.assertEqual(trend[-1]['month'], self.first.strftime('%Y-%m'))
        self.assertEqual(trend[0]['month'],
                         previous_month(previous_month(previous_month(previous_month(previous_month(self.first))))).strftime('%Y-%m'))

    def test_month_helpers_cross_year_boundaries(self):
        self.assertEqual(next_month(date(2026, 12, 1)), date(2027, 1, 1))
        self.assertEqual(previous_month(date(2027, 1, 1)), date(2026, 12, 1))
        self.assertEqual(parse_month('2026-12'), (date(2026, 12, 1), False))
        self.assertTrue(parse_month('2026-00')[1])

    def test_dashboard_has_reports_navigation_and_no_patient_details(self):
        self.client.force_login(self.bill_user)
        response = self.client.get(reverse('reports_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clinic reports')
        self.assertContains(response, 'Export monthly CSV')
        self.assertNotContains(response, 'CONFIDENTIAL TEST PATIENT')
        homepage = self.client.get(reverse('dashboard'))
        self.assertContains(homepage, 'Reports')
