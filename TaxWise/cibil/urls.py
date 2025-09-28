from django.urls import path
from . import views

app_name = 'cibil'

urlpatterns = [
    path('dashboard/', views.cibil_dashboard, name='dashboard'),
    path('analysis/', views.score_analysis, name='score_analysis'),
    path('improve/', views.improve_score, name='improve_score'),
    path('history/', views.score_history, name='score_history'),
    path('what-if/', views.what_if_analysis, name='what_if_analysis'),
    path('quick-import/', views.quick_import_cibil, name='quick_import'),
]