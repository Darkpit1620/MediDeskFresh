from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='reports_home'),
    path('monthly.csv', views.monthly_csv, name='reports_monthly_csv'),
    path('trends.csv', views.trends_csv, name='reports_trends_csv'),
]
