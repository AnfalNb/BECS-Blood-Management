from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from .models import BloodDonation

# טבלאות תאימות
COMPATIBILITY = {
    'A+': {'donate_to': ['A+', 'AB+'], 'receive_from': ['A+', 'A-', 'O+', 'O-']},
    'O+': {'donate_to': ['O+', 'A+', 'B+', 'AB+'], 'receive_from': ['O+', 'O-']},
    'B+': {'donate_to': ['B+', 'AB+'], 'receive_from': ['B+', 'B-', 'O+', 'O-']},
    'AB+': {'donate_to': ['AB+'], 'receive_from': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']},
    'A-': {'donate_to': ['A+', 'A-', 'AB+', 'AB-'], 'receive_from': ['A-', 'O-']},
    'O-': {'donate_to': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'], 'receive_from': ['O-']},
    'B-': {'donate_to': ['B+', 'B-', 'AB+', 'AB-'], 'receive_from': ['B-', 'O-']},
    'AB-': {'donate_to': ['AB+', 'AB-'], 'receive_from': ['AB-', 'A-', 'B-', 'O-']},
}

# התפלגות נדירות (אחוז באוכלוסייה)
RARITY = {
    'O+': 32.0, 'A+': 34.0, 'B+': 17.0, 'AB+': 7.0,
    'O-': 3.0, 'A-': 4.0, 'B-': 2.0, 'AB-': 1.0
}

def index(request):
    return render(request, 'blood/index.html')

def donation_page(request):
    return render(request, 'blood/donation.html')

def dispense_page(request):
    return render(request, 'blood/dispense.html')

def emergency_page(request):
    return render(request, 'blood/emergency.html')

@csrf_exempt
@require_http_methods(["POST"])
def add_donation(request):
    try:
        data = json.loads(request.body)
        donation = BloodDonation.objects.create(
            blood_type=data['blood_type'],
            donation_date=datetime.strptime(data['donation_date'], '%Y-%m-%d').date(),
            donor_id=data['donor_id'],
            donor_name=data['donor_name']
        )
        return JsonResponse({
            'success': True,
            'message': 'התרומה נקלטה בהצלחה',
            'donation_id': donation.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def dispense_blood(request):
    try:
        data = json.loads(request.body)
        blood_type = data['blood_type']
        quantity = int(data['quantity'])
        
        available = BloodDonation.objects.filter(
            blood_type=blood_type,
            is_available=True
        ).count()
        
        if available >= quantity:
            units = BloodDonation.objects.filter(
                blood_type=blood_type,
                is_available=True
            )[:quantity]
            units.update(is_available=False)
            
            return JsonResponse({
                'success': True,
                'message': f'ניפוק הצליח: {quantity} מנות מסוג {blood_type}'
            })
        else:
            alternatives = find_alternatives(blood_type, quantity)
            return JsonResponse({
                'success': False,
                'available': available,
                'alternatives': alternatives,
                'message': f'מלאי לא מספיק. זמין: {available} מנות'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def emergency_dispense(request):
    try:
        available = BloodDonation.objects.filter(
            blood_type='O-',
            is_available=True
        ).count()
        
        if available == 0:
            return JsonResponse({
                'success': False,
                'message': 'שגיאה: אין מלאי זמין של O-'
            }, status=400)
        
        units = BloodDonation.objects.filter(
            blood_type='O-',
            is_available=True
        )
        units.update(is_available=False)
        
        return JsonResponse({
            'success': True,
            'quantity': available,
            'message': f'ניפוק חירום הצליח: {available} מנות O-'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

def get_inventory(request):
    inventory = {}
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        count = BloodDonation.objects.filter(
            blood_type=blood_type,
            is_available=True
        ).count()
        inventory[blood_type] = count
    return JsonResponse(inventory)

def find_alternatives(blood_type, quantity):
    alternatives = []
    donors = COMPATIBILITY[blood_type]['receive_from']
    
    for donor_type in donors:
        if donor_type != blood_type:
            available = BloodDonation.objects.filter(
                blood_type=donor_type,
                is_available=True
            ).count()
            
            if available >= quantity:
                alternatives.append({
                    'blood_type': donor_type,
                    'available': available,
                    'rarity': RARITY[donor_type]
                })
    
    alternatives.sort(key=lambda x: x['rarity'], reverse=True)
    return alternatives
