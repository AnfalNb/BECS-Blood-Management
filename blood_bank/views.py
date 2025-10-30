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

from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime, timedelta

from datetime import date, timedelta


from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncDate
from datetime import datetime, timedelta
from collections import defaultdict


from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import inch
import matplotlib
matplotlib.use('Agg')  # בשביל שרת
import matplotlib.pyplot as plt
import base64


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




@login_required
@user_passes_test(is_user_or_admin)
def donations_list(request):
    """רשימת כל התרומות עם חיפוש וסינון"""
    log_audit('RECORD_VIEWED', 'גישה לרשימת תרומות', request=request)
    return render(request, 'blood/donations_list.html')

@login_required
@user_passes_test(is_user_or_admin)
def search_donations(request):
    """API לחיפוש תרומות"""
    # פרמטרים מהבקשה
    search_query = request.GET.get('search', '').strip()
    blood_type_filter = request.GET.get('blood_type', '')
    availability_filter = request.GET.get('availability', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sort_by = request.GET.get('sort_by', '-donation_date')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    
    # בניית שאילתה
    donations = BloodDonation.objects.all()
    
    # חיפוש טקסט חופשי
    if search_query:
        donations = donations.filter(
            Q(donor_name__icontains=search_query) |
            Q(donor_id__icontains=search_query) |
            Q(blood_type__icontains=search_query)
        )
    
    # סינון לפי סוג דם
    if blood_type_filter:
        donations = donations.filter(blood_type=blood_type_filter)
    
    # סינון לפי זמינות
    if availability_filter:
        is_available = availability_filter == 'available'
        donations = donations.filter(is_available=is_available)
    
    # סינון לפי תאריכים
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            donations = donations.filter(donation_date__gte=date_from_obj)
        except:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            donations = donations.filter(donation_date__lte=date_to_obj)
        except:
            pass
    
    # מיון
    donations = donations.order_by(sort_by)
    
    # ספירה לפני pagination
    total_count = donations.count()
    
    # Pagination
    paginator = Paginator(donations, per_page)
    page_obj = paginator.get_page(page)
    
    # המרה ל-JSON
    data = [{
        'id': d.id,
        'blood_type': d.blood_type,
        'donation_date': d.donation_date.strftime('%Y-%m-%d'),
        'donor_id': d.donor_id,
        'donor_name': d.donor_name,
        'is_available': d.is_available,
    } for d in page_obj]
    
    log_audit(
        'SEARCH_PERFORMED',
        f'חיפוש תרומות: "{search_query}" - {total_count} תוצאות',
        request=request
    )
    
    return JsonResponse({
        'donations': data,
        'total': total_count,
        'page': page,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })

@login_required
@user_passes_test(is_user_or_admin)
def export_search_results(request):
    """יצוא תוצאות חיפוש ל-CSV"""
    # אותם פרמטרים כמו בחיפוש
    search_query = request.GET.get('search', '').strip()
    blood_type_filter = request.GET.get('blood_type', '')
    availability_filter = request.GET.get('availability', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # בניית שאילתה זהה
    donations = BloodDonation.objects.all()
    
    if search_query:
        donations = donations.filter(
            Q(donor_name__icontains=search_query) |
            Q(donor_id__icontains=search_query) |
            Q(blood_type__icontains=search_query)
        )
    
    if blood_type_filter:
        donations = donations.filter(blood_type=blood_type_filter)
    
    if availability_filter:
        is_available = availability_filter == 'available'
        donations = donations.filter(is_available=is_available)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            donations = donations.filter(donation_date__gte=date_from_obj)
        except:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            donations = donations.filter(donation_date__lte=date_to_obj)
        except:
            pass
    
    donations = donations.order_by('-donation_date')
    
    # יצירת CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="donations_search_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Blood Type', 'Date', 'Donor ID', 'Donor Name', 'Available'])
    
    for d in donations:
        writer.writerow([
            d.id,
            d.blood_type,
            d.donation_date.strftime('%Y-%m-%d'),
            d.donor_id,
            d.donor_name,
            'Yes' if d.is_available else 'No'
        ])
    
    log_audit(
        'DATA_EXPORTED',
        f'יצוא תוצאות חיפוש: {donations.count()} רשומות',
        request=request
    )
    
    return response





@login_required
@user_passes_test(is_user_or_admin)
def expiration_tracking(request):
    """דף מעקב תוקף מנות דם"""
    log_audit('RECORD_VIEWED', 'גישה למעקב תוקף מנות', request=request)
    return render(request, 'blood/expiration_tracking.html')

@login_required
@user_passes_test(is_user_or_admin)
def get_expiration_data(request):
    """API - נתוני תפוגה"""
    today = date.today()
    
    # מנות זמינות בלבד
    available_donations = BloodDonation.objects.filter(is_available=True)
    
    # קטגוריות
    expired = available_donations.filter(expiration_date__lt=today)
    expiring_soon = available_donations.filter(
        expiration_date__gte=today,
        expiration_date__lte=today + timedelta(days=7)
    )
    expiring_medium = available_donations.filter(
        expiration_date__gt=today + timedelta(days=7),
        expiration_date__lte=today + timedelta(days=14)
    )
    ok = available_donations.filter(expiration_date__gt=today + timedelta(days=14))
    
    # סטטיסטיקות
    stats = {
        'total_available': available_donations.count(),
        'expired': expired.count(),
        'expiring_soon': expiring_soon.count(),
        'expiring_medium': expiring_medium.count(),
        'ok': ok.count()
    }
    
    # מנות פגות - מפורט
    expired_list = [{
        'id': d.id,
        'blood_type': d.blood_type,
        'donation_date': d.donation_date.strftime('%Y-%m-%d'),
        'expiration_date': d.expiration_date.strftime('%Y-%m-%d'),
        'donor_name': d.donor_name,
        'days_expired': abs(d.days_until_expiry())
    } for d in expired.order_by('expiration_date')]
    
    # מנות שתפוגתן מתקרבת - מפורט
    expiring_list = [{
        'id': d.id,
        'blood_type': d.blood_type,
        'donation_date': d.donation_date.strftime('%Y-%m-%d'),
        'expiration_date': d.expiration_date.strftime('%Y-%m-%d'),
        'donor_name': d.donor_name,
        'days_left': d.days_until_expiry()
    } for d in expiring_soon.order_by('expiration_date')]
    
    # פילוח לפי סוג דם
    by_blood_type = {}
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        type_donations = available_donations.filter(blood_type=blood_type)
        by_blood_type[blood_type] = {
            'total': type_donations.count(),
            'expired': type_donations.filter(expiration_date__lt=today).count(),
            'expiring_soon': type_donations.filter(
                expiration_date__gte=today,
                expiration_date__lte=today + timedelta(days=7)
            ).count()
        }
    
    return JsonResponse({
        'stats': stats,
        'expired_list': expired_list,
        'expiring_list': expiring_list,
        'by_blood_type': by_blood_type
    })

@login_required
@user_passes_test(is_user_or_admin)
@csrf_exempt
@require_http_methods(["POST"])
def mark_as_expired(request):
    """סימון מנה כפגה (הסרה מהמלאי)"""
    try:
        data = json.loads(request.body)
        donation_id = data.get('donation_id')
        
        donation = BloodDonation.objects.get(id=donation_id)
        
        if donation.is_expired():
            donation.is_available = False
            donation.save()
            
            log_audit(
                'BLOOD_EXPIRED',
                f'מנה סומנה כפגה: {donation.blood_type} - {donation.donor_name}',
                blood_type=donation.blood_type,
                quantity=1,
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'message': f'מנה {donation_id} סומנה כפגה והוסרה מהמלאי'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'המנה עדיין לא פגה'
            }, status=400)
            
    except BloodDonation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'מנה לא נמצאה'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@user_passes_test(is_user_or_admin)
@csrf_exempt
@require_http_methods(["POST"])
def batch_remove_expired(request):
    """הסרת כל המנות שפג תוקפן"""
    try:
        today = date.today()
        expired_donations = BloodDonation.objects.filter(
            is_available=True,
            expiration_date__lt=today
        )
        
        count = expired_donations.count()
        
        # פירוט לפי סוג דם
        by_type = {}
        for blood_type, _ in BloodDonation.BLOOD_TYPES:
            type_count = expired_donations.filter(blood_type=blood_type).count()
            if type_count > 0:
                by_type[blood_type] = type_count
        
        # הסרה מהמלאי
        expired_donations.update(is_available=False)
        
        log_audit(
            'BATCH_EXPIRED',
            f'הסרה אוטומטית של {count} מנות פגות: {by_type}',
            quantity=count,
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'הוסרו {count} מנות שפג תוקפן',
            'count': count,
            'by_type': by_type
        })
        
    except Exception as e:
        log_audit('BATCH_EXPIRED', f'שגיאה: {str(e)}', success=False, request=request)
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@user_passes_test(is_user_or_admin)
def export_expiration_report(request):
    """יצוא דוח תפוגה ל-CSV"""
    today = date.today()
    available_donations = BloodDonation.objects.filter(is_available=True).order_by('expiration_date')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="expiration_report_{today.strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Blood Type', 'Donation Date', 'Expiration Date', 'Days Left', 'Status', 'Donor Name'])
    
    for d in available_donations:
        days_left = d.days_until_expiry()
        status = 'פג תוקף' if d.is_expired() else f'{days_left} ימים' if days_left is not None else 'לא ידוע'
        
        writer.writerow([
            d.id,
            d.blood_type,
            d.donation_date.strftime('%Y-%m-%d'),
            d.expiration_date.strftime('%Y-%m-%d') if d.expiration_date else 'N/A',
            days_left if days_left is not None else 'N/A',
            status,
            d.donor_name
        ])
    
    log_audit('DATA_EXPORTED', f'יצוא דוח תפוגה: {available_donations.count()} רשומות', request=request)
    
    return response



# ============= Dashboard & Analytics =============

@login_required
def dashboard(request):
    """דף Dashboard מרכזי"""
    log_audit('RECORD_VIEWED', 'גישה ל-Dashboard', request=request)
    return render(request, 'blood/dashboard.html')

@login_required
def get_dashboard_data(request):
    """API - נתונים ל-Dashboard"""
    today = date.today()
    
    # --- KPIs מרכזיים ---
    total_donations = BloodDonation.objects.count()
    available_units = BloodDonation.objects.filter(is_available=True).count()
    dispensed_units = BloodDonation.objects.filter(is_available=False).count()
    
    # תרומות 30 יום אחרונים
    last_30_days = today - timedelta(days=30)
    donations_last_month = BloodDonation.objects.filter(
        donation_date__gte=last_30_days
    ).count()
    
    # מנות קרובות לפקיעה
    expiring_soon = BloodDonation.objects.filter(
        is_available=True,
        expiration_date__gte=today,
        expiration_date__lte=today + timedelta(days=7)
    ).count()
    
    # מנות פגות
    expired = BloodDonation.objects.filter(
        is_available=True,
        expiration_date__lt=today
    ).count()
    
    kpis = {
        'total_donations': total_donations,
        'available_units': available_units,
        'dispensed_units': dispensed_units,
        'donations_last_month': donations_last_month,
        'expiring_soon': expiring_soon,
        'expired': expired,
        'utilization_rate': round((dispensed_units / total_donations * 100) if total_donations > 0 else 0, 1)
    }
    
    # --- מלאי לפי סוג דם ---
    inventory_by_type = {}
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        inventory_by_type[blood_type] = BloodDonation.objects.filter(
            blood_type=blood_type,
            is_available=True
        ).count()
    
    # --- מגמות תרומות (12 חודשים אחרונים) ---
    last_12_months = today - timedelta(days=365)
    donations_by_month = BloodDonation.objects.filter(
        donation_date__gte=last_12_months
    ).annotate(
        month=TruncMonth('donation_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    monthly_trend = [{
        'month': item['month'].strftime('%Y-%m'),
        'count': item['count']
    } for item in donations_by_month]
    
    # --- תרומות לפי סוג דם (כל הזמן) ---
    donations_by_blood_type = {}
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        donations_by_blood_type[blood_type] = BloodDonation.objects.filter(
            blood_type=blood_type
        ).count()
    
    # --- ניפוקים לפי סוג דם ---
    dispensed_by_blood_type = {}
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        dispensed_by_blood_type[blood_type] = BloodDonation.objects.filter(
            blood_type=blood_type,
            is_available=False
        ).count()
    
    # --- פעילות 7 ימים אחרונים ---
    last_7_days = today - timedelta(days=7)
    daily_activity = []
    
    for i in range(7):
        day = today - timedelta(days=6-i)
        donations = BloodDonation.objects.filter(donation_date=day).count()
        
        # ספירת ניפוקים מ-AuditLog
        dispensed = AuditLog.objects.filter(
            action__in=['BLOOD_DISPENSED', 'EMERGENCY_DISPENSED'],
            timestamp__date=day,
            success=True
        ).count()
        
        daily_activity.append({
            'date': day.strftime('%d/%m'),
            'donations': donations,
            'dispensed': dispensed
        })
    
    # --- Top 5 תורמים פעילים (אם Admin או User) ---
    top_donors = []
    if request.user.is_admin() or request.user.is_user():
        donor_stats = BloodDonation.objects.values('donor_name', 'donor_id').annotate(
            donation_count=Count('id')
        ).order_by('-donation_count')[:5]
        
        top_donors = [{
            'name': donor['donor_name'],
            'donor_id': donor['donor_id'],
            'count': donor['donation_count']
        } for donor in donor_stats]
    
    # --- סטטוס תפוגה ---
    expiration_status = {
        'ok': BloodDonation.objects.filter(
            is_available=True,
            expiration_date__gt=today + timedelta(days=14)
        ).count(),
        'warning': BloodDonation.objects.filter(
            is_available=True,
            expiration_date__gt=today,
            expiration_date__lte=today + timedelta(days=14)
        ).count(),
        'critical': expiring_soon,
        'expired': expired
    }
    
    # --- אחוז ניצול לפי סוג דם ---
    utilization_by_type = {}
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        total = BloodDonation.objects.filter(blood_type=blood_type).count()
        used = BloodDonation.objects.filter(blood_type=blood_type, is_available=False).count()
        utilization_by_type[blood_type] = round((used / total * 100) if total > 0 else 0, 1)
    
    return JsonResponse({
        'kpis': kpis,
        'inventory_by_type': inventory_by_type,
        'monthly_trend': monthly_trend,
        'donations_by_blood_type': donations_by_blood_type,
        'dispensed_by_blood_type': dispensed_by_blood_type,
        'daily_activity': daily_activity,
        'top_donors': top_donors,
        'expiration_status': expiration_status,
        'utilization_by_type': utilization_by_type
    })




# ============= Advanced Reports Generator =============

@login_required
@user_passes_test(is_user_or_admin)
def reports_generator(request):
    """דף מחולל דוחות"""
    log_audit('RECORD_VIEWED', 'גישה למחולל דוחות', request=request)
    return render(request, 'blood/reports_generator.html')

@login_required
@user_passes_test(is_user_or_admin)
def generate_custom_report(request):
    """יצירת דוח מותאם אישית"""
    report_type = request.GET.get('type', 'inventory')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    blood_types = request.GET.getlist('blood_types[]')
    include_charts = request.GET.get('include_charts', 'true') == 'true'
    format_type = request.GET.get('format', 'pdf')  # pdf or csv
    
    today = date.today()
    
    # בניית שאילתה
    donations = BloodDonation.objects.all()
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            donations = donations.filter(donation_date__gte=date_from_obj)
        except:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            donations = donations.filter(donation_date__lte=date_to_obj)
        except:
            pass
    
    if blood_types:
        donations = donations.filter(blood_type__in=blood_types)
    
    # יצירת דוח לפי סוג
    if format_type == 'csv':
        return generate_csv_report(request, report_type, donations, date_from, date_to)
    else:
        return generate_pdf_report(request, report_type, donations, date_from, date_to, include_charts)

def generate_csv_report(request, report_type, donations, date_from, date_to):
    """יצירת דוח CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    filename = f'{report_type}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    if report_type == 'inventory':
        writer.writerow(['Blood Type', 'Total', 'Available', 'Used', 'Utilization %'])
        for blood_type, _ in BloodDonation.BLOOD_TYPES:
            type_donations = donations.filter(blood_type=blood_type)
            total = type_donations.count()
            available = type_donations.filter(is_available=True).count()
            used = type_donations.filter(is_available=False).count()
            util = round((used / total * 100) if total > 0 else 0, 1)
            writer.writerow([blood_type, total, available, used, f'{util}%'])
    
    elif report_type == 'donations':
        writer.writerow(['ID', 'Blood Type', 'Date', 'Donor ID', 'Donor Name', 'Status', 'Expiration'])
        for d in donations.order_by('-donation_date'):
            writer.writerow([
                d.id,
                d.blood_type,
                d.donation_date.strftime('%Y-%m-%d'),
                d.donor_id,
                d.donor_name,
                'Available' if d.is_available else 'Used',
                d.expiration_date.strftime('%Y-%m-%d') if d.expiration_date else 'N/A'
            ])
    
    elif report_type == 'expiration':
        writer.writerow(['Blood Type', 'Total', 'Expired', 'Expiring Soon', 'OK'])
        for blood_type, _ in BloodDonation.BLOOD_TYPES:
            type_donations = donations.filter(blood_type=blood_type, is_available=True)
            total = type_donations.count()
            expired = type_donations.filter(expiration_date__lt=date.today()).count()
            expiring = type_donations.filter(
                expiration_date__gte=date.today(),
                expiration_date__lte=date.today() + timedelta(days=7)
            ).count()
            ok = total - expired - expiring
            writer.writerow([blood_type, total, expired, expiring, ok])
    
    log_audit('REPORT_GENERATED', f'דוח CSV נוצר: {report_type}', request=request)
    return response

def generate_pdf_report(request, report_type, donations, date_from, date_to, include_charts):
    """יצירת דוח PDF מתקדם"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=50, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # כותרת ראשית
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#667eea'),
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=20
    )
    
    # כותרת
    report_titles = {
        'inventory': 'Inventory Report - Blood Stock Analysis',
        'donations': 'Donations Report - Detailed Records',
        'expiration': 'Expiration Report - Stock Validity',
        'summary': 'Summary Report - Complete Overview'
    }
    
    elements.append(Paragraph(f'BECS - {report_titles.get(report_type, "Custom Report")}', title_style))
    
    # תאריכים
    date_range = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}'
    if date_from and date_to:
        date_range += f' | Period: {date_from} to {date_to}'
    elements.append(Paragraph(date_range, subtitle_style))
    elements.append(Spacer(1, 20))
    
    # תוכן לפי סוג דוח
    if report_type == 'inventory':
        elements.extend(generate_inventory_report_content(donations, include_charts))
    elif report_type == 'donations':
        elements.extend(generate_donations_report_content(donations))
    elif report_type == 'expiration':
        elements.extend(generate_expiration_report_content(donations, include_charts))
    elif report_type == 'summary':
        elements.extend(generate_summary_report_content(donations, include_charts))
    
    # Footer
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
    elements.append(Paragraph('BECS - Blood Establishment Computer Software | PART 11 & HIPAA Compliant', footer_style))
    
    # בניית PDF
    doc.build(elements)
    buffer.seek(0)
    
    log_audit('REPORT_GENERATED', f'דוח PDF נוצר: {report_type}, {donations.count()} רשומות', request=request)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="becs_{report_type}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response

def generate_inventory_report_content(donations, include_charts):
    """תוכן דוח מלאי"""
    elements = []
    
    # כותרת סעיף
    section_style = ParagraphStyle('Section', fontSize=16, textColor=colors.HexColor('#667eea'), spaceAfter=15, fontName='Helvetica-Bold')
    elements.append(Paragraph('Current Inventory Status', section_style))
    
    # טבלת נתונים
    data = [['Blood Type', 'Total', 'Available', 'Used', 'Utilization %', 'Status']]
    
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        type_donations = donations.filter(blood_type=blood_type)
        total = type_donations.count()
        available = type_donations.filter(is_available=True).count()
        used = type_donations.filter(is_available=False).count()
        util = round((used / total * 100) if total > 0 else 0, 1)
        
        status = '✓ Good' if available > 10 else '⚠ Low' if available > 0 else '✗ Empty'
        
        data.append([blood_type, str(total), str(available), str(used), f'{util}%', status])
    
    # סה"כ
    total_all = donations.count()
    available_all = donations.filter(is_available=True).count()
    used_all = donations.filter(is_available=False).count()
    util_all = round((used_all / total_all * 100) if total_all > 0 else 0, 1)
    data.append(['TOTAL', str(total_all), str(available_all), str(used_all), f'{util_all}%', ''])
    
    table = Table(data, colWidths=[80, 60, 70, 60, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # גרף אם נדרש
    if include_charts:
        chart_img = create_inventory_chart(donations)
        if chart_img:
            elements.append(Paragraph('Visual Analysis', section_style))
            elements.append(chart_img)
    
    return elements

def generate_donations_report_content(donations):
    """תוכן דוח תרומות"""
    elements = []
    
    section_style = ParagraphStyle('Section', fontSize=16, textColor=colors.HexColor('#667eea'), spaceAfter=15, fontName='Helvetica-Bold')
    elements.append(Paragraph('Detailed Donations Records', section_style))
    
    # לקיחת 100 רשומות אחרונות
    recent_donations = donations.order_by('-donation_date')[:100]
    
    data = [['ID', 'Type', 'Date', 'Donor ID', 'Donor Name', 'Status']]
    
    for d in recent_donations:
        data.append([
            str(d.id),
            d.blood_type,
            d.donation_date.strftime('%Y-%m-%d'),
            d.donor_id,
            d.donor_name[:20],
            '✓' if d.is_available else '✗'
        ])
    
    table = Table(data, colWidths=[40, 50, 70, 70, 130, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    
    if donations.count() > 100:
        note_style = ParagraphStyle('Note', fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f'Showing 100 most recent records out of {donations.count()} total', note_style))
    
    return elements

def generate_expiration_report_content(donations, include_charts):
    """תוכן דוח תפוגה"""
    elements = []
    
    section_style = ParagraphStyle('Section', fontSize=16, textColor=colors.HexColor('#667eea'), spaceAfter=15, fontName='Helvetica-Bold')
    elements.append(Paragraph('Expiration Analysis', section_style))
    
    today = date.today()
    available = donations.filter(is_available=True)
    
    data = [['Blood Type', 'Total', 'Expired', 'Expiring (7d)', 'Warning (14d)', 'OK']]
    
    for blood_type, _ in BloodDonation.BLOOD_TYPES:
        type_don = available.filter(blood_type=blood_type)
        total = type_don.count()
        expired = type_don.filter(expiration_date__lt=today).count()
        expiring = type_don.filter(
            expiration_date__gte=today,
            expiration_date__lte=today + timedelta(days=7)
        ).count()
        warning = type_don.filter(
            expiration_date__gt=today + timedelta(days=7),
            expiration_date__lte=today + timedelta(days=14)
        ).count()
        ok = total - expired - expiring - warning
        
        data.append([blood_type, str(total), str(expired), str(expiring), str(warning), str(ok)])
    
    table = Table(data, colWidths=[80, 60, 60, 80, 80, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    return elements

def generate_summary_report_content(donations, include_charts):
    """דוח סיכום מקיף"""
    elements = []
    
    section_style = ParagraphStyle('Section', fontSize=16, textColor=colors.HexColor('#667eea'), spaceAfter=15, fontName='Helvetica-Bold')
    
    # סיכום כללי
    elements.append(Paragraph('Executive Summary', section_style))
    
    total = donations.count()
    available = donations.filter(is_available=True).count()
    used = donations.filter(is_available=False).count()
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Donations', str(total)],
        ['Available Units', str(available)],
        ['Used Units', str(used)],
        ['Utilization Rate', f'{round((used/total*100) if total > 0 else 0, 1)}%'],
    ]
    
    table = Table(summary_data, colWidths=[200, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # מלאי + תפוגה
    elements.extend(generate_inventory_report_content(donations, False))
    elements.append(PageBreak())
    elements.extend(generate_expiration_report_content(donations, False))
    
    return elements

def create_inventory_chart(donations):
    """יצירת גרף מלאי"""
    try:
        fig, ax = plt.subplots(figsize=(8, 4))
        
        blood_types = []
        available_counts = []
        
        for blood_type, _ in BloodDonation.BLOOD_TYPES:
            blood_types.append(blood_type)
            count = donations.filter(blood_type=blood_type, is_available=True).count()
            available_counts.append(count)
        
        ax.barh(blood_types, available_counts, color='#667eea')
        ax.set_xlabel('Available Units')
        ax.set_title('Current Inventory by Blood Type')
        ax.grid(axis='x', alpha=0.3)
        
        # שמירה ל-buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        plt.close()
        
        # המרה ל-Image של ReportLab
        img = Image(buf, width=6*inch, height=3*inch)
        return img
    except:
        return None










#=============================================================================