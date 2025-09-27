# analyzer/urls.py
from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
    path('detail/<int:pk>/', views.detail_view, name='detail'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
]
