"""
Django REST API Views for Tax Optimization Engine
Provides endpoints for financial data processing, tax calculation, and recommendations
"""

import logging
import json
from decimal import Decimal
from datetime import datetime
from typing import Dict, List

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    UserProfile, FinancialTransaction, Investment, TaxCalculation,
    TaxOptimizationRecommendation, FileUpload, CreditProfile, CreditAccount,
    PaymentHistory, CreditScoreHistory, CreditScoreFactors,
    CreditImprovementRecommendation, CreditScoreWhatIfScenario,
    FinancialDataIngestion, IngestionFileUpload, ExtractedTransaction,
    TransactionPattern, PatternTransaction, IngestionUserPreferences,
    IngestionAuditLog
)

logger = logging.getLogger(__name__)

# Import AI components with error handling
try:
    from .ai_engine.transaction_classifier import transaction_classifier
    from .ai_engine.recommendation_engine import recommendation_engine
    AI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI components not available: {e}")
    transaction_classifier = None
    recommendation_engine = None
    AI_AVAILABLE = False

from .tax_calculator.engine import tax_calculator
from .utils.file_processor import process_bank_statement
from .utils.cibil_utils import CIBILScoreCalculator, CIBILRecommendationEngine, CIBILWhatIfAnalyzer, analyze_credit_from_financial_data

# Template Views for Frontend Pages
def home(request):
    """Enhanced home page with HTML template"""
    if request.headers.get('Accept') == 'application/json':
        # Return JSON for API calls
        return JsonResponse({
            'message': 'Welcome to TaxWise AI Tax Optimization Engine!',
            'status': 'success',
            'features': [
                'AI-powered transaction classification',
                'Tax calculation for both regimes',
                'Personalized recommendations',
                'File upload and processing'
            ]
        })
    else:
        # Return HTML template for browser requests
        return render(request, 'tax_optimization/dashboard.html')

def calculator_page(request):
    """Tax calculator page"""
    return render(request, 'tax_optimization/calculator.html')

def recommendations_page(request):
    """Tax recommendations page"""
    return render(request, 'tax_optimization/recommendations.html')

# Simple Backward Compatibility Endpoints
@csrf_exempt
def calculate_tax_simple(request):
    """Simple tax calculation endpoint for backward compatibility"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get income (support both field names)
            annual_income = data.get('annual_income', 0)
            salary_income = data.get('salary_income', 0)
            income = Decimal(str(annual_income or salary_income))
            
            # Get deductions
            deductions = Decimal(str(data.get('deductions', 0)))
            taxable_income = income - deductions
            
            # Simple tax calculation for New Regime FY 2024-25
            tax = Decimal('0')
            if taxable_income > 300000:
                if taxable_income <= 600000:
                    tax = (taxable_income - 300000) * Decimal('0.05')
                elif taxable_income <= 900000:
                    tax = 15000 + (taxable_income - 600000) * Decimal('0.10')
                elif taxable_income <= 1200000:
                    tax = 45000 + (taxable_income - 900000) * Decimal('0.15')
                elif taxable_income <= 1500000:
                    tax = 90000 + (taxable_income - 1200000) * Decimal('0.20')
                else:
                    tax = 150000 + (taxable_income - 1500000) * Decimal('0.30')
            
            # Add 4% cess
            cess = tax * Decimal('0.04')
            total_tax = tax + cess
            
            return JsonResponse({
                'status': 'success',
                'data': {
                    'annual_income': float(income),
                    'deductions': float(deductions),
                    'taxable_income': float(taxable_income),
                    'base_tax': float(tax),
                    'cess': float(cess),
                    'total_tax': float(total_tax),
                    'effective_rate': float((total_tax / income * 100)) if income > 0 else 0,
                    'tax_regime': 'New Regime (FY 2024-25)'
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@csrf_exempt
def classify_transaction_simple(request):
    """Simple transaction classification"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            description = data.get('description', '').lower()
            amount = float(data.get('amount', 0))
            
            # Simple keyword-based classification
            category = 'OTHER'
            is_tax_relevant = False
            tax_section = None
            
            if any(word in description for word in ['salary', 'wage', 'payroll']):
                category = 'SALARY'
                transaction_type = 'INCOME'
            elif any(word in description for word in ['rent', 'house', 'apartment']):
                category = 'RENT'
                transaction_type = 'EXPENSE'
                if amount >= 25000:  # Monthly rent threshold
                    is_tax_relevant = True
                    tax_section = '80GG'
            elif any(word in description for word in ['medical', 'hospital', 'pharmacy']):
                category = 'MEDICAL'
                transaction_type = 'EXPENSE'
                is_tax_relevant = True
                tax_section = '80D'
            elif any(word in description for word in ['investment', 'mutual fund', 'ppf', 'epf']):
                category = 'INVESTMENT'
                transaction_type = 'EXPENSE'
                is_tax_relevant = True
                tax_section = '80C'
            else:
                transaction_type = 'EXPENSE' if amount < 0 else 'INCOME'
            
            return JsonResponse({
                'status': 'success',
                'data': {
                    'description': data.get('description', ''),
                    'amount': amount,
                    'category': category,
                    'transaction_type': transaction_type,
                    'is_tax_relevant': is_tax_relevant,
                    'tax_section': tax_section,
                    'confidence_score': 0.7  # Mock confidence
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


# Comprehensive REST API Views

class TaxCalculationAPIView(APIView):
    """API endpoint for tax calculation"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Calculate tax for both regimes and provide recommendation"""
        try:
            data = request.data
            user = request.user
            
            # Extract income details
            income_details = {
                'salary_income': Decimal(str(data.get('salary_income', 0))),
                'business_income': Decimal(str(data.get('business_income', 0))),
                'capital_gains': Decimal(str(data.get('capital_gains', 0))),
                'other_income': Decimal(str(data.get('other_income', 0)))
            }
            
            # Extract deduction details
            deduction_details = {
                '80C': Decimal(str(data.get('section_80c', 0))),
                '80D': Decimal(str(data.get('section_80d', 0))),
                '80E': Decimal(str(data.get('section_80e', 0))),
                '80G': Decimal(str(data.get('section_80g', 0))),
                '80GG': Decimal(str(data.get('section_80gg', 0))),
                '80CCD1B': Decimal(str(data.get('section_80ccd1b', 0))),
                '80TTA': Decimal(str(data.get('section_80tta', 0)))
            }
            
            # Get user profile for age
            try:
                user_profile = UserProfile.objects.get(user=user)
                age = user_profile.age
                financial_year = user_profile.financial_year
            except UserProfile.DoesNotExist:
                age = data.get('age', 30)
                financial_year = "2024-25"
            
            # Calculate tax
            tax_result = tax_calculator.calculate_complete_tax(
                income_details=income_details,
                deduction_details=deduction_details,
                age=age,
                regime=data.get('preferred_regime', 'NEW')
            )
            
            # Convert Decimal objects to float for JSON serialization
            def decimal_to_float(obj):
                if isinstance(obj, dict):
                    return {k: decimal_to_float(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [decimal_to_float(v) for v in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                else:
                    return obj
            
            serialized_result = decimal_to_float(tax_result)
            
            return Response({
                'status': 'success',
                'data': serialized_result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Tax calculation error: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TransactionClassificationAPIView(APIView):
    """API endpoint for transaction classification"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Classify a single transaction or batch of transactions"""
        if not AI_AVAILABLE or transaction_classifier is None:
            return Response({
                'status': 'error',
                'message': 'AI classification not available - using rule-based approach'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            data = request.data
            
            if 'transactions' in data:
                # Batch classification
                transactions = data['transactions']
                results = transaction_classifier.batch_classify_transactions(transactions)
                
                return Response({
                    'status': 'success',
                    'data': results,
                    'statistics': transaction_classifier.get_category_statistics(transactions)
                }, status=status.HTTP_200_OK)
            
            else:
                # Single transaction classification
                result = transaction_classifier.classify_transaction(
                    description=data.get('description', ''),
                    amount=float(data.get('amount', 0)),
                    transaction_date=data.get('date')
                )
                
                return Response({
                    'status': 'success',
                    'data': result
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Transaction classification error: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# Legacy function-based views for backward compatibility

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_tax(request):
    """Legacy endpoint for tax calculation"""
    view = TaxCalculationAPIView()
    return view.post(request)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def classify_transactions(request):
    """Legacy endpoint for transaction classification"""
    view = TransactionClassificationAPIView()
    return view.post(request)@csrf_exempt
def get_recommendations_simple(request):
    """Simple tax recommendations - works with both GET and POST"""
    if request.method in ['GET', 'POST']:
        recommendations = [
            {
                'title': 'Invest in ELSS Mutual Funds',
                'description': 'Invest up to ₹1,50,000 in ELSS for tax savings under Section 80C with only 3-year lock-in.',
                'recommendation_type': 'INVESTMENT',
                'priority': 'HIGH',
                'potential_savings': 46500,  # 31% of 1.5L
                'investment_required': 150000,
                'tax_section': '80C',
                'confidence_score': 0.9
            },
            {
                'title': 'Get Health Insurance',
                'description': 'Purchase health insurance for self and family with premium up to ₹25,000.',
                'recommendation_type': 'INVESTMENT',
                'priority': 'HIGH',
                'potential_savings': 7750,  # 31% of 25K
                'investment_required': 25000,
                'tax_section': '80D',
                'confidence_score': 0.95
            },
            {
                'title': 'Consider New Tax Regime',
                'description': 'Evaluate if new tax regime is beneficial based on your income and deductions.',
                'recommendation_type': 'REGIME_SWITCH',
                'priority': 'MEDIUM',
                'potential_savings': 15000,
                'investment_required': 0,
                'tax_section': None,
                'confidence_score': 0.7
            }
        ]
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'recommendations': recommendations,
                'total_potential_savings': sum(r['potential_savings'] for r in recommendations),
                'high_priority_count': len([r for r in recommendations if r['priority'] == 'HIGH'])
            }
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


# ========================================
# CIBIL Score and Credit Analysis Views
# ========================================

def cibil_dashboard(request):
    """CIBIL Score dashboard page"""
    return render(request, 'tax_optimization/cibil_dashboard.html')

def cibil_analysis(request):
    """Detailed CIBIL analysis page"""
    return render(request, 'tax_optimization/cibil_analysis.html')

def cibil_recommendations(request):
    """CIBIL improvement recommendations page"""
    return render(request, 'tax_optimization/cibil_recommendations.html')

def cibil_whatif(request):
    """What-if scenarios page"""
    return render(request, 'tax_optimization/cibil_whatif.html')

@csrf_exempt
def get_cibil_score(request):
    """Get or calculate user's CIBIL score"""
    if request.method == 'GET':
        try:
            # For demo purposes, return mock data if no real profile exists
            user_id = request.GET.get('user_id', 1)
            
            # Try to get existing credit profile
            try:
                from django.contrib.auth.models import User
                user = User.objects.get(id=user_id)
                credit_profile = CreditProfile.objects.get(user=user)
                
                calculator = CIBILScoreCalculator(credit_profile)
                score_analysis = calculator.calculate_comprehensive_score()
                
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'current_score': score_analysis['overall_score'],
                        'score_range': score_analysis['score_range'],
                        'previous_score': credit_profile.previous_score,
                        'score_change': credit_profile.score_change,
                        'last_updated': credit_profile.last_updated.isoformat() if credit_profile.last_updated else None,
                        'factor_breakdown': score_analysis['factor_scores'],
                        'improvement_areas': score_analysis['improvement_areas']
                    }
                })
                
            except (User.DoesNotExist, CreditProfile.DoesNotExist):
                # Return demo data for new users
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'current_score': 720,
                        'score_range': 'GOOD',
                        'previous_score': 700,
                        'score_change': 20,
                        'last_updated': '2024-01-15',
                        'factor_breakdown': {
                            'payment_history': {
                                'score': 750,
                                'weight': 0.35,
                                'contribution': 262.5,
                                'status': 'GOOD'
                            },
                            'credit_utilization': {
                                'score': 700,
                                'weight': 0.30,
                                'contribution': 210.0,
                                'status': 'GOOD'
                            },
                            'credit_history': {
                                'score': 680,
                                'weight': 0.15,
                                'contribution': 102.0,
                                'status': 'FAIR'
                            },
                            'credit_mix': {
                                'score': 730,
                                'weight': 0.10,
                                'contribution': 73.0,
                                'status': 'GOOD'
                            },
                            'recent_credit': {
                                'score': 750,
                                'weight': 0.10,
                                'contribution': 75.0,
                                'status': 'GOOD'
                            }
                        },
                        'improvement_areas': ['credit_history', 'credit_utilization']
                    }
                })
                
        except Exception as e:
            logger.error(f"Error getting CIBIL score: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to retrieve CIBIL score'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@csrf_exempt
def get_cibil_recommendations(request):
    """Get personalized CIBIL improvement recommendations"""
    if request.method in ['GET', 'POST']:
        try:
            # For demo purposes, return sample recommendations
            recommendations = [
                {
                    'category': 'PAYMENT_BEHAVIOR',
                    'title': 'Set Up Automatic Payments',
                    'description': 'Set up autopay for all credit cards and loans to ensure you never miss a payment. This is the most impactful way to improve your CIBIL score.',
                    'expected_score_improvement': 50,
                    'timeframe_months': 3,
                    'priority': 'CRITICAL',
                    'is_easy_to_implement': True,
                    'cost_involved': 0,
                    'ai_confidence': 0.95,
                    'action_steps': [
                        'Contact your bank to set up autopay',
                        'Choose minimum payment or full payment option',
                        'Set autopay date 3-5 days before due date',
                        'Monitor account regularly for sufficient balance'
                    ]
                },
                {
                    'category': 'CREDIT_UTILIZATION',
                    'title': 'Reduce Credit Card Utilization Below 30%',
                    'description': 'Your current utilization is 45%. Reduce it to below 30% for significant score improvement, ideally below 10% for excellent scores.',
                    'expected_score_improvement': 40,
                    'timeframe_months': 2,
                    'priority': 'HIGH',
                    'is_easy_to_implement': True,
                    'cost_involved': 25000,
                    'ai_confidence': 0.85,
                    'action_steps': [
                        'Calculate 30% of total credit limit (₹45,000)',
                        'Pay down highest utilization cards first',
                        'Consider multiple payments per month',
                        'Track utilization using apps or bank websites'
                    ]
                },
                {
                    'category': 'CREDIT_UTILIZATION',
                    'title': 'Request Credit Limit Increases',
                    'description': 'Increasing your credit limits without increasing balances will automatically improve your utilization ratio.',
                    'expected_score_improvement': 25,
                    'timeframe_months': 1,
                    'priority': 'MEDIUM',
                    'is_easy_to_implement': True,
                    'cost_involved': 0,
                    'ai_confidence': 0.75,
                    'action_steps': [
                        'Contact all credit card companies',
                        'Request limit increases on cards with good payment history',
                        'Avoid using the additional credit',
                        'Wait 6 months between requests'
                    ]
                },
                {
                    'category': 'ACCOUNT_MANAGEMENT',
                    'title': 'Keep Old Credit Cards Active',
                    'description': 'Keep your oldest credit cards open and use them occasionally to maintain credit history length.',
                    'expected_score_improvement': 15,
                    'timeframe_months': 6,
                    'priority': 'MEDIUM',
                    'is_easy_to_implement': True,
                    'cost_involved': 0,
                    'ai_confidence': 0.8,
                    'action_steps': [
                        'Identify your oldest credit cards',
                        'Make small purchases monthly (₹200-500)',
                        'Pay off balances immediately',
                        'Avoid closing old accounts unless they have high fees'
                    ]
                },
                {
                    'category': 'CREDIT_INQUIRIES',
                    'title': 'Limit New Credit Applications',
                    'description': 'You have 3 hard inquiries in the last 6 months. Avoid new credit applications for the next 6 months.',
                    'expected_score_improvement': 20,
                    'timeframe_months': 6,
                    'priority': 'MEDIUM',
                    'is_easy_to_implement': True,
                    'cost_involved': 0,
                    'ai_confidence': 0.8,
                    'action_steps': [
                        'Avoid applying for new credit cards or loans',
                        'Wait at least 6 months between applications',
                        'Use soft inquiry tools to check eligibility first',
                        'Focus on improving existing accounts'
                    ]
                }
            ]
            
            return JsonResponse({
                'status': 'success',
                'data': {
                    'recommendations': recommendations,
                    'total_expected_improvement': sum(r['expected_score_improvement'] for r in recommendations[:3]),
                    'critical_count': len([r for r in recommendations if r['priority'] == 'CRITICAL']),
                    'high_priority_count': len([r for r in recommendations if r['priority'] == 'HIGH']),
                    'quick_wins': [r for r in recommendations if r['timeframe_months'] <= 3 and r['is_easy_to_implement']]
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting CIBIL recommendations: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to generate recommendations'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@csrf_exempt
def cibil_whatif_analysis(request):
    """What-if scenario analysis for CIBIL score prediction"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            scenario_type = data.get('scenario_type', 'custom')
            
            # Define common scenarios
            scenarios = {
                'perfect_payments': {
                    'name': 'Perfect Payment History',
                    'description': 'Maintain 100% on-time payments for all accounts',
                    'current_score': 720,
                    'predicted_score': 770,
                    'score_improvement': 50,
                    'timeframe_months': 6,
                    'confidence_level': 0.9,
                    'difficulty': 'LOW',
                    'changes': [
                        'Set up autopay for all accounts',
                        'Never miss a payment',
                        'Pay at least minimum amount on time'
                    ]
                },
                'reduce_utilization': {
                    'name': 'Reduce Credit Utilization to 10%',
                    'description': 'Lower credit card utilization from 45% to 10%',
                    'current_score': 720,
                    'predicted_score': 760,
                    'score_improvement': 40,
                    'timeframe_months': 2,
                    'confidence_level': 0.85,
                    'difficulty': 'MEDIUM',
                    'changes': [
                        'Pay down ₹52,500 in credit card debt',
                        'Keep balances below 10% of limits',
                        'Monitor utilization monthly'
                    ]
                },
                'increase_limits': {
                    'name': 'Increase Credit Limits by 50%',
                    'description': 'Request credit limit increases on all cards',
                    'current_score': 720,
                    'predicted_score': 745,
                    'score_improvement': 25,
                    'timeframe_months': 1,
                    'confidence_level': 0.75,
                    'difficulty': 'LOW',
                    'changes': [
                        'Call credit card companies',
                        'Request limit increases',
                        'Provide income documentation if needed',
                        'Don\'t use additional credit'
                    ]
                },
                'time_healing': {
                    'name': 'Natural Improvement Over Time',
                    'description': 'Let time naturally improve your credit profile',
                    'current_score': 720,
                    'predicted_score': 735,
                    'score_improvement': 15,
                    'timeframe_months': 12,
                    'confidence_level': 0.95,
                    'difficulty': 'LOW',
                    'changes': [
                        'Continue current payment behavior',
                        'Avoid new credit applications',
                        'Let credit history age naturally',
                        'Old negative marks will have less impact'
                    ]
                },
                'combined_approach': {
                    'name': 'Combined Optimization Strategy',
                    'description': 'Implement multiple improvements simultaneously',
                    'current_score': 720,
                    'predicted_score': 790,
                    'score_improvement': 70,
                    'timeframe_months': 6,
                    'confidence_level': 0.8,
                    'difficulty': 'MEDIUM',
                    'changes': [
                        'Perfect payment history',
                        'Reduce utilization to 10%',
                        'Increase credit limits',
                        'Keep old accounts open',
                        'Limit new inquiries'
                    ]
                }
            }
            
            if scenario_type == 'all':
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'scenarios': list(scenarios.values()),
                        'current_score': 720,
                        'best_scenario': scenarios['combined_approach'],
                        'quickest_improvement': scenarios['increase_limits'],
                        'lowest_cost': scenarios['time_healing']
                    }
                })
            elif scenario_type in scenarios:
                return JsonResponse({
                    'status': 'success',
                    'data': scenarios[scenario_type]
                })
            else:
                # Custom scenario
                custom_params = data.get('parameters', {})
                
                # Simple custom calculation
                base_score = 720
                improvement = 0
                
                if custom_params.get('improve_payments'):
                    improvement += 50
                if custom_params.get('target_utilization'):
                    target = custom_params['target_utilization']
                    current = 45
                    if target < current:
                        improvement += min(40, (current - target) * 1.2)
                if custom_params.get('increase_limits'):
                    improvement += 25
                
                predicted_score = min(900, base_score + improvement)
                
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'name': 'Custom Scenario',
                        'description': 'Custom what-if analysis based on your parameters',
                        'current_score': base_score,
                        'predicted_score': predicted_score,
                        'score_improvement': predicted_score - base_score,
                        'timeframe_months': custom_params.get('timeframe_months', 6),
                        'confidence_level': 0.75,
                        'difficulty': 'MEDIUM'
                    }
                })
                
        except Exception as e:
            logger.error(f"Error in what-if analysis: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to analyze scenario'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@csrf_exempt
def analyze_financial_data_for_cibil(request):
    """Analyze financial transaction data to extract credit behavior patterns"""
    if request.method == 'POST':
        try:
            # This would analyze the user's financial transactions to identify credit patterns
            # For demo purposes, return sample analysis
            
            analysis = {
                'payment_regularity': 85.5,  # Percentage of on-time payments
                'estimated_utilization': 42.3,  # Estimated credit utilization
                'emi_payment_count': 24,  # Number of EMI payments found
                'credit_card_payment_count': 18,  # Number of credit card payments
                'avg_monthly_emi': 15750,  # Average monthly EMI
                'credit_discipline_score': 73.2,  # Overall credit discipline score
                'identified_accounts': [
                    {
                        'type': 'Home Loan',
                        'bank': 'HDFC Bank',
                        'monthly_emi': 25000,
                        'regularity': 100
                    },
                    {
                        'type': 'Credit Card',
                        'bank': 'SBI Card',
                        'avg_payment': 8500,
                        'regularity': 80
                    },
                    {
                        'type': 'Personal Loan',
                        'bank': 'Axis Bank',
                        'monthly_emi': 12000,
                        'regularity': 90
                    }
                ],
                'recommendations': [
                    'Set up autopay for SBI Credit Card to improve payment regularity',
                    'Your credit utilization appears high - consider paying down balances',
                    'Excellent EMI payment history shows good credit discipline'
                ]
            }
            
            return JsonResponse({
                'status': 'success',
                'data': analysis
            })
            
        except Exception as e:
            logger.error(f"Error analyzing financial data: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to analyze financial data'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


# Smart Financial Data Ingestion Views

@login_required
def data_ingestion_upload(request):
    """Data ingestion upload page"""
    return render(request, 'data_ingestion_upload.html', {
        'title': 'Smart Financial Data Ingestion'
    })

@login_required
def data_ingestion_results(request, session_id):
    """Display results of data ingestion session"""
    try:
        ingestion_session = FinancialDataIngestion.objects.get(
            session_id=session_id, 
            user=request.user
        )
        
        # Get session statistics
        uploaded_files = ingestion_session.uploaded_files.all()
        extracted_transactions = ingestion_session.extracted_transactions.all()
        detected_patterns = ingestion_session.detected_patterns.all()
        
        # Categorize transactions by status
        transactions_by_status = {}
        for transaction in extracted_transactions:
            status = transaction.extraction_status
            if status not in transactions_by_status:
                transactions_by_status[status] = []
            transactions_by_status[status].append(transaction)
        
        # Get pattern statistics
        pattern_stats = {}
        for pattern in detected_patterns:
            pattern_type = pattern.pattern_type
            if pattern_type not in pattern_stats:
                pattern_stats[pattern_type] = {
                    'count': 0,
                    'total_amount': Decimal('0'),
                    'confidence': []
                }
            pattern_stats[pattern_type]['count'] += 1
            pattern_stats[pattern_type]['total_amount'] += pattern.average_amount
            pattern_stats[pattern_type]['confidence'].append(pattern.pattern_confidence)
        
        # Calculate average confidence for each pattern type
        for pattern_type, stats in pattern_stats.items():
            if stats['confidence']:
                stats['avg_confidence'] = sum(stats['confidence']) / len(stats['confidence'])
            else:
                stats['avg_confidence'] = 0
        
        context = {
            'session': ingestion_session,
            'uploaded_files': uploaded_files,
            'extracted_transactions': extracted_transactions[:100],  # Limit for display
            'detected_patterns': detected_patterns,
            'transactions_by_status': transactions_by_status,
            'pattern_stats': pattern_stats,
            'total_transactions': extracted_transactions.count(),
            'total_patterns': detected_patterns.count(),
            'success_rate': ingestion_session.success_rate
        }
        
        return render(request, 'data_ingestion_results.html', context)
        
    except FinancialDataIngestion.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Ingestion session not found'
        }, status=404)

@csrf_exempt
@login_required
def api_create_ingestion_session(request):
    """API endpoint to create a new data ingestion session"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Method not allowed'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Create ingestion session
        session = FinancialDataIngestion.objects.create(
            user=request.user,
            session_name=data.get('session_name', 'Untitled Session'),
            session_type=data.get('session_type', 'BULK_UPLOAD'),
            auto_categorize=data.get('auto_categorize', True),
            merge_duplicates=data.get('merge_duplicates', True),
            create_patterns=data.get('create_patterns', True)
        )
        
        # Log audit entry
        IngestionAuditLog.objects.create(
            ingestion_session=session,
            user=request.user,
            action_type='PROCESSING_STARTED',
            action_description=f'Started ingestion session: {session.session_name}',
            was_successful=True
        )
        
        return JsonResponse({
            'status': 'success',
            'session_id': str(session.session_id),
            'message': 'Ingestion session created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating ingestion session: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to create ingestion session'
        }, status=500)

@csrf_exempt
@login_required
def api_upload_file(request):
    """API endpoint to upload files for processing"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Method not allowed'
        }, status=405)
    
    try:
        session_id = request.POST.get('session_id')
        uploaded_file = request.FILES.get('file')
        
        if not session_id or not uploaded_file:
            return JsonResponse({
                'status': 'error',
                'message': 'Missing session_id or file'
            }, status=400)
        
        # Get ingestion session
        try:
            session = FinancialDataIngestion.objects.get(
                session_id=session_id,
                user=request.user
            )
        except FinancialDataIngestion.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Ingestion session not found'
            }, status=404)
        
        # Create file upload record
        file_extension = uploaded_file.name.split('.')[-1].upper()
        file_upload = IngestionFileUpload.objects.create(
            ingestion_session=session,
            original_filename=uploaded_file.name,
            file_format=file_extension,
            file_size_bytes=uploaded_file.size,
            file_path=uploaded_file,
            processing_status='PROCESSING'
        )
        
        # Process the file
        try:
            # Import pattern recognition
            from .utils.pattern_recognition import recognize_transaction_patterns
            from .utils.file_processor import process_bank_statement
            
            # Process the uploaded file
            transactions = process_bank_statement(uploaded_file)
            
            if not transactions:
                file_upload.processing_status = 'FAILED'
                file_upload.processing_error_message = 'No transactions found in file'
                file_upload.save()
                
                return JsonResponse({
                    'status': 'error',
                    'message': 'No transactions found in file'
                }, status=400)
            
            # Analyze patterns
            pattern_analysis = recognize_transaction_patterns(transactions)
            categorized_transactions = pattern_analysis['categorized_transactions']
            detected_patterns = pattern_analysis['patterns']
            
            # Save extracted transactions
            extracted_count = 0
            for trans_data in categorized_transactions:
                extracted_transaction = ExtractedTransaction.objects.create(
                    file_upload=file_upload,
                    ingestion_session=session,
                    raw_transaction_text=trans_data.get('description', ''),
                    extracted_date=trans_data['date'],
                    extracted_amount=abs(trans_data['amount']),
                    extracted_description=trans_data.get('description', ''),
                    ai_predicted_category=trans_data.get('predicted_category', 'OTHER'),
                    ai_confidence_score=trans_data.get('confidence', 0.0),
                    is_recurring_transaction=trans_data.get('is_recurring', False),
                    extraction_confidence=0.9,  # Default confidence
                    extraction_status='CLEANED'
                )
                extracted_count += 1
            
            # Create transaction patterns
            pattern_count = 0
            for category, category_patterns in detected_patterns.items():
                for pattern_data in category_patterns:
                    pattern = TransactionPattern.objects.create(
                        ingestion_session=session,
                        user=request.user,
                        pattern_type=map_category_to_pattern_type(category),
                        pattern_name=f"{category} - {pattern_data['description_pattern']}",
                        pattern_description=f"Recurring {category.lower()} pattern",
                        base_description_pattern=pattern_data['description_pattern'],
                        amount_range_min=pattern_data['avg_amount'] * Decimal('0.9'),
                        amount_range_max=pattern_data['avg_amount'] * Decimal('1.1'),
                        frequency_days=30,  # Default monthly
                        total_occurrences=len(pattern_data['transactions']),
                        first_occurrence_date=min(t['date'] for t in pattern_data['transactions']),
                        last_occurrence_date=max(t['date'] for t in pattern_data['transactions']),
                        next_predicted_date=pattern_data.get('next_expected_date'),
                        pattern_confidence=pattern_data['confidence'],
                        consistency_score=pattern_data['confidence']
                    )
                    pattern_count += 1
            
            # Update file upload status
            file_upload.processing_status = 'COMPLETED'
            file_upload.transactions_extracted = extracted_count
            if transactions:
                file_upload.date_range_start = min(t['date'] for t in transactions)
                file_upload.date_range_end = max(t['date'] for t in transactions)
            file_upload.save()
            
            # Update session statistics
            session.total_files_uploaded += 1
            session.files_processed_successfully += 1
            session.total_transactions_extracted += extracted_count
            session.transactions_with_patterns += sum(
                1 for t in categorized_transactions if t.get('is_recurring', False)
            )
            session.save()
            
            # Log audit entry
            IngestionAuditLog.objects.create(
                ingestion_session=session,
                user=request.user,
                action_type='FILE_UPLOADED',
                action_description=f'Processed file: {uploaded_file.name}',
                affected_object_type='IngestionFileUpload',
                affected_object_id=str(file_upload.id),
                was_successful=True
            )
            
            return JsonResponse({
                'status': 'success',
                'transactions_extracted': extracted_count,
                'patterns_detected': pattern_count,
                'file_id': file_upload.id
            })
            
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            file_upload.processing_status = 'FAILED'
            file_upload.processing_error_message = str(e)
            file_upload.save()
            
            session.files_failed += 1
            session.save()
            
            return JsonResponse({
                'status': 'error',
                'message': 'File processing failed: ' + str(e)
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error in file upload: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Upload failed: ' + str(e)
        }, status=500)

@login_required
def api_session_status(request, session_id):
    """API endpoint to get ingestion session status"""
    try:
        session = FinancialDataIngestion.objects.get(
            session_id=session_id,
            user=request.user
        )
        
        # Calculate processing progress
        total_files = session.total_files_uploaded
        processed_files = session.files_processed_successfully + session.files_failed
        progress_percentage = (processed_files / total_files * 100) if total_files > 0 else 0
        
        # Check if processing is complete
        if processed_files == total_files and total_files > 0:
            if session.files_failed == 0:
                session.ingestion_status = 'COMPLETED'
            elif session.files_processed_successfully > 0:
                session.ingestion_status = 'PARTIALLY_COMPLETED'
            else:
                session.ingestion_status = 'FAILED'
            session.completed_at = datetime.now()
            session.save()
        
        return JsonResponse({
            'session_id': str(session.session_id),
            'ingestion_status': session.ingestion_status,
            'total_files_uploaded': session.total_files_uploaded,
            'files_processed_successfully': session.files_processed_successfully,
            'files_failed': session.files_failed,
            'total_transactions_extracted': session.total_transactions_extracted,
            'transactions_categorized': session.transactions_categorized,
            'transactions_with_patterns': session.transactions_with_patterns,
            'progress_percentage': round(progress_percentage, 2),
            'success_rate': round(session.success_rate, 2),
            'started_at': session.started_at.isoformat(),
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        })
        
    except FinancialDataIngestion.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Session not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get session status'
        }, status=500)

@csrf_exempt
@login_required
def api_confirm_transactions(request):
    """API endpoint to confirm processed transactions"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Method not allowed'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        transaction_ids = data.get('transaction_ids', [])
        
        if not transaction_ids:
            return JsonResponse({
                'status': 'error',
                'message': 'No transaction IDs provided'
            }, status=400)
        
        # Get extracted transactions
        extracted_transactions = ExtractedTransaction.objects.filter(
            id__in=transaction_ids,
            ingestion_session__user=request.user
        )
        
        confirmed_count = 0
        for extracted_trans in extracted_transactions:
            # Create final financial transaction
            final_transaction = FinancialTransaction.objects.create(
                user=request.user,
                date=extracted_trans.extracted_date,
                amount=extracted_trans.extracted_amount,
                description=extracted_trans.extracted_description,
                transaction_type='EXPENSE' if extracted_trans.extracted_amount > 0 else 'INCOME',
                ai_category=extracted_trans.ai_predicted_category,
                ai_confidence_score=extracted_trans.ai_confidence_score,
                processed_by_ai=True
            )
            
            # Update extracted transaction
            extracted_trans.extraction_status = 'VALIDATED'
            extracted_trans.final_transaction = final_transaction
            extracted_trans.save()
            
            confirmed_count += 1
        
        return JsonResponse({
            'status': 'success',
            'confirmed_count': confirmed_count,
            'message': f'Confirmed {confirmed_count} transactions'
        })
        
    except Exception as e:
        logger.error(f"Error confirming transactions: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to confirm transactions'
        }, status=500)

@csrf_exempt
@login_required
def api_confirm_patterns(request):
    """API endpoint to confirm detected transaction patterns"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Method not allowed'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        pattern_ids = data.get('pattern_ids', [])
        
        if not pattern_ids:
            return JsonResponse({
                'status': 'error',
                'message': 'No pattern IDs provided'
            }, status=400)
        
        # Get and confirm patterns
        patterns = TransactionPattern.objects.filter(
            pattern_id__in=pattern_ids,
            user=request.user
        )
        
        confirmed_count = 0
        for pattern in patterns:
            pattern.pattern_status = 'CONFIRMED'
            pattern.save()
            confirmed_count += 1
        
        return JsonResponse({
            'status': 'success',
            'confirmed_count': confirmed_count,
            'message': f'Confirmed {confirmed_count} patterns'
        })
        
    except Exception as e:
        logger.error(f"Error confirming patterns: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to confirm patterns'
        }, status=500)

def map_category_to_pattern_type(category):
    """Map AI category to pattern type"""
    category_mapping = {
        'EMI': 'MONTHLY_EMI',
        'SIP': 'MONTHLY_SIP', 
        'RENT': 'MONTHLY_RENT',
        'INSURANCE': 'MONTHLY_INSURANCE',
        'SUBSCRIPTION': 'MONTHLY_SUBSCRIPTION',
        'UTILITIES': 'MONTHLY_PAYMENT',
        'SALARY': 'MONTHLY_PAYMENT'
    }
    return category_mapping.get(category, 'CUSTOM_RECURRING')