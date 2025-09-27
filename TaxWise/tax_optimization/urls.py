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
    
    # CIBIL Score Advisor pages
    path('cibil/', views.cibil_dashboard, name='cibil-dashboard'),
    path('cibil/analysis/', views.cibil_analysis, name='cibil-analysis'),
    path('cibil/recommendations/', views.cibil_recommendations, name='cibil-recommendations'),
    path('cibil/whatif/', views.cibil_whatif, name='cibil-whatif'),
    
    # Smart Financial Data Ingestion pages
    path('data-ingestion/', views.data_ingestion_upload, name='data-ingestion-upload'),
    path('data-ingestion/results/<uuid:session_id>/', views.data_ingestion_results, name='data-ingestion-results'),
]

# Simple API URLs for backward compatibility
simple_api_patterns = [
    path('calculate/', views.calculate_tax_simple, name='api-calculate-simple'),
    path('classify/', views.classify_transaction_simple, name='api-classify-simple'),
    path('recommendations/', views.get_recommendations_simple, name='api-recommendations-simple'),
    
    # CIBIL Score API endpoints
    path('cibil/score/', views.get_cibil_score, name='api-cibil-score'),
    path('cibil/recommendations/', views.get_cibil_recommendations, name='api-cibil-recommendations'),
    path('cibil/whatif/', views.cibil_whatif_analysis, name='api-cibil-whatif'),
    path('cibil/analyze-financial-data/', views.analyze_financial_data_for_cibil, name='api-cibil-analyze-data'),
    
    # Smart Financial Data Ingestion API endpoints
    path('ingestion/create-session/', views.api_create_ingestion_session, name='api-create-ingestion-session'),
    path('ingestion/upload-file/', views.api_upload_file, name='api-upload-file'),
    path('ingestion/session-status/<uuid:session_id>/', views.api_session_status, name='api-session-status'),
    path('ingestion/confirm-transactions/', views.api_confirm_transactions, name='api-confirm-transactions'),
    path('ingestion/confirm-patterns/', views.api_confirm_patterns, name='api-confirm-patterns'),
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