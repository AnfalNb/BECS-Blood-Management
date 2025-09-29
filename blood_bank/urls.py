from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('donation/', views.donation_page, name='donation'),
    path('dispense/', views.dispense_page, name='dispense'),
    path('emergency/', views.emergency_page, name='emergency'),
    path('api/donation/', views.add_donation, name='add_donation'),
    path('api/dispense/', views.dispense_blood, name='dispense_blood'),
    path('api/emergency/', views.emergency_dispense, name='emergency_dispense'),
    path('api/inventory/', views.get_inventory, name='inventory'),
]