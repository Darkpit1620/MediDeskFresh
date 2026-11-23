from django import forms
from clinic.models import Appointment
from .models import Invoice, InvoiceLine, Payment, Service


class StyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'field')


class ServiceForm(StyledForm):
    class Meta:
        model = Service
        fields = ['code', 'name', 'description', 'price', 'active']


class InvoiceForm(StyledForm):
    class Meta:
        model = Invoice
        fields = ['patient', 'appointment', 'due_on', 'memo']
        widgets = {'due_on': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def clean(self):
        values = super().clean()
        patient = values.get('patient')
        appointment = values.get('appointment')
        if patient and appointment and appointment.patient_id != patient.pk:
            self.add_error('appointment', 'Appointment must belong to this patient.')
        return values


class InvoiceLineForm(StyledForm):
    class Meta:
        model = InvoiceLine
        fields = ['service', 'quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.filter(active=True)
        self.fields['quantity'].initial = 1


class PaymentForm(StyledForm):
    class Meta:
        model = Payment
        fields = ['amount', 'method', 'reference', 'note']

    def __init__(self, *args, invoice, **kwargs):
        self.invoice = invoice
        super().__init__(*args, **kwargs)
        self.fields['amount'].help_text = f'Maximum outstanding: {invoice.balance:.2f}'

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount > self.invoice.balance:
            raise forms.ValidationError('Amount exceeds the current invoice balance.')
        return amount

    def clean(self):
        values = super().clean()
        if values.get('method') in ('mpesa', 'bank', 'card') and not values.get('reference', '').strip():
            self.add_error('reference', 'Enter the verified transaction reference.')
        return values
