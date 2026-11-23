"""Aggregated operational and billing reports; no patient-level export."""
import csv
from decimal import Decimal

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.shortcuts import render

from billing.views import billing_staff
from .services import last_six_months, month_snapshot, parse_month

reports_only = user_passes_test(billing_staff, login_url='login')


def selected_month(request):
    month, invalid = parse_month(request.GET.get('month', ''))
    return month, invalid


@reports_only
def dashboard(request):
    month, invalid = selected_month(request)
    snapshot = month_snapshot(month)
    history = last_six_months(month)
    scale = max((max(row['billed'], row['cash_received']) for row in history), default=Decimal('0.00'))
    for row in history:
        row['billed_width'] = round(100 * row['billed'] / scale) if scale else 0
        row['cash_width'] = round(100 * row['cash_received'] / scale) if scale else 0
    return render(request, 'insights/dashboard.html', {
        'data': snapshot, 'trends': history, 'invalid_month': invalid,
    })


def csv_output(filename, rows):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'no-store'
    writer = csv.writer(response)
    for row in rows:
        writer.writerow(row)
    return response


@reports_only
def monthly_csv(request):
    month, _ = selected_month(request)
    item = month_snapshot(month)
    rows = [
        ['MediDesk demo aggregated report', item['month']],
        ['Metric', 'Value'],
        ['Appointments scheduled in month', item['appointments']],
        ['Patients registered in month', item['new_patients']],
        ['Consultations created in month', item['consultations']],
        ['Invoices issued in month', item['invoice_count']],
        ['Invoice line totals issued in month', str(item['billed'])],
        ['Payments recorded in month', str(item['cash_received'])],
        ['Current outstanding across all invoice months', str(item['outstanding_now'])],
        [],
        ['Appointment status', 'Count'],
        *item['appointment_statuses'],
        [],
        ['Consultation status', 'Count'],
        *item['consultation_statuses'],
    ]
    return csv_output(f'medidesk-summary-{item["month"]}.csv', rows)


@reports_only
def trends_csv(request):
    month, _ = selected_month(request)
    rows = [['Month', 'Appointments scheduled', 'Patients registered',
             'Consultations created', 'Invoices issued', 'Invoice line totals', 'Payments recorded']]
    for r in last_six_months(month):
        rows.append([r['month'], r['appointments'], r['new_patients'], r['consultations'],
                     r['invoice_count'], str(r['billed']), str(r['cash_received'])])
    return csv_output(f'medidesk-trends-{month:%Y-%m}.csv', rows)
