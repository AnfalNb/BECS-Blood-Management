# from django.urls import path
# from . import views

# urlpatterns = [
#     path('', views.index, name='index'),
#     path('donation/', views.donation_page, name='donation'),
#     path('dispense/', views.dispense_page, name='dispense'),
#     path('emergency/', views.emergency_page, name='emergency'),
#     path('api/donation/', views.add_donation, name='add_donation'),
#     path('api/dispense/', views.dispense_blood, name='dispense_blood'),
#     path('api/emergency/', views.emergency_dispense, name='emergency_dispense'),
#     path('api/inventory/', views.get_inventory, name='inventory'),
# ]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('donation/', views.donation_page, name='donation'),
    path('dispense/', views.dispense_page, name='dispense'),
    path('emergency/', views.emergency_page, name='emergency'),
    path('audit/', views.audit_page, name='audit'),
    path('export/', views.export_page, name='export'),
    
    # API endpoints
    path('api/donation/', views.add_donation, name='add_donation'),
    path('api/dispense/', views.dispense_blood, name='dispense_blood'),
    path('api/emergency/', views.emergency_dispense, name='emergency_dispense'),
    path('api/inventory/', views.get_inventory, name='inventory'),
    path('api/audit-logs/', views.get_audit_logs, name='audit_logs'),
    
    # Export endpoints
    path('export/donations/csv/', views.export_donations_csv, name='export_donations_csv'),
    path('export/donations/pdf/', views.export_donations_pdf, name='export_donations_pdf'),
    path('export/audit/csv/', views.export_audit_csv, name='export_audit_csv'),
    path('export/audit/pdf/', views.export_audit_pdf, name='export_audit_pdf'),
]