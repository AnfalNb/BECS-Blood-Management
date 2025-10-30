# blood_bank/chatbot_views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
import json
from .deepseek_service import DeepSeekChatbot
from .models import AuditLog

# בדיקת הרשאות - רק אדמין וחוקר
def is_allowed_chatbot(user):
    return user.role in ['ADMIN', 'RESEARCHER']

@login_required
@user_passes_test(is_allowed_chatbot)
def chatbot_page(request):
    """
    Render chatbot interface
    """
    quick_answers = DeepSeekChatbot().get_quick_answers(request.user.role)
    
    # רישום ב-Audit
    AuditLog.objects.create(
        action='CHATBOT_ACCESS',
        details=f'User {request.user.username} accessed chatbot',
        user=request.user.username,
        ip_address=request.META.get('REMOTE_ADDR', '')
    )
    
    context = {
        'user_role': request.user.role,
        'quick_answers': quick_answers,
        'is_admin': request.user.role == 'ADMIN',
        'is_researcher': request.user.role == 'RESEARCHER'
    }
    return render(request, 'blood/chatbot.html', context)

@login_required
@user_passes_test(is_allowed_chatbot)
@csrf_exempt
def chatbot_send_message(request):
    """
    Handle chat message and return response
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        conversation_history = data.get('history', [])
        
        if not message:
            return JsonResponse({'error': 'Empty message'}, status=400)
        
        # רישום השאלה ב-Audit (בלי PHI)
        AuditLog.objects.create(
            action='CHATBOT_QUERY',
            details=f'Query length: {len(message)} chars',
            user=request.user.username,
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # שלח ל-DeepSeek
        chatbot = DeepSeekChatbot()
        result = chatbot.chat(
            message=message,
            user_role=request.user.role,
            conversation_history=conversation_history
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'response': result['response'],
                'usage': result.get('usage', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_allowed_chatbot)
def chatbot_get_suggestions(request):
    """
    Get contextual suggestions based on current page/action
    """
    context = request.GET.get('context', '')
    chatbot = DeepSeekChatbot()
    
    suggestions = {
        'donation': [
            "What are the donor eligibility criteria?",
            "How long does blood last in storage?",
            "What tests are performed on donated blood?"
        ],
        'dispense': [
            "Show blood compatibility chart",
            "What's the protocol for emergency dispensing?",
            "How to handle rare blood type requests?"
        ],
        'audit': [
            "What are PART 11 requirements?",
            "How to generate compliance report?",
            "What actions require audit logging?"
        ],
        'research': [
            "What's the distribution of blood types in Israel?",
            "Show donation trends over last 6 months",
            "How to export de-identified data?"
        ]
    }
    
    return JsonResponse({
        'suggestions': suggestions.get(context, chatbot.get_quick_answers(request.user.role))
    })