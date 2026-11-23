from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='billing_home'),
    path('services/', views.service_list, name='billing_services'),
    path('services/new/', views.service_create, name='billing_service_create'),
    path('services/<int:pk>/edit/', views.service_edit, name='billing_service_edit'),
    path('invoices/', views.invoice_list, name='billing_invoices'),
    path('invoices/new/', views.invoice_create, name='billing_invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='billing_invoice_detail'),
    path('invoices/<int:pk>/lines/new/', views.line_add, name='billing_line_add'),
    path('invoices/<int:pk>/payments/new/', views.record_payment, name='billing_payment_create'),
    path('invoices/export.csv', views.export_invoices, name='billing_export'),
]
