from django.urls import path
from core import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('domains/', views.domain_list, name='domain_list'),
    path('domain/add/', views.domain_form, name='domain_form'),
    path('domain/edit/<int:domain_id>/', views.domain_form, name='domain_form'),
    path('alert-config/', views.alert_config, name='alert_config'),
    path('mfa-setup/', views.mfa_setup, name='mfa_setup'),
    path('change-password/', views.change_password, name='change_password'),
    path('toggle-monitor/<int:domain_id>/<str:monitor_type>/', views.toggle_monitor, name='toggle_monitor'),
    path('toggle-active/<int:domain_id>/', views.toggle_active, name='toggle_active'),
    path('delete-domain/<int:domain_id>/', views.delete_domain, name='delete_domain'),
    path('toggle-all-monitors/<int:domain_id>/<str:state>/', views.toggle_all_monitors, name='toggle_all_monitors'),
]
