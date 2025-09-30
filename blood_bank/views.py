# ================= views.py - קוד מלא =================
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import json
from datetime import datetime
from .models import BloodDonation, AuditLog, CustomUser
import csv
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

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

RARITY = {
    'O+': 32.0, 'A+': 34.0, 'B+': 17.0, 'AB+': 7.0,
    'O-': 3.0, 'A-': 4.0, 'B-': 2.0, 'AB-': 1.0
}

# פונקציות הרשאות
def is_admin(user):
    return user.is_authenticated and user.is_admin()

def is_user_or_admin(user):
    return user.is_authenticated and (user.is_user() or user.is_admin())

def is_researcher_or_admin(user):
    return user.is_authenticated and (user.is_researcher() or user.is_admin())

# פונקציית Audit Log
def log_audit(action, details, blood_type=None, quantity=None, success=True, request=None, user=None):
    ip = None
    username = 'anonymous'
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        if request.user.is_authenticated:
            username = request.user.username
    
    if user:
        username = user.username
    
    AuditLog.objects.create(
        action=action,
        user=username,
        details=details,
        blood_type=blood_type,
        quantity=quantity,
        ip_address=ip,
        success=success
    )

# ============= Login/Logout =============

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            log_audit('USER_LOGIN', f'התחברות: {username}', request=request, user=user)
            messages.success(request, f'ברוך הבא, {user.username}!')
            return redirect('index')
        else:
            log_audit('USER_LOGIN', f'התחברות נכשלה: {username}', success=False, request=request)
            messages.error(request, 'שם משתמש או סיסמה שגויים')
    
    return render(request, 'blood/login.html')

@login_required
def logout_view(request):
    username = request.user.username
    logout(request)
    log_audit('USER_LOGOUT', f'התנתקות: {username}', request=request)
    messages.info(request, 'התנתקת בהצלחה')
    return redirect('login')

# ============= Main Pages =============

# החלף את הפונקציה index הקיימת:
def index(request):
    """דף בית - מנתב לפי סטטוס משתמש"""
    if not request.user.is_authenticated:
        # משתמש לא מחובר - דף בית ציבורי
        return render(request, 'blood/public_home.html')
    
    # משתמש מחובר - נתב לפי תפקיד
    log_audit('RECORD_VIEWED', 'גישה לעמוד הבית', request=request)
    
    if request.user.is_admin():
        return render(request, 'blood/admin_home.html')
    elif request.user.is_user():
        return render(request, 'blood/user_home.html')
    elif request.user.is_researcher():
        return render(request, 'blood/researcher_home.html')
    else:
        return render(request, 'blood/user_home.html')

@login_required
@user_passes_test(is_user_or_admin)
def donation_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד קליטת תרומות', request=request)
    return render(request, 'blood/donation.html')

@login_required
@user_passes_test(is_user_or_admin)
def dispense_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד ניפוק דם', request=request)
    return render(request, 'blood/dispense.html')

@login_required
@user_passes_test(is_user_or_admin)
def emergency_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד ניפוק חירום', request=request)
    return render(request, 'blood/emergency.html')

@login_required
def audit_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד Audit Trail', request=request)
    return render(request, 'blood/audit.html')

@login_required
def export_page(request):
    log_audit('RECORD_VIEWED', 'גישה לעמוד יצוא נתונים', request=request)
    return render(request, 'blood/export.html')

@login_required
@user_passes_test(is_admin)
def admin_users_page(request):
    log_audit('RECORD_VIEWED', 'גישה לניהול משתמשים', request=request)
    return render(request, 'blood/admin_users.html')

@login_required
@user_passes_test(is_researcher_or_admin)
def research_page(request):
    log_audit('RECORD_VIEWED', 'גישה למחקר', request=request)
    return render(request, 'blood/research.html')

# ============= API Endpoints - Blood Operations =============

@login_required
@user_passes_test(is_user_or_admin)
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

@login_required
@user_passes_test(is_user_or_admin)
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
                f"ניפוק נכשל - מלאי לא מספיק: {blood_type}",
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
        log_audit('BLOOD_DISPENSED', f"שגיאה: {str(e)}", success=False, request=request)
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@user_passes_test(is_user_or_admin)
@csrf_exempt
@require_http_methods(["POST"])
def emergency_dispense(request):
    try:
        available = BloodDonation.objects.filter(
            blood_type='O-',
            is_available=True
        ).count()
        
        if available == 0:
            log_audit('EMERGENCY_DISPENSED', 'נכשל - אין מלאי O-', blood_type='O-', success=False, request=request)
            return JsonResponse({'success': False, 'message': 'אין מלאי O-'}, status=400)
        
        units = BloodDonation.objects.filter(blood_type='O-', is_available=True)
        units.update(is_available=False)
        
        log_audit('EMERGENCY_DISPENSED', f'ניפוק חירום: {available} מנות O-', blood_type='O-', quantity=available, request=request)
        
        return JsonResponse({
            'success': True,
            'quantity': available,
            'message': f'ניפוק חירום: {available} מנות O-'
        })
    except Exception as e:
        log_audit('EMERGENCY_DISPENSED', f"שגיאה: {str(e)}", success=False, request=request)
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
def get_inventory(request):
    inventory = {}
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        count = BloodDonation.objects.filter(
            blood_type=blood_type,
            is_available=True
        ).count()
        inventory[blood_type] = count
    
    log_audit('INVENTORY_CHECKED', 'בדיקת מלאי', request=request)
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

# ============= Audit Trail =============

@login_required
def get_audit_logs(request):
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
        'user': log.user,
        'details': log.details,
        'blood_type': log.blood_type or '-',
        'quantity': log.quantity or '-',
        'success': log.success,
        'ip_address': log.ip_address or '-'
    } for log in logs]
    
    return JsonResponse({'logs': data})

# ============= HIPAA - De-identified Data =============

@login_required
@user_passes_test(is_researcher_or_admin)
def get_deidentified_data(request):
    donations = BloodDonation.objects.all()
    data = []
    for i, d in enumerate(donations, 1):
        data.append({
            'record_id': f'REC-{i:05d}',
            'blood_type': d.blood_type,
            'donation_month': d.donation_date.strftime('%Y-%m'),
            'is_available': d.is_available,
        })
    log_audit('DATA_VIEWED', f'צפייה בנתונים מוסווים: {len(data)}', request=request)
    return JsonResponse({'data': data})

# ============= Admin - User Management =============

@login_required
@user_passes_test(is_admin)
def get_users(request):
    users = CustomUser.objects.all().order_by('-date_joined')
    data = [{
        'id': u.id,
        'username': u.username,
        'full_name': u.get_full_name() or '-',
        'email': u.email,
        'role': u.get_role_display(),
        'is_active': u.is_active,
        'date_joined': u.date_joined.strftime('%Y-%m-%d')
    } for u in users]
    return JsonResponse({'users': data})

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def create_user(request):
    try:
        data = json.loads(request.body)
        user = CustomUser.objects.create_user(
            username=data['username'],
            password=data['password'],
            email=data.get('email', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            role=data['role']
        )
        log_audit('USER_CREATED', f'משתמש נוצר: {user.username}', request=request)
        return JsonResponse({'success': True, 'message': f'משתמש {user.username} נוצר'})
    except Exception as e:
        log_audit('USER_CREATED', f'שגיאה: {str(e)}', success=False, request=request)
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

# ============= Export - CSV =============

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def export_donations_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="blood_donations_full.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Blood Type', 'Date', 'Donor ID', 'Donor Name', 'Available'])
    
    donations = BloodDonation.objects.all().order_by('-donation_date')
    for d in donations:
        writer.writerow([d.id, d.blood_type, d.donation_date, d.donor_id, d.donor_name, 'Yes' if d.is_available else 'No'])
    
    log_audit('DATA_EXPORTED', f'יצוא מלא: {donations.count()}', request=request)
    return response

@login_required
@require_http_methods(["GET"])
def export_audit_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Time', 'Action', 'User', 'Details', 'Blood Type', 'Quantity', 'Success', 'IP'])
    
    logs = AuditLog.objects.all().order_by('-timestamp')
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.get_action_display(),
            log.user,
            log.details,
            log.blood_type or '-',
            log.quantity or '-',
            'Yes' if log.success else 'No',
            log.ip_address or '-'
        ])
    
    log_audit('DATA_EXPORTED', f'יצוא Audit: {logs.count()}', request=request)
    return response

@login_required
@user_passes_test(is_researcher_or_admin)
@require_http_methods(["GET"])
def export_deidentified_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="blood_donations_deidentified.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Record ID', 'Blood Type', 'Month', 'Available'])
    
    donations = BloodDonation.objects.all().order_by('-donation_date')
    for i, d in enumerate(donations, 1):
        writer.writerow([f'REC-{i:05d}', d.blood_type, d.donation_date.strftime('%Y-%m'), 'Yes' if d.is_available else 'No'])
    
    log_audit('DATA_EXPORTED', f'יצוא מוסווה: {donations.count()}', request=request)
    return response

# ============= Export - PDF =============

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def export_donations_pdf(request):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
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
    
    donations = BloodDonation.objects.all().order_by('-donation_date')[:100]
    
    data = [['ID', 'Type', 'Date', 'Donor ID', 'Name', 'Available']]
    for d in donations:
        data.append([
            str(d.id),
            d.blood_type,
            d.donation_date.strftime('%Y-%m-%d'),
            d.donor_id,
            d.donor_name[:20],
            'Yes' if d.is_available else 'No'
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c62828')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    
    log_audit('DATA_EXPORTED', f'יצוא PDF: {donations.count()}', request=request)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="blood_donations.pdf"'
    return response

@login_required
@require_http_methods(["GET"])
def export_audit_pdf(request):
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
    
    data = [['ID', 'Time', 'User', 'Action', 'Details']]
    for log in logs:
        data.append([
            str(log.id),
            log.timestamp.strftime('%Y-%m-%d %H:%M'),
            log.user[:15],
            log.get_action_display()[:20],
            log.details[:30]
        ])
    
    table = Table(data, colWidths=[30, 80, 70, 100, 130])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    
    log_audit('DATA_EXPORTED', f'יצוא PDF Audit: {logs.count()}', request=request)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.pdf"'
    return response