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
