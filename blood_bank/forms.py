from django import forms
from .models import Donor, BloodType
from datetime import date

class DonorRegistrationForm(forms.ModelForm):
    """טופס רישום תורם חדש"""
    class Meta:
        model = Donor
        fields = ['id_number', 'full_name', 'blood_type', 'phone', 'email']
        widgets = {
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123456789',
                'maxlength': '9',
                'pattern': '[0-9]{9}',
                'dir': 'ltr'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'שם מלא',
                'dir': 'rtl'
            }),
            'blood_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '050-1234567',
                'dir': 'ltr'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com',
                'dir': 'ltr'
            }),
        }
        labels = {
            'id_number': 'תעודת זהות',
            'full_name': 'שם מלא',
            'blood_type': 'סוג דם',
            'phone': 'טלפון',
            'email': 'דוא"ל',
        }


class BloodDonationForm(forms.Form):
    """טופס קליטת תרומת דם"""
    donor_id_number = forms.CharField(
        max_length=9,
        label='תעודת זהות תורם',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123456789',
            'pattern': '[0-9]{9}',
            'dir': 'ltr'
        })
    )
    blood_type = forms.ChoiceField(
        choices=BloodType.choices,
        label='סוג דם',
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    donation_date = forms.DateField(
        label='תאריך תרומה',
        initial=date.today,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'dir': 'ltr'
        })
    )
    
    def clean_donor_id_number(self):
        id_number = self.cleaned_data['donor_id_number']
        if not id_number.isdigit() or len(id_number) != 9:
            raise forms.ValidationError('תעודת זהות חייבת להכיל 9 ספרות בדיוק')
        return id_number
    
    def clean_donation_date(self):
        donation_date = self.cleaned_data['donation_date']
        if donation_date > date.today():
            raise forms.ValidationError('תאריך תרומה לא יכול להיות בעתיד')
        return donation_date


class RoutineDispensationForm(forms.Form):
    """טופס ניפוק דם שגרתי"""
    blood_type = forms.ChoiceField(
        choices=BloodType.choices,
        label='סוג דם מבוקש',
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    quantity = forms.IntegerField(
        min_value=1,
        max_value=100,
        label='כמות מנות',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1',
            'dir': 'ltr'
        })
    )
    hospital_name = forms.CharField(
        max_length=200,
        label='שם בית חולים',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'בית חולים איכילוב',
            'dir': 'rtl'
        })
    )
    dispensed_by = forms.CharField(
        max_length=100,
        label='מי מנפק',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'שם הטכנאי',
            'dir': 'rtl'
        })
    )
    notes = forms.CharField(
        required=False,
        label='הערות',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'הערות נוספות (אופציונלי)',
            'dir': 'rtl'
        })
    )


class EmergencyDispensationForm(forms.Form):
    """טופס ניפוק דם לחירום (אר"ן)"""
    quantity = forms.IntegerField(
        min_value=1,
        max_value=500,
        label='כמות מנות O- נדרשת',
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '10',
            'dir': 'ltr',
            'style': 'font-size: 1.5rem; text-align: center;'
        })
    )
    dispensed_by = forms.CharField(
        max_length=100,
        label='מי מנפק',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'שם הטכנאי',
            'dir': 'rtl'
        })
    )
    notes = forms.CharField(
        required=False,
        label='פרטי האירוע',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'תיאור אירוע החירום',
            'dir': 'rtl'
        })
    )