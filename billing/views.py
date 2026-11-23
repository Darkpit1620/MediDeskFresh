"""Billing for fictional clinic records; payments are manually recorded only."""
import csv
import re
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InvoiceForm, InvoiceLineForm, PaymentForm, ServiceForm
from .models import Invoice, InvoiceLine, Payment, Service


def billing_staff(user):
    return (user.is_authenticated and user.is_active and user.is_staff and
            (user.is_superuser or user.groups.filter(name='Billing').exists()))


billing_only = user_passes_test(billing_staff, login_url='login')


def invoices_with_totals():
    return Invoice.objects.select_related('patient', 'appointment').prefetch_related('lines', 'payments')


@billing_only
def overview(request):
    invoices = list(invoices_with_totals()[:100])
    return render(request, 'billing/overview.html', {
        'invoices': invoices[:8],
        'invoice_count': Invoice.objects.count(),
        'service_count': Service.objects.filter(active=True).count(),
        'unpaid_count': sum(item.balance > Decimal('0.00') and bool(item.lines.all()) for item in invoices),
        'outstanding_preview': sum((item.balance for item in invoices), Decimal('0.00')),
    })


@billing_only
def service_list(request):
    return render(request, 'billing/services.html', {'items': Service.objects.all()})


@billing_only
def service_create(request):
    form = ServiceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, f'Service {item.code} created.')
        return redirect('billing_services')
    return render(request, 'billing/form.html', {'form': form, 'title': 'Add clinic service', 'back': 'billing_services'})


@billing_only
def service_edit(request, pk):
    item = get_object_or_404(Service, pk=pk)
    form = ServiceForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Service saved. Earlier invoice prices remain unchanged.')
        return redirect('billing_services')
    return render(request, 'billing/form.html', {'form': form, 'title': 'Edit clinic service', 'back': 'billing_services'})


@billing_only
def invoice_list(request):
    q = request.GET.get('q', '').strip()[:100]
    rows = invoices_with_totals()
    if q:
        rows = rows.filter(Q(reference__icontains=q) | Q(patient__full_name__icontains=q))
    return render(request, 'billing/invoices.html', {'items': rows[:100], 'q': q})


@billing_only
def invoice_create(request):
    form = InvoiceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.created_by = request.user
        item.full_clean()
        item.save()
        messages.success(request, 'Invoice created. Add one or more service lines.')
        return redirect('billing_line_add', pk=item.pk)
    return render(request, 'billing/form.html', {'form': form, 'title': 'Create invoice', 'back': 'billing_invoices'})


@billing_only
def invoice_detail(request, pk):
    item = get_object_or_404(invoices_with_totals(), pk=pk)
    return render(request, 'billing/detail.html', {'item': item})


@billing_only
def line_add(request, pk):
    item = get_object_or_404(Invoice, pk=pk)
    form = InvoiceLineForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        line = form.save(commit=False)
        line.invoice = item
        line.description = line.service.name
        line.unit_price = line.service.price  # Snapshot, never changes when service is edited.
        line.full_clean()
        line.save()
        messages.success(request, 'Service line added.')
        return redirect('billing_invoice_detail', pk=pk)
    return render(request, 'billing/form.html', {
        'form': form, 'title': f'Add service to {item.reference}', 'back_url': item.get_absolute_url() if hasattr(item, 'get_absolute_url') else None,
        'invoice_id': pk,
    })


@billing_only
def record_payment(request, pk):
    # Lock when supported by the database; model validation repeats the balance check.
    item = get_object_or_404(invoices_with_totals(), pk=pk)
    if request.method == 'GET' and item.balance <= Decimal('0.00'):
        messages.info(request, 'This invoice has no outstanding balance.')
        return redirect('billing_invoice_detail', pk=pk)
    form = PaymentForm(request.POST or None, invoice=item)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                current = get_object_or_404(Invoice.objects.select_for_update(), pk=pk)
                payment = form.save(commit=False)
                payment.invoice = current
                payment.recorded_by = request.user
                payment.full_clean()
                payment.save()
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, f'Could not record this payment. Check the amount and reference. {exc}')
        else:
            messages.success(request, 'Payment record saved. Verify it against your external receipt.')
            return redirect('billing_invoice_detail', pk=pk)
    return render(request, 'billing/payment.html', {'form': form, 'item': item})


def csv_safe(value):
    text = str(value) if value is not None else ''
    if re.match(r'^\s*[=+\-@]', text):
        return "'" + text
    return text


@billing_only
def export_invoices(request):
    result = HttpResponse(content_type='text/csv; charset=utf-8')
    result['Content-Disposition'] = 'attachment; filename="medidesk-invoices-demo.csv"'
    writer = csv.writer(result)
    writer.writerow(['Reference', 'Patient', 'Issued', 'Total', 'Recorded payments', 'Balance', 'Status'])
    for item in invoices_with_totals()[:10000]:
        writer.writerow([csv_safe(item.reference), csv_safe(item.patient.full_name), item.issued_on.isoformat(),
                         str(item.total), str(item.paid), str(item.balance), item.payment_status])
    return result
