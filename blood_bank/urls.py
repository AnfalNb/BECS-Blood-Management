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
from . import chatbot_views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

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

    path('admin-users/', views.admin_users_page, name='admin_users'),
    path('research/', views.research_page, name='research'),
    path('api/users/', views.get_users, name='get_users'),
    path('api/users/create/', views.create_user, name='create_user'),
    path('api/deidentified/', views.get_deidentified_data, name='deidentified_data'),
    path('export/deidentified/csv/', views.export_deidentified_csv, name='export_deidentified_csv'),

    path('donations-list/', views.donations_list, name='donations_list'),
    path('api/search-donations/', views.search_donations, name='search_donations'),
    path('api/export-search/', views.export_search_results, name='export_search_results'),


    path('expiration-tracking/', views.expiration_tracking, name='expiration_tracking'),
    path('api/expiration-data/', views.get_expiration_data, name='expiration_data'),
    path('api/mark-expired/', views.mark_as_expired, name='mark_expired'),
    path('api/batch-remove-expired/', views.batch_remove_expired, name='batch_remove_expired'),
    path('export/expiration-report/', views.export_expiration_report, name='export_expiration_report'),


    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/dashboard-data/', views.get_dashboard_data, name='dashboard_data'),


    path('reports/', views.reports_generator, name='reports_generator'),
    path('api/generate-report/', views.generate_custom_report, name='generate_report'),



    path('chatbot/', chatbot_views.chatbot_page, name='chatbot'),
    path('api/chatbot/send/', chatbot_views.chatbot_send_message, name='chatbot_send_message'),
    path('api/chatbot/suggestions/', chatbot_views.chatbot_get_suggestions, name='chatbot_suggestions'),
]

