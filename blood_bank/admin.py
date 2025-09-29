from django.contrib import admin
from .models import BloodDonation

@admin.register(BloodDonation)
class BloodDonationAdmin(admin.ModelAdmin):
    list_display = ['blood_type', 'donor_name', 'donor_id', 'donation_date', 'is_available']
    list_filter = ['blood_type', 'is_available', 'donation_date']
    search_fields = ['donor_name', 'donor_id']
    date_hierarchy = 'donation_date'