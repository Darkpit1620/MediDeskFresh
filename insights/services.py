"""Read-only, aggregated reports for a fictional clinic demonstration.

The appointment figures use scheduled dates; invoices use issue dates; payments
use their actual recorded timestamps. These are intentionally distinct periods.
"""
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import re

from django.db.models import Count, DecimalField, F, Sum
from django.utils import timezone

from billing.models import Invoice, InvoiceLine, Payment
from clinic.models import Appointment, Consultation, Patient

ZERO = Decimal('0.00')
MONEY_FIELD = DecimalField(max_digits=18, decimal_places=2)
MONTH_PATTERN = re.compile(r'^(20\d{2}|2100)-(0[1-9]|1[0-2])$')
STATUS_LABELS = dict(Appointment.STATUS)
CONSULTATION_LABELS = dict(Consultation.STATUS)


def parse_month(text):
    """Return (first day, was_invalid). Never execute malformed input in filters."""
    current = timezone.localdate().replace(day=1)
    if text in ('', None):
        return current, False
    if not isinstance(text, str) or not MONTH_PATTERN.fullmatch(text):
        return current, True
    try:
        return date.fromisoformat(text + '-01'), False
    except ValueError:
        return current, True


def next_month(first):
    if first.month == 12:
        return date(first.year + 1, 1, 1)
    return date(first.year, first.month + 1, 1)


def previous_month(first):
    return (first - timedelta(days=1)).replace(day=1)


def timestamp_range(first):
    tz = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(first, time.min), tz),
        timezone.make_aware(datetime.combine(next_month(first), time.min), tz),
    )


def service_total(filters):
    # Billed amounts belong to the month the INVOICE was issued.
    result = InvoiceLine.objects.filter(**filters).aggregate(
        amount=Sum(F('unit_price') * F('quantity'), output_field=MONEY_FIELD)
    )['amount']
    return result or ZERO


def current_outstanding():
    """Current unpaid line-item value across all invoiced months, excluding drafts."""
    line_totals = InvoiceLine.objects.values('invoice_id').annotate(
        amount=Sum(F('unit_price') * F('quantity'), output_field=MONEY_FIELD)
    )
    paid_totals = {
        row['invoice_id']: row['amount'] or ZERO
        for row in Payment.objects.values('invoice_id').annotate(amount=Sum('amount'))
    }
    return sum((max((row['amount'] or ZERO) - paid_totals.get(row['invoice_id'], ZERO), ZERO)
                for row in line_totals), ZERO)


def month_snapshot(first, *, with_details=True):
    following = next_month(first)
    from_time, until_time = timestamp_range(first)
    appointments = Appointment.objects.filter(scheduled_for__gte=from_time, scheduled_for__lt=until_time)
    payments = Payment.objects.filter(recorded_at__gte=from_time, recorded_at__lt=until_time)
    consultations = Consultation.objects.filter(created_at__gte=from_time, created_at__lt=until_time)
    invoiced = Invoice.objects.filter(issued_on__gte=first, issued_on__lt=following)

    snapshot = {
        'month': first.strftime('%Y-%m'),
        'month_label': first.strftime('%B %Y'),
        'appointments': appointments.count(),
        'new_patients': Patient.objects.filter(created_at__gte=from_time, created_at__lt=until_time).count(),
        'consultations': consultations.count(),
        'invoice_count': invoiced.count(),
        'billed': service_total({'invoice__issued_on__gte': first,
                                 'invoice__issued_on__lt': following}),
        'cash_received': payments.aggregate(amount=Sum('amount'))['amount'] or ZERO,
    }
    if with_details:
        appointment_counts = dict(appointments.values_list('status').annotate(total=Count('id')))
        consultation_counts = dict(consultations.values_list('status').annotate(total=Count('id')))
        snapshot['appointment_statuses'] = [
            (label, appointment_counts.get(key, 0)) for key, label in Appointment.STATUS
        ]
        snapshot['consultation_statuses'] = [
            (label, consultation_counts.get(key, 0)) for key, label in Consultation.STATUS
        ]
        snapshot['outstanding_now'] = current_outstanding()
        snapshot['payment_methods'] = [
            (label, amount or ZERO)
            for key, label in Payment.METHODS
            for amount in [payments.filter(method=key).aggregate(amount=Sum('amount'))['amount']]
        ]
        snapshot['top_services'] = list(
            InvoiceLine.objects.filter(invoice__issued_on__gte=first, invoice__issued_on__lt=following)
            .values('description')
            .annotate(billed=Sum(F('unit_price') * F('quantity'), output_field=MONEY_FIELD))
            .order_by('-billed', 'description')[:5]
        )
    return snapshot


def last_six_months(first):
    months = [first]
    for _ in range(5):
        months.append(previous_month(months[-1]))
    return [month_snapshot(m, with_details=False) for m in reversed(months)]
