import json
import uuid
import google.generativeai as genai
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .models import ChatSession, ChatMessage
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# Configure Gemini AI
genai.configure(api_key="AIzaSyDtRhEngeP-bsHoDv_ni-h-sKsbzPwMIds")

class TaxAssistantView(View):
    def get(self, request):
        return render(request, 'ai_voice_assistant/chat.html')

@method_decorator(csrf_exempt, name='dispatch')
class ChatAPIView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            session_id = data.get('session_id', str(uuid.uuid4()))
            is_voice = data.get('is_voice', False)
            
            if not message:
                return JsonResponse({'error': 'Message is required'}, status=400)
            
            # Get or create chat session
            session, created = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={'user': request.user if request.user.is_authenticated else None}
            )
            
            # Generate AI response
            response_text = self.generate_tax_response(message)
            
            # Save chat message
            ChatMessage.objects.create(
                session=session,
                message=message,
                response=response_text,
                is_voice=is_voice
            )
            
            return JsonResponse({
                'response': response_text,
                'session_id': session_id,
                'success': True
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def generate_tax_response(self, message):
        try:
            # Create model instance
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Enhanced tax assistant prompt
            system_prompt = """You are TaxWise AI, an expert tax assistant. You help users with:
            - Tax planning and optimization strategies
            - Deduction identification and maximization  
            - Tax law explanations and updates
            - Filing requirements and deadlines
            - Business tax advice
            - Investment tax implications
            - Retirement account tax benefits
            
            Provide accurate, helpful, and personalized tax advice. Always remind users to consult with a qualified tax professional for complex situations. Keep responses concise but comprehensive."""
            
            full_prompt = f"{system_prompt}\n\nUser Question: {message}\n\nResponse:"
            
            response = model.generate_content(full_prompt)
            return response.text
            
        except Exception as e:
            return f"I apologize, but I'm experiencing technical difficulties. Please try again. Error: {str(e)}"

@method_decorator(csrf_exempt, name='dispatch') 
class ChatHistoryView(View):
    def get(self, request):
        session_id = request.GET.get('session_id')
        if not session_id:
            return JsonResponse({'error': 'Session ID required'}, status=400)
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = session.messages.all()
            
            history = []
            for msg in messages:
                history.append({
                    'message': msg.message,
                    'response': msg.response,
                    'timestamp': msg.timestamp.isoformat(),
                    'is_voice': msg.is_voice
                })
            
            return JsonResponse({'history': history})
        except ChatSession.DoesNotExist:
            return JsonResponse({'history': []})