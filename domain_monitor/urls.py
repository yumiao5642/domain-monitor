from django.urls import path
from core import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('domains/', views.domain_list, name='domain_list'),
    path('domain/add/', views.domain_form, name='domain_form'),
    path('domain/<int:domain_id>/', views.domain_form, name='domain_form'),
    path('toggle/<int:domain_id>/<str:monitor_type>/', views.toggle_monitor, name='toggle_monitor'),
    path('toggle-all/<int:domain_id>/<str:action>/', views.toggle_all_monitors, name='toggle_all_monitors'),
    path('delete/<int:domain_id>/', views.delete_domain, name='delete_domain'),
    path('bulk-action/', views.bulk_action, name='bulk_action'),
    path('alert-config/', views.alert_config, name='alert_config'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('mfa-setup/', views.user_login, name='mfa_setup'),  # Placeholder
]
