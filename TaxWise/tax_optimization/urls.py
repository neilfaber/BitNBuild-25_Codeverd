"""
URL patterns for Tax Optimization Engine - Comprehensive Routes
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'tax_optimization'

# Frontend Page URLs
frontend_patterns = [
    path('', views.home, name='home'),
    path('calculator/', views.calculator_page, name='calculator'),
    path('recommendations/', views.recommendations_page, name='recommendations'),
]

# Simple API URLs for backward compatibility
simple_api_patterns = [
    path('calculate/', views.calculate_tax_simple, name='api-calculate-simple'),
    path('classify/', views.classify_transaction_simple, name='api-classify-simple'),
]

# Comprehensive REST API URLs
api_patterns = [
    # Tax calculation endpoints
    path('calculate-tax/', views.TaxCalculationAPIView.as_view(), name='calculate-tax'),
    path('tax/calculate/', views.calculate_tax, name='calculate-tax-legacy'),
    
    # Transaction classification endpoints
    path('classify-transactions/', views.TransactionClassificationAPIView.as_view(), name='classify-transactions'),
    path('transactions/classify/', views.classify_transactions, name='classify-transactions-legacy'),
]

urlpatterns = [
    # Frontend pages
    *frontend_patterns,
    
    # Simple API endpoints (for frontend compatibility)
    path('api/', include(simple_api_patterns)),
    
    # Comprehensive REST API endpoints
    path('api/v1/', include(api_patterns)),
]