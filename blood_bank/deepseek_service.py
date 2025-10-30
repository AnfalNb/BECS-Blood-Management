# blood_bank/deepseek_service.py
import requests
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DeepSeekChatbot:
    """
    Chatbot service using DeepSeek API for blood bank assistance
    """
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"
        
    def get_system_prompt(self, user_role):
        """
        Return role-specific system prompts
        """
        base_prompt = """
        You are a helpful assistant for a blood bank management system.
        You have knowledge about:
        - Blood types and compatibility (A+, A-, B+, B-, AB+, AB-, O+, O-)
        - Blood donation procedures and requirements
        - FDA PART 11 and HIPAA compliance
        - Blood storage and expiration guidelines
        """
        
        if user_role == 'ADMIN':
            return base_prompt + """
            You are assisting an administrator. You can provide:
            - System management guidance
            - User management help
            - Compliance and audit information
            - Advanced statistics and reports
            - Emergency procedures (MCI - Mass Casualty Incident)
            - Full access to all blood bank operations
            """
        
        elif user_role == 'RESEARCHER':
            return base_prompt + """
            You are assisting a research student. Remember:
            - Only discuss de-identified data
            - Focus on statistical and research aspects
            - DO NOT reveal any PHI (Personal Health Information)
            - Help with data analysis and trends
            - Explain blood type distributions in Israeli population
            - Guide on research methodologies
            Important: Never mention specific donor names, IDs, or exact dates.
            """
        
        else:  # Regular USER
            return base_prompt + """
            You are assisting a blood bank employee. You can help with:
            - Blood donation procedures
            - Blood dispensing guidelines
            - Inventory management
            - Emergency protocols
            - Daily operations
            """
    
    def get_context_data(self, user_role):
        """
        Get relevant context based on user role
        """
        from .models import BloodDonation
        from django.db.models import Count
        from datetime import datetime, timedelta
        
        context = {}
        
        # כולם יכולים לראות סטטיסטיקות בסיסיות
        context['total_units'] = BloodDonation.objects.filter(
            is_available=True
        ).count()
        
        # ספירה לפי סוג דם
        blood_counts = BloodDonation.objects.filter(
            is_available=True
        ).values('blood_type').annotate(
            count=Count('blood_type')
        )
        context['inventory'] = {
            item['blood_type']: item['count'] 
            for item in blood_counts
        }
        
        if user_role == 'ADMIN':
            # אדמין רואה הכל
            context['total_donations'] = BloodDonation.objects.count()
            context['expiring_soon'] = BloodDonation.objects.filter(
                is_available=True,
                expiration_date__lte=datetime.now().date() + timedelta(days=7)  # תיקון כאן
            ).count()
            
        elif user_role == 'RESEARCHER':
            # חוקר רואה רק נתונים מוסווים
            context['monthly_donations'] = BloodDonation.objects.filter(
                donation_date__gte=datetime.now().date() - timedelta(days=30)
            ).count()
            # ללא שמות או תעודות זהות!
            
        return context
    
    def chat(self, message, user_role, conversation_history=None):
        """
        Send message to DeepSeek and get response
        """
        try:
            # הכן את ההיסטוריה
            messages = [
                {"role": "system", "content": self.get_system_prompt(user_role)}
            ]
            
            # הוסף הקשר מהמערכת
            context = self.get_context_data(user_role)
            context_message = f"Current blood bank status: {json.dumps(context)}"
            messages.append({"role": "system", "content": context_message})
            
            # הוסף היסטוריית שיחה אם יש
            if conversation_history:
                messages.extend(conversation_history)
            
            # הוסף את ההודעה החדשה
            messages.append({"role": "user", "content": message})
            
            # שלח ל-DeepSeek
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500,
                "stream": False
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'usage': result.get('usage', {})
                }
            else:
                logger.error(f"DeepSeek API error: {response.status_code}")
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Chatbot error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_quick_answers(self, user_role):
        """
        Return role-specific quick answers/suggestions
        """
        if user_role == 'ADMIN':
            return [
                "Check system audit logs",
                "View expiring blood units",
                "Emergency protocol for MCI",
                "User management guide",
                "Generate compliance report"
            ]
        elif user_role == 'RESEARCHER':
            return [
                "Blood type distribution in Israel",
                "Monthly donation trends",
                "Rare blood types analysis",
                "Export de-identified data",
                "Statistical significance testing"
            ]
        else:
            return [
                "How to register a donation",
                "Blood compatibility chart",
                "Check current inventory",
                "Emergency dispensing procedure",
                "Donor eligibility criteria"
            ]