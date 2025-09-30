from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import BloodDonation, AuditLog, CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('תפקיד', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('תפקיד', {'fields': ('role', 'phone')}),
    )

@admin.register(BloodDonation)
class BloodDonationAdmin(admin.ModelAdmin):
    list_display = ['blood_type', 'donor_name', 'donor_id', 'donation_date', 'is_available']
    list_filter = ['blood_type', 'is_available', 'donation_date']
    search_fields = ['donor_name', 'donor_id']
    date_hierarchy = 'donation_date'

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'user', 'blood_type', 'quantity', 'success', 'ip_address']
    list_filter = ['action', 'success', 'timestamp']
    search_fields = ['details', 'user', 'ip_address']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp', 'action', 'user', 'details', 'blood_type', 'quantity', 'ip_address', 'success']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False