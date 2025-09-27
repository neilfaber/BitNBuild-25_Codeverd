# cibil/urls.py
from django.urls import path
from . import views

app_name = 'cibil'

urlpatterns = [
    # ==================== MAIN DASHBOARD ====================
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard-alt'),
    
    # ==================== PROFILE MANAGEMENT ====================
    path('profile/create/', views.create_profile, name='create_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('score/update/', views.update_score, name='update_score'),
    
    # ==================== CREDIT ACCOUNTS ====================
    path('accounts/', views.credit_accounts, name='credit_accounts'),
    path('accounts/add/', views.add_credit_account, name='add_credit_account'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('accounts/<int:account_id>/edit/', views.edit_credit_account, name='edit_credit_account'),
    path('accounts/<int:account_id>/delete/', views.delete_credit_account, name='delete_credit_account'),
    
    # ==================== PAYMENT HISTORY ====================
    path('payments/', views.payment_history, name='payment_history'),
    path('payments/<int:account_id>/', views.payment_history, name='account_payment_history'),
    path('accounts/<int:account_id>/add-payment/', views.add_payment, name='add_payment'),
    
    # ==================== RECOMMENDATIONS ====================
    path('recommendations/', views.recommendations, name='recommendations'),
    path('recommendations/<int:recommendation_id>/complete/', 
         views.mark_recommendation_completed, name='mark_recommendation_completed'),
    
    # ==================== WHAT-IF SCENARIOS ====================
    path('scenarios/', views.what_if_scenarios, name='what_if_scenarios'),
    path('scenarios/create/', views.create_scenario, name='create_scenario'),
    path('scenarios/<int:scenario_id>/delete/', views.delete_scenario, name='delete_scenario'),
    
    # ==================== ANALYTICS & REPORTS ====================
    path('analytics/', views.analytics, name='analytics'),
    path('export/', views.export_data, name='export_data'),
    
    # ==================== API ENDPOINTS ====================
    path('api/score-history/', views.score_history_api, name='score_history_api'),
    path('api/utilization/', views.utilization_api, name='utilization_api'),
    path('api/payment-trends/', views.payment_trends_api, name='payment_trends_api'),
    
    # ==================== YOUR EXISTING ENDPOINT ====================
    path('advice/', views.get_cibil_advice, name='cibil-advice'),
]