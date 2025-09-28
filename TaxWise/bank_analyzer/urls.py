# analyzer/urls.py
from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
    path('detail/<int:pk>/', views.detail_view, name='detail'),
    path('das/', views.user_dashboard, name='user_dashboard'),
    path('predictions/', views.financial_predictions_view, name='financial_predictions'),
    path('predictions/<str:prediction_type>/', views.prediction_details_view, name='prediction_details'),
]
