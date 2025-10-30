from django.db import models
from django.core.validators import RegexValidator

from django.utils import timezone
from datetime import timedelta
class BloodDonation(models.Model):
    BLOOD_TYPES = [
        ('A+', 'A+'), ('O+', 'O+'), ('B+', 'B+'), ('AB+', 'AB+'),
        ('A-', 'A-'), ('O-', 'O-'), ('B-', 'B-'), ('AB-', 'AB-'),
    ]
    
    blood_type = models.CharField(max_length=3, choices=BLOOD_TYPES)
    donation_date = models.DateField()
    donor_id = models.CharField(
        max_length=9,
        validators=[RegexValidator(r'^\d{9}$', 'מספר ת"ז חייב להכיל 9 ספרות')]
    )
    donor_name = models.CharField(max_length=200)
    is_available = models.BooleanField(default=True)
    
    # שדה חדש - תאריך תפוגה
    expiration_date = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'blood_donations'
        ordering = ['donation_date']
    
    def save(self, *args, **kwargs):
        """חישוב אוטומטי של תאריך תפוגה (35 יום מהתרומה)"""
        if not self.expiration_date and self.donation_date:
            self.expiration_date = self.donation_date + timedelta(days=35)
        super().save(*args, **kwargs)
    
    def days_until_expiry(self):
        """כמה ימים נשארו עד התפוגה"""
        if not self.expiration_date:
            return None
        delta = self.expiration_date - timezone.now().date()
        return delta.days
    
    def is_expired(self):
        """האם המנה פגה"""
        if not self.expiration_date:
            return False
        return timezone.now().date() > self.expiration_date
    
    def is_expiring_soon(self, days=7):
        """האם המנה תפוג בקרוב"""
        days_left = self.days_until_expiry()
        if days_left is None:
            return False
        return 0 <= days_left <= days
    
    def expiration_status(self):
        """סטטוס תפוגה: expired, expiring_soon, ok"""
        if self.is_expired():
            return 'expired'
        elif self.is_expiring_soon():
            return 'expiring_soon'
        return 'ok'
    
    def __str__(self):
        return f"{self.blood_type} - {self.donor_name} - {self.donation_date}"

class AuditLog(models.Model):
    """
    Audit Trail - לוג לכל פעילות במערכת
    """
    ACTION_CHOICES = [
        ('DONATION_ADDED', 'קליטת תרומת דם'),
        ('BLOOD_DISPENSED', 'ניפוק דם רגיל'),
        ('EMERGENCY_DISPENSED', 'ניפוק חירום'),
        ('DATA_EXPORTED', 'יצוא נתונים'),
        ('RECORD_VIEWED', 'צפייה ברשומה'),
        ('INVENTORY_CHECKED', 'בדיקת מלאי'),
        ('SEARCH_PERFORMED', 'ביצוע חיפוש'),  
        ('BLOOD_EXPIRED', 'סימון מנה כפגה'),  
        ('BATCH_EXPIRED', 'הסרת מנות פגות'), 
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.CharField(max_length=200, default='system')
    details = models.TextField()
    blood_type = models.CharField(max_length=3, blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    success = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.get_action_display()}"


from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """משתמש מותאם עם תפקידים"""
    ROLE_CHOICES = [
        ('ADMIN', 'אדמין'),
        ('USER', 'עובד בנק דם'),
        ('RESEARCHER', 'סטודנט מחקר'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='USER')
    phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'ADMIN'
    
    def is_user(self):
        return self.role == 'USER'
    
    def is_researcher(self):
        return self.role == 'RESEARCHER'
    
    