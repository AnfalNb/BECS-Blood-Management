from django.db import models
from django.core.validators import RegexValidator

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
    
    class Meta:
        db_table = 'blood_donations'
        ordering = ['donation_date']
    
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
