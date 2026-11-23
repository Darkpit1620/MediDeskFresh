"""Fictional clinic billing records. No electronic payment processing occurs."""
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from clinic.models import Appointment, Patient

ZERO = Decimal('0.00')


def invoice_reference():
    return 'MD-' + uuid.uuid4().hex[:16].upper()


class Service(models.Model):
    code = models.CharField(max_length=24, unique=True)
    name = models.CharField(max_length=140)
    description = models.CharField(max_length=300, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name', 'id']

    def clean(self):
        super().clean()
        self.code = (self.code or '').strip().upper()
        if not self.code:
            raise ValidationError({'code': 'Enter a service code.'})

    def __str__(self):
        return f'{self.code} – {self.name}'


class Invoice(models.Model):
    reference = models.CharField(max_length=24, unique=True, default=invoice_reference, editable=False)
    patient = models.ForeignKey(Patient, related_name='clinic_invoices', on_delete=models.PROTECT)
    appointment = models.ForeignKey(Appointment, related_name='clinic_invoices', on_delete=models.PROTECT,
                                    null=True, blank=True)
    issued_on = models.DateField(default=timezone.localdate)
    due_on = models.DateField(null=True, blank=True)
    memo = models.CharField(max_length=250, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name='medidesk_invoices')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def clean(self):
        super().clean()
        if self.patient_id and self.appointment_id and self.appointment.patient_id != self.patient_id:
            raise ValidationError({'appointment': 'Appointment must belong to the selected patient.'})
        if self.due_on and self.issued_on and self.due_on < self.issued_on:
            raise ValidationError({'due_on': 'Due date cannot be earlier than the invoice date.'})

    @property
    def total(self):
        return sum((line.unit_price * line.quantity for line in self.lines.all()), ZERO)

    @property
    def paid(self):
        return sum((payment.amount for payment in self.payments.all()), ZERO)

    @property
    def balance(self):
        return max(self.total - self.paid, ZERO)

    @property
    def payment_status(self):
        if not self.lines.exists():
            return 'Draft'
        if self.balance == ZERO:
            return 'Paid'
        if self.paid > ZERO:
            return 'Partially paid'
        return 'Unpaid'

    def __str__(self):
        return self.reference


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='lines', on_delete=models.PROTECT)
    service = models.ForeignKey(Service, related_name='billed_lines', on_delete=models.PROTECT)
    description = models.CharField(max_length=180)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2,
                                     validators=[MinValueValidator(Decimal('0.01'))])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.description} × {self.quantity}'


class Payment(models.Model):
    METHODS = [('cash', 'Cash'), ('mpesa', 'M-Pesa (record only)'),
               ('bank', 'Bank transfer (record only)'), ('card', 'Card (record only)')]
    invoice = models.ForeignKey(Invoice, related_name='payments', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2,
                                 validators=[MinValueValidator(Decimal('0.01'))])
    method = models.CharField(max_length=12, choices=METHODS)
    reference = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='medidesk_recorded_payments')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at', '-pk']
        constraints = [
            models.UniqueConstraint(fields=['reference'], condition=~models.Q(reference=''),
                                    name='medidesk_unique_nonblank_payment_reference')
        ]

    def clean(self):
        super().clean()
        self.reference = (self.reference or '').strip()
        if self.method in ('mpesa', 'bank', 'card') and not self.reference:
            raise ValidationError({'reference': 'Enter the verified payment reference.'})
        if self.invoice_id and self.amount is not None and self.amount > ZERO:
            prior_payments = self.invoice.payments.exclude(pk=self.pk)
            prior_total = sum((p.amount for p in prior_payments), ZERO)
            if self.amount > self.invoice.total - prior_total:
                raise ValidationError({'amount': 'Payment exceeds the outstanding invoice balance.'})

    def __str__(self):
        return f'{self.invoice.reference}: {self.amount} ({self.get_method_display()})'
