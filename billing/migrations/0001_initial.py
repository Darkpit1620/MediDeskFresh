from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone

import billing.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clinic', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=24, unique=True)),
                ('name', models.CharField(max_length=140)),
                ('description', models.CharField(blank=True, max_length=300)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['name', 'id']},
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(default=billing.models.invoice_reference, editable=False, max_length=24, unique=True)),
                ('issued_on', models.DateField(default=django.utils.timezone.localdate)),
                ('due_on', models.DateField(blank=True, null=True)),
                ('memo', models.CharField(blank=True, max_length=250)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='clinic_invoices', to='clinic.appointment')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='clinic_invoices', to='clinic.patient')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='medidesk_invoices', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at', '-pk']},
        ),
        migrations.CreateModel(
            name='InvoiceLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=180)),
                ('quantity', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lines', to='billing.invoice')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='billed_lines', to='billing.service')),
            ],
            options={'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('method', models.CharField(choices=[('cash', 'Cash'), ('mpesa', 'M-Pesa (record only)'), ('bank', 'Bank transfer (record only)'), ('card', 'Card (record only)')], max_length=12)),
                ('reference', models.CharField(blank=True, max_length=100)),
                ('note', models.CharField(blank=True, max_length=200)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='billing.invoice')),
                ('recorded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='medidesk_recorded_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-recorded_at', '-pk']},
        ),
        migrations.AddConstraint(
            model_name='payment',
            constraint=models.UniqueConstraint(condition=~models.Q(reference=''), fields=('reference',), name='medidesk_unique_nonblank_payment_reference'),
        ),
    ]
