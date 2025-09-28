from django.urls import path
from .views import TaxAssistantView, ChatAPIView, ChatHistoryView

app_name = 'ai_voice_assistant'

urlpatterns = [
    path('', TaxAssistantView.as_view(), name='chat'),
    path('api/chat/', ChatAPIView.as_view(), name='chat_api'),
    path('api/history/', ChatHistoryView.as_view(), name='chat_history'),
]