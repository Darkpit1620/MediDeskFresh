from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction
from .forms import PatientForm, AppointmentForm, ConsultationForm
from .models import Patient, Appointment, Consultation

staff_only = user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='login')
clinician_only = user_passes_test(
    lambda u: u.is_authenticated and u.is_staff and (u.is_superuser or u.groups.filter(name='Clinician').exists()),
    login_url='login'
)

def home(request):
    return render(request, 'clinic/home.html')

def health(request):
    return JsonResponse({'project': 'MediDeskFresh', 'status': 'ok'})

@staff_only
def dashboard(request):
    return render(request, 'clinic/dashboard.html', {
        'patient_count': Patient.objects.count(),
        'appointment_count': Appointment.objects.count(),
        'today_count': Appointment.objects.filter(scheduled_for__date=timezone.localdate()).count(),
        'draft_count': Consultation.objects.filter(status='draft').count(),
        'upcoming': Appointment.objects.select_related('patient', 'clinician').filter(scheduled_for__gte=timezone.now()).exclude(status='cancelled')[:6],
    })

@staff_only
def patient_list(request):
    q = request.GET.get('q', '').strip()[:100]
    records = Patient.objects.all()
    if q:
        records = records.filter(Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q))
    return render(request, 'clinic/patient_list.html', {'records': records[:100], 'q': q})

@staff_only
def patient_create(request):
    form = PatientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        patient = form.save()
        messages.success(request, 'Patient record added.')
        return redirect('patient_detail', pk=patient.pk)
    return render(request, 'clinic/form.html', {'form': form, 'title': 'Register patient', 'cancel_url': 'patient_list'})

@staff_only
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    appointments = patient.appointments.select_related('clinician').order_by('-scheduled_for')[:25]
    return render(request, 'clinic/patient_detail.html', {'patient': patient, 'appointments': appointments})

@staff_only
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    form = PatientForm(request.POST or None, instance=patient)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Patient record updated.')
        return redirect('patient_detail', pk=pk)
    return render(request, 'clinic/form.html', {'form': form, 'title': 'Edit patient', 'cancel_url': 'patient_list'})

@staff_only
def appointment_list(request):
    records = Appointment.objects.select_related('patient', 'clinician')
    status = request.GET.get('status', '')
    if status in dict(Appointment.STATUS):
        records = records.filter(status=status)
    return render(request, 'clinic/appointment_list.html', {'records': records.order_by('-scheduled_for')[:100], 'status': status})

@staff_only
def appointment_create(request):
    form = AppointmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, 'Appointment saved.')
        return redirect('appointment_detail', pk=item.pk)
    return render(request, 'clinic/form.html', {'form': form, 'title': 'Schedule appointment', 'cancel_url': 'appointment_list'})

@staff_only
def appointment_detail(request, pk):
    item = get_object_or_404(Appointment.objects.select_related('patient','clinician'), pk=pk)
    consultation = Consultation.objects.filter(appointment=item).first()
    return render(request, 'clinic/appointment_detail.html', {'item': item, 'consultation': consultation})

@clinician_only
def consultation_list(request):
    records = Consultation.objects.select_related('appointment__patient', 'clinician')
    if not request.user.is_superuser:
        records = records.filter(clinician=request.user)
    return render(request, 'clinic/consultation_list.html', {'records': records[:100]})

@clinician_only
def consultation_create(request):
    form = ConsultationForm(request.POST or None)
    if not request.user.is_superuser:
        form.fields['appointment'].queryset = form.fields['appointment'].queryset.filter(clinician=request.user)
    if request.method == 'POST' and form.is_valid():
        instance = form.save(commit=False)
        instance.clinician = request.user
        instance.save()
        messages.success(request, 'Consultation created as draft.')
        return redirect('consultation_detail', pk=instance.pk)
    return render(request, 'clinic/form.html', {'form': form, 'title': 'New consultation (draft)', 'cancel_url': 'consultation_list'})

@clinician_only
def consultation_detail(request, pk):
    record = get_object_or_404(Consultation.objects.select_related('appointment__patient', 'clinician'), pk=pk)
    if not request.user.is_superuser and record.clinician_id != request.user.pk:
        return HttpResponseForbidden('Not assigned to this record.')
    return render(request, 'clinic/consultation_detail.html', {'item': record})

@clinician_only
def consultation_edit(request, pk):
    record = get_object_or_404(Consultation, pk=pk)
    if record.status == 'signed' or (not request.user.is_superuser and record.clinician_id != request.user.pk):
        return HttpResponseForbidden('This record cannot be edited.')
    form = ConsultationForm(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Draft updated.')
        return redirect('consultation_detail', pk=record.pk)
    return render(request, 'clinic/form.html', {'form': form, 'title': 'Edit consultation draft', 'cancel_url': 'consultation_list'})

@clinician_only
@require_POST
def consultation_sign(request, pk):
    with transaction.atomic():
        record = get_object_or_404(Consultation.objects.select_for_update(), pk=pk)
        if record.status == 'signed' or (not request.user.is_superuser and record.clinician_id != request.user.pk):
            return HttpResponseForbidden('Cannot sign this record.')
        record.status = 'signed'
        record.signed_at = timezone.now()
        record.save(update_fields=['status', 'signed_at'])
    messages.success(request, 'Consultation signed. Edits are now blocked in this demonstration.')
    return redirect('consultation_detail', pk=pk)
