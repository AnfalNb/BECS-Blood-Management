from django.db import transaction
from django.db.models import Count, Q
from .models import (
    BloodUnit, Dispensation, CompatibilityRule, 
    BloodTypeDistribution, InventoryLog, Donor
)

class BloodBankManager:
    """מנהל מרכזי לכל פעולות בנק הדם"""
    
    # מטריצת תאימות מובנית
    COMPATIBILITY_MATRIX = {
        'O-': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
        'O+': ['O+', 'A+', 'B+', 'AB+'],
        'A-': ['A-', 'A+', 'AB-', 'AB+'],
        'A+': ['A+', 'AB+'],
        'B-': ['B-', 'B+', 'AB-', 'AB+'],
        'B+': ['B+', 'AB+'],
        'AB-': ['AB-', 'AB+'],
        'AB+': ['AB+'],
    }
    
    @classmethod
    def initialize_compatibility_rules(cls):
        """אתחול כללי תאימות במסד הנתונים"""
        CompatibilityRule.objects.all().delete()
        rules = []
        for donor_type, recipients in cls.COMPATIBILITY_MATRIX.items():
            for recipient_type in recipients:
                rules.append(
                    CompatibilityRule(
                        donor_type=donor_type,
                        recipient_type=recipient_type
                    )
                )
        CompatibilityRule.objects.bulk_create(rules)
    
    @classmethod
    def initialize_distribution_data(cls):
        """אתחול נתוני התפלגות סוגי דם באוכלוסייה הישראלית"""
        distributions = [
            ('O+', 32.0),
            ('A+', 34.0),
            ('B+', 17.0),
            ('AB+', 7.0),
            ('O-', 3.0),
            ('A-', 4.0),
            ('B-', 2.0),
            ('AB-', 1.0),
        ]
        BloodTypeDistribution.objects.all().delete()
        for blood_type, percentage in distributions:
            BloodTypeDistribution.objects.create(
                blood_type=blood_type,
                percentage=percentage
            )
    
    @classmethod
    def get_compatible_donors(cls, recipient_blood_type):
        """החזרת כל סוגי הדם התואמים למטופל"""
        rules = CompatibilityRule.objects.filter(
            recipient_type=recipient_blood_type
        ).values_list('donor_type', flat=True)
        return list(rules)
    
    @classmethod
    def get_inventory_status(cls):
        """סטטוס מלאי נוכחי לפי סוג דם"""
        inventory = BloodUnit.objects.filter(
            status='available'
        ).values('blood_type').annotate(
            count=Count('id')
        ).order_by('blood_type')
        
        result = {}
        for item in inventory:
            result[item['blood_type']] = item['count']
        
        # הוספת סוגי דם עם 0 מנות
        from .models import BloodType
        for blood_type in BloodType.values:
            if blood_type not in result:
                result[blood_type] = 0
        
        return result
    
    @classmethod
    def get_alternative_blood_type(cls, requested_type):
        """
        מציאת סוג דם חלופי מיטבי כאשר הסוג המבוקש אזל
        לפי סדר עדיפות: תאימות + זמינות + נדירות (ככל שפחות נדיר - עדיף)
        """
        compatible_types = cls.get_compatible_donors(requested_type)
        inventory = cls.get_inventory_status()
        
        # סינון רק סוגים זמינים
        available_types = [
            bt for bt in compatible_types 
            if inventory.get(bt, 0) > 0
        ]
        
        if not available_types:
            return None
        
        # אם יש רק אופציה אחת
        if len(available_types) == 1:
            return available_types[0]
        
        # מיון לפי נדירות (העדפה לפחות נדירים)
        distributions = BloodTypeDistribution.objects.filter(
            blood_type__in=available_types
        ).order_by('-percentage')  # מהנפוץ לנדיר
        
        if distributions.exists():
            return distributions.first().blood_type
        
        return available_types[0]
    
    @classmethod
    @transaction.atomic
    def donate_blood(cls, donor_id, blood_type, donation_date, user='System'):
        """קליטת תרומת דם חדשה"""
        try:
            donor = Donor.objects.get(id=donor_id)
        except Donor.DoesNotExist:
            raise ValueError("תורם לא נמצא במערכת")
        
        # יצירת מנת דם חדשה
        blood_unit = BloodUnit.objects.create(
            donor=donor,
            blood_type=blood_type,
            donation_date=donation_date,
            status='available'
        )
        
        # רישום בלוג
        InventoryLog.objects.create(
            blood_type=blood_type,
            action='donation',
            quantity_change=1,
            blood_unit=blood_unit,
            notes=f'תרומה מ-{donor.full_name}',
            user=user
        )
        
        return blood_unit
    
    @classmethod
    @transaction.atomic
    def dispense_routine(cls, requested_type, quantity, hospital_name, 
                        dispensed_by, notes=''):
        """
        ניפוק דם בשגרה
        מחזיר: (Dispensation object, success_message או error_message)
        """
        inventory = cls.get_inventory_status()
        actual_type = requested_type
        units_to_dispense = []
        
        # בדיקת זמינות
        if inventory.get(requested_type, 0) >= quantity:
            # יש מספיק מהסוג המבוקש
            units_to_dispense = BloodUnit.objects.filter(
                blood_type=requested_type,
                status='available'
            ).order_by('donation_date', 'created_at')[:quantity]
        else:
            # לא מספיק - חיפוש חלופה
            alternative = cls.get_alternative_blood_type(requested_type)
            
            if alternative and inventory.get(alternative, 0) >= quantity:
                actual_type = alternative
                units_to_dispense = BloodUnit.objects.filter(
                    blood_type=alternative,
                    status='available'
                ).order_by('donation_date', 'created_at')[:quantity]
            else:
                # אין מספיק מנות זמינות
                return None, f"אין מספיק מנות זמינות. מבוקש: {quantity}, זמין: {inventory.get(requested_type, 0)}"
        
        # יצירת רישום ניפוק
        dispensation = Dispensation.objects.create(
            dispensation_type='routine',
            requested_blood_type=requested_type,
            units_requested=quantity,
            units_dispensed=len(units_to_dispense),
            alternative_type_used=actual_type if actual_type != requested_type else None,
            hospital_name=hospital_name,
            notes=notes,
            dispensed_by=dispensed_by
        )
        
        # עדכון מנות הדם וקישור לניפוק
        for unit in units_to_dispense:
            unit.status = 'dispensed'
            unit.save()
            dispensation.blood_units.add(unit)
        
        # רישום בלוג
        InventoryLog.objects.create(
            blood_type=actual_type,
            action='dispensation',
            quantity_change=-len(units_to_dispense),
            dispensation=dispensation,
            notes=f'ניפוק שגרה ל-{hospital_name}',
            user=dispensed_by
        )
        
        message = f"נופקו {len(units_to_dispense)} מנות מסוג {actual_type}"
        if actual_type != requested_type:
            message += f" (במקום {requested_type} שאזל)"
        
        return dispensation, message
    
    @classmethod
    @transaction.atomic
    def dispense_emergency(cls, quantity, dispensed_by, notes=''):
        """
        ניפוק דם לחירום (אר"ן) - רק O-
        מחזיר: (Dispensation object, message) או (None, error_message)
        """
        inventory = cls.get_inventory_status()
        o_neg_available = inventory.get('O-', 0)
        
        if o_neg_available < quantity:
            return None, f"שגיאה: לא מספיק מנות O- זמינות! זמין: {o_neg_available}, מבוקש: {quantity}"
        
        # שליפת המנות הנדרשות (FIFO)
        units_to_dispense = BloodUnit.objects.filter(
            blood_type='O-',
            status='available'
        ).order_by('donation_date', 'created_at')[:quantity]
        
        # יצירת רישום ניפוק חירום
        dispensation = Dispensation.objects.create(
            dispensation_type='emergency',
            requested_blood_type='O-',
            units_requested=quantity,
            units_dispensed=len(units_to_dispense),
            hospital_name='אר"ן - חירום',
            notes=f'חירום! {notes}',
            dispensed_by=dispensed_by
        )
        
        # עדכון מנות
        for unit in units_to_dispense:
            unit.status = 'dispensed'
            unit.save()
            dispensation.blood_units.add(unit)
        
        # רישום בלוג
        InventoryLog.objects.create(
            blood_type='O-',
            action='dispensation',
            quantity_change=-len(units_to_dispense),
            dispensation=dispensation,
            notes=f'ניפוק חירום אר"ן',
            user=dispensed_by
        )
        
        remaining = o_neg_available - quantity
        message = f"נופקו {quantity} מנות O- לחירום. נותרו {remaining} מנות במלאי"
        
        return dispensation, message
    
    @classmethod
    def get_critical_inventory_alert(cls):
        """התראות על מלאי קריטי"""
        alerts = []
        inventory = cls.get_inventory_status()
        
        # O- קריטי - מתחת ל-10 מנות
        if inventory.get('O-', 0) < 10:
            alerts.append({
                'level': 'critical',
                'blood_type': 'O-',
                'count': inventory.get('O-', 0),
                'message': f'מלאי קריטי של O-! נותרו רק {inventory.get("O-", 0)} מנות'
            })
        
        # סוגי דם נדירים אחרים - מתחת ל-5 מנות
        rare_types = ['AB-', 'B-', 'A-']
        for blood_type in rare_types:
            count = inventory.get(blood_type, 0)
            if count < 5:
                alerts.append({
                    'level': 'warning',
                    'blood_type': blood_type,
                    'count': count,
                    'message': f'מלאי נמוך של {blood_type}: {count} מנות'
                })
        
        return alerts