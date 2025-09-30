# from django.shortcuts import render
# from django.http import JsonResponse
# from django.views.decorators.http import require_http_methods
# from django.views.decorators.csrf import csrf_exempt
# import json
# from datetime import datetime
# from .models import BloodDonation

# # טבלאות תאימות
# COMPATIBILITY = {
#     'A+': {'donate_to': ['A+', 'AB+'], 'receive_from': ['A+', 'A-', 'O+', 'O-']},
#     'O+': {'donate_to': ['O+', 'A+', 'B+', 'AB+'], 'receive_from': ['O+', 'O-']},
#     'B+': {'donate_to': ['B+', 'AB+'], 'receive_from': ['B+', 'B-', 'O+', 'O-']},
#     'AB+': {'donate_to': ['AB+'], 'receive_from': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']},
#     'A-': {'donate_to': ['A+', 'A-', 'AB+', 'AB-'], 'receive_from': ['A-', 'O-']},
#     'O-': {'donate_to': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'], 'receive_from': ['O-']},
#     'B-': {'donate_to': ['B+', 'B-', 'AB+', 'AB-'], 'receive_from': ['B-', 'O-']},
#     'AB-': {'donate_to': ['AB+', 'AB-'], 'receive_from': ['AB-', 'A-', 'B-', 'O-']},
# }

# # התפלגות נדירות (אחוז באוכלוסייה)
# RARITY = {
#     'O+': 32.0, 'A+': 34.0, 'B+': 17.0, 'AB+': 7.0,
#     'O-': 3.0, 'A-': 4.0, 'B-': 2.0, 'AB-': 1.0
# }

# def index(request):
#     return render(request, 'blood/index.html')

# def donation_page(request):
#     return render(request, 'blood/donation.html')

# def dispense_page(request):
#     return render(request, 'blood/dispense.html')

# def emergency_page(request):
#     return render(request, 'blood/emergency.html')

# @csrf_exempt
# @require_http_methods(["POST"])
# def add_donation(request):
#     try:
#         data = json.loads(request.body)
#         donation = BloodDonation.objects.create(
#             blood_type=data['blood_type'],
#             donation_date=datetime.strptime(data['donation_date'], '%Y-%m-%d').date(),
#             donor_id=data['donor_id'],
#             donor_name=data['donor_name']
#         )
#         return JsonResponse({
#             'success': True,
#             'message': 'התרומה נקלטה בהצלחה',
#             'donation_id': donation.id
#         })
#     except Exception as e:
#         return JsonResponse({'success': False, 'message': str(e)}, status=400)

# @csrf_exempt
# @require_http_methods(["POST"])
# def dispense_blood(request):
#     try:
#         data = json.loads(request.body)
#         blood_type = data['blood_type']
#         quantity = int(data['quantity'])
        
#         available = BloodDonation.objects.filter(
#             blood_type=blood_type,
#             is_available=True
#         ).count()
        
#         if available >= quantity:
#             units = BloodDonation.objects.filter(
#                 blood_type=blood_type,
#                 is_available=True
#             )[:quantity]
#             units.update(is_available=False)
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'ניפוק הצליח: {quantity} מנות מסוג {blood_type}'
#             })
#         else:
#             alternatives = find_alternatives(blood_type, quantity)
#             return JsonResponse({
#                 'success': False,
#                 'available': available,
#                 'alternatives': alternatives,
#                 'message': f'מלאי לא מספיק. זמין: {available} מנות'
#             })
#     except Exception as e:
#         return JsonResponse({'success': False, 'message': str(e)}, status=400)

# @csrf_exempt
# @require_http_methods(["POST"])
# def emergency_dispense(request):
#     try:
#         available = BloodDonation.objects.filter(
#             blood_type='O-',
#             is_available=True
#         ).count()
        
#         if available == 0:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'שגיאה: אין מלאי זמין של O-'
#             }, status=400)
        
#         units = BloodDonation.objects.filter(
#             blood_type='O-',
#             is_available=True
#         )
#         units.update(is_available=False)
        
#         return JsonResponse({
#             'success': True,
#             'quantity': available,
#             'message': f'ניפוק חירום הצליח: {available} מנות O-'
#         })
#     except Exception as e:
#         return JsonResponse({'success': False, 'message': str(e)}, status=400)

# def get_inventory(request):
#     inventory = {}
#     for blood_type, _ in BloodDonation.BLOOD_TYPES:
#         count = BloodDonation.objects.filter(
#             blood_type=blood_type,
#             is_available=True
#         ).count()
#         inventory[blood_type] = count
#     return JsonResponse(inventory)

# def find_alternatives(blood_type, quantity):
#     alternatives = []
#     donors = COMPATIBILITY[blood_type]['receive_from']
    
#     for donor_type in donors:
#         if donor_type != blood_type:
#             available = BloodDonation.objects.filter(
#                 blood_type=donor_type,
#                 is_available=True
#             ).count()
            
#             if available >= quantity:
#                 alternatives.append({
#                     'blood_type': donor_type,
#                     'available': available,
#                     'rarity': RARITY[donor_type]
#                 })
    
#     alternatives.sort(key=lambda x: x['rarity'], reverse=True)
#     return alternatives




from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from .models import BloodDonation, AuditLog
import csv
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

# טבלאות תאימות - נשארות כמו קודם
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

RARITY = {
    'O+': 32.0, 'A+': 34.0, 'B+': 17.0, 'AB+': 7.0,
    'O-': 3.0, 'A-': 4.0, 'B-': 2.0, 'AB-': 1.0
}

# פונקציה לרישום Audit Log
def log_audit(action, details, blood_type=None, quantity=None, success=True, request=None):
    """רישום פעילות ב-Audit Trail"""
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
    
    AuditLog.objects.create(
        action=action,
        details=details,
        blood_type=blood_type,
        quantity=quantity,
        ip_address=ip,
        success=success
    )

# Views הקיימים - עם תוספת Audit Trail

def index(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד הבית', request=request)
    return render(request, 'blood/index.html')

def donation_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד קליטת תרומות', request=request)
    return render(request, 'blood/donation.html')

def dispense_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד ניפוק דם', request=request)
    return render(request, 'blood/dispense.html')

def emergency_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד ניפוק חירום', request=request)
    return render(request, 'blood/emergency.html')

def audit_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד Audit Trail', request=request)
    return render(request, 'blood/audit.html')

def export_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד יצוא נתונים', request=request)
    return render(request, 'blood/export.html')

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
        
        # Audit Log
        log_audit(
            'DONATION_ADDED',
            f"תרומה נוספה: {data['donor_name']} (ת\"ז: {data['donor_id']})",
            blood_type=data['blood_type'],
            quantity=1,
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'התרומה נקלטה בהצלחה',
            'donation_id': donation.id
        })
    except Exception as e:
        log_audit(
            'DONATION_ADDED',
            f"שגיאה בקליטת תרומה: {str(e)}",
            success=False,
            request=request
        )
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
            
            # Audit Log
            log_audit(
                'BLOOD_DISPENSED',
                f"ניפוק הצליח: {quantity} מנות מסוג {blood_type}",
                blood_type=blood_type,
                quantity=quantity,
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'message': f'ניפוק הצליח: {quantity} מנות מסוג {blood_type}'
            })
        else:
            alternatives = find_alternatives(blood_type, quantity)
            
            log_audit(
                'BLOOD_DISPENSED',
                f"ניפוק נכשל - מלאי לא מספיק: {blood_type}, מבוקש: {quantity}, זמין: {available}",
                blood_type=blood_type,
                quantity=quantity,
                success=False,
                request=request
            )
            
            return JsonResponse({
                'success': False,
                'available': available,
                'alternatives': alternatives,
                'message': f'מלאי לא מספיק. זמין: {available} מנות'
            })
    except Exception as e:
        log_audit(
            'BLOOD_DISPENSED',
            f"שגיאה בניפוק: {str(e)}",
            success=False,
            request=request
        )
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
            log_audit(
                'EMERGENCY_DISPENSED',
                'ניפוק חירום נכשל - אין מלאי O-',
                blood_type='O-',
                quantity=0,
                success=False,
                request=request
            )
            return JsonResponse({
                'success': False,
                'message': 'שגיאה: אין מלאי זמין של O-'
            }, status=400)
        
        units = BloodDonation.objects.filter(
            blood_type='O-',
            is_available=True
        )
        units.update(is_available=False)
        
        # Audit Log
        log_audit(
            'EMERGENCY_DISPENSED',
            f'ניפוק חירום - אר"ן: {available} מנות O-',
            blood_type='O-',
            quantity=available,
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'quantity': available,
            'message': f'ניפוק חירום הצליח: {available} מנות O-'
        })
    except Exception as e:
        log_audit(
            'EMERGENCY_DISPENSED',
            f"שגיאה בניפוק חירום: {str(e)}",
            success=False,
            request=request
        )
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

def get_inventory(request):
    inventory = {}
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        count = BloodDonation.objects.filter(
            blood_type=blood_type,
            is_available=True
        ).count()
        inventory[blood_type] = count
    
    log_audit(
        'INVENTORY_CHECKED',
        'בדיקת מלאי',
        request=request
    )
    
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


# ============= API חדש - Audit Trail =============

def get_audit_logs(request):
    """החזרת לוגים לממשק"""
    limit = int(request.GET.get('limit', 100))
    action_filter = request.GET.get('action', '')
    
    logs = AuditLog.objects.all()
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    logs = logs[:limit]
    
    data = [{
        'id': log.id,
        'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'action': log.get_action_display(),
        'details': log.details,
        'blood_type': log.blood_type or '-',
        'quantity': log.quantity or '-',
        'success': log.success,
        'ip_address': log.ip_address or '-'
    } for log in logs]
    
    return JsonResponse({'logs': data})

# ============= יצוא נתונים - CSV =============

@require_http_methods(["GET"])
def export_donations_csv(request):
    """יצוא תרומות ל-CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="blood_donations.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['מזהה', 'סוג דם', 'תאריך תרומה', 'תעודת זהות', 'שם תורם', 'זמין'])
    
    donations = BloodDonation.objects.all().order_by('-donation_date')
    for d in donations:
        writer.writerow([
            d.id,
            d.blood_type,
            d.donation_date.strftime('%Y-%m-%d'),
            d.donor_id,
            d.donor_name,
            'כן' if d.is_available else 'לא'
        ])
    
    log_audit(
        'DATA_EXPORTED',
        f'יצוא תרומות ל-CSV: {donations.count()} רשומות',
        request=request
    )
    
    return response

@require_http_methods(["GET"])
def export_audit_csv(request):
    """יצוא Audit Logs ל-CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['מזהה', 'זמן', 'פעולה', 'פרטים', 'סוג דם', 'כמות', 'הצלחה', 'IP'])
    
    logs = AuditLog.objects.all().order_by('-timestamp')
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.get_action_display(),
            log.details,
            log.blood_type or '-',
            log.quantity or '-',
            'כן' if log.success else 'לא',
            log.ip_address or '-'
        ])
    
    log_audit(
        'DATA_EXPORTED',
        f'יצוא Audit Logs ל-CSV: {logs.count()} רשומות',
        request=request
    )
    
    return response

# ============= יצוא נתונים - PDF =============

@require_http_methods(["GET"])
def export_donations_pdf(request):
    """יצוא תרומות ל-PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # כותרת
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#c62828'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    elements.append(Paragraph('BECS - Blood Donations Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # טבלה
    donations = BloodDonation.objects.all().order_by('-donation_date')[:100]
    
    data = [['ID', 'Blood Type', 'Date', 'Donor ID', 'Donor Name', 'Available']]
    
    for d in donations:
        data.append([
            str(d.id),
            d.blood_type,
            d.donation_date.strftime('%Y-%m-%d'),
            d.donor_id,
            d.donor_name,
            'Yes' if d.is_available else 'No'
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c62828')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    
    log_audit(
        'DATA_EXPORTED',
        f'יצוא תרומות ל-PDF: {donations.count()} רשומות',
        request=request
    )
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="blood_donations.pdf"'
    
    return response

@require_http_methods(["GET"])
def export_audit_pdf(request):
    """יצוא Audit Logs ל-PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1565c0'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    elements.append(Paragraph('BECS - Audit Trail Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    logs = AuditLog.objects.all().order_by('-timestamp')[:100]
    
    data = [['ID', 'Time', 'Action', 'Details', 'Success']]
    
    for log in logs:
        data.append([
            str(log.id),
            log.timestamp.strftime('%Y-%m-%d %H:%M'),
            log.get_action_display()[:20],
            log.details[:30],
            'Yes' if log.success else 'No'
        ])
    
    table = Table(data, colWidths=[30, 80, 100, 150, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    
    log_audit(
        'DATA_EXPORTED',
        f'יצוא Audit Logs ל-PDF: {logs.count()} רשומות',
        request=request
    )
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.pdf"'
    
    return response