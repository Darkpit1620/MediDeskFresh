from django.contrib import admin
from django.core.exceptions import PermissionDenied
from .models import Invoice, InvoiceLine, Payment, Service


class BillingAccessMixin:
    def has_module_permission(self, request):
        u = request.user
        return bool(u.is_active and u.is_staff and (u.is_superuser or u.groups.filter(name='Billing').exists()))

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Service)
class ServiceAdmin(BillingAccessMixin, admin.ModelAdmin):
    list_display = ['code', 'name', 'price', 'active']
    search_fields = ['code', 'name']


@admin.register(Invoice)
class InvoiceAdmin(BillingAccessMixin, admin.ModelAdmin):
    list_display = ['reference', 'patient', 'issued_on', 'due_on']
    search_fields = ['reference', 'patient__full_name']
    readonly_fields = ['reference', 'created_by', 'created_at']

    def has_add_permission(self, request):
        return False  # Use the billing screens to validate patient/appointment consistency.

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(InvoiceLine)
class InvoiceLineAdmin(BillingAccessMixin, admin.ModelAdmin):
    list_display = ['invoice', 'service', 'quantity', 'unit_price']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(BillingAccessMixin, admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'method', 'reference', 'recorded_at']
    search_fields = ['invoice__reference', 'reference']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
