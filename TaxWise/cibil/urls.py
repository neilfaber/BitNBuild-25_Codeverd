from django.urls import path
from . import views

app_name = 'cibil'

urlpatterns = [
    path('dashboard/', views.cibil_dashboard, name='dashboard'),
    path('history/', views.score_history, name='score_history'),
    path('what-if/', views.what_if_analysis, name='what_if_analysis'),
]