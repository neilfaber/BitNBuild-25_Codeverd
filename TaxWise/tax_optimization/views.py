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
from django.shortcuts import render, redirect

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    UserProfile, FinancialTransaction, Investment, TaxCalculation,
    TaxOptimizationRecommendation, FileUpload, CreditProfile, CreditAccount,
    PaymentHistory, CreditScoreHistory, CreditScoreFactors,
    CreditImprovementRecommendation, CreditScoreWhatIfScenario
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
from .utils.cibil_utils import CIBILScoreCalculator, CIBILRecommendationEngine, CIBILWhatIfAnalyzer, analyze_credit_from_financial_data
from .automatic_tax_calculator import AutomaticTaxCalculator

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
    """CIBIL Score dashboard page - redirects to comprehensive CIBIL app dashboard"""
    return redirect('cibil:dashboard')

def cibil_analysis(request):
    """Detailed CIBIL analysis page - redirects to comprehensive CIBIL dashboard"""
    return redirect('cibil:dashboard')

def cibil_recommendations(request):
    """CIBIL improvement recommendations page - redirects to comprehensive CIBIL dashboard"""
    return redirect('cibil:dashboard')

def cibil_whatif(request):
    """What-if scenarios page - redirects to CIBIL what-if analysis"""
    return redirect('cibil:what_if_analysis')

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


# ====================================
# AUTOMATIC TAX CALCULATION VIEWS
# ====================================

@login_required
def automatic_tax_dashboard(request):
    """
    Main dashboard for automatic tax calculations
    """
    try:
        calculator = AutomaticTaxCalculator(request.user)
        tax_analysis = calculator.calculate_comprehensive_tax_savings()
        
        return render(request, 'tax_optimization/automatic_tax_dashboard.html', {
            'tax_analysis': tax_analysis,
            'user': request.user
        })
        
    except Exception as e:
        logger.error(f"Error in automatic tax dashboard: {e}")
        return render(request, 'tax_optimization/automatic_tax_dashboard.html', {
            'error': 'Unable to calculate tax analysis at the moment.'
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_automatic_tax_calculations(request):
    """
    API endpoint to get automatic tax calculations
    """
    try:
        financial_year = request.GET.get('financial_year', None)
        calculator = AutomaticTaxCalculator(request.user, financial_year)
        tax_analysis = calculator.calculate_comprehensive_tax_savings()
        
        # Convert Decimal objects to float for JSON serialization
        def decimal_to_float(obj):
            if isinstance(obj, dict):
                return {k: decimal_to_float(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [decimal_to_float(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            else:
                return obj
        
        serializable_analysis = decimal_to_float(tax_analysis)
        
        return Response({
            'status': 'success',
            'data': serializable_analysis
        })
        
    except Exception as e:
        logger.error(f"Error in automatic tax calculation API: {e}")
        return Response({
            'status': 'error',
            'message': 'Unable to calculate tax analysis'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_section_wise_analysis(request, section):
    """
    Get detailed analysis for a specific tax section
    """
    try:
        calculator = AutomaticTaxCalculator(request.user)
        
        section_methods = {
            '80C': calculator.calculate_section_80c_deductions,
            '80D': calculator.calculate_section_80d_deductions,
            '80G': calculator.calculate_section_80g_deductions,
            '24B': calculator.calculate_section_24b_deductions
        }
        
        if section not in section_methods:
            return Response({
                'status': 'error',
                'message': f'Invalid section: {section}'
            }, status=400)
        
        analysis = section_methods[section]()
        
        # Convert Decimal objects to float for JSON serialization
        def decimal_to_float(obj):
            if isinstance(obj, dict):
                return {k: decimal_to_float(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [decimal_to_float(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            else:
                return obj
        
        serializable_analysis = decimal_to_float(analysis)
        
        return Response({
            'status': 'success',
            'data': serializable_analysis
        })
        
    except Exception as e:
        logger.error(f"Error in section-wise analysis for {section}: {e}")
        return Response({
            'status': 'error',
            'message': f'Unable to analyze section {section}'
        }, status=500)


@login_required
def section_detail_view(request, section):
    """
    Detailed view for a specific tax section
    """
    try:
        calculator = AutomaticTaxCalculator(request.user)
        
        section_methods = {
            '80C': calculator.calculate_section_80c_deductions,
            '80D': calculator.calculate_section_80d_deductions,
            '80G': calculator.calculate_section_80g_deductions,
            '24B': calculator.calculate_section_24b_deductions
        }
        
        if section not in section_methods:
            return redirect('automatic_tax_dashboard')
        
        analysis = section_methods[section]()
        
        return render(request, 'tax_optimization/section_detail.html', {
            'section': section,
            'analysis': analysis,
            'user': request.user
        })
        
    except Exception as e:
        logger.error(f"Error in section detail view for {section}: {e}")
        return render(request, 'tax_optimization/section_detail.html', {
            'section': section,
            'error': f'Unable to analyze section {section}'
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_tax_calculation(request):
    """
    Save automatic tax calculation results to database
    """
    try:
        calculator = AutomaticTaxCalculator(request.user)
        tax_analysis = calculator.calculate_comprehensive_tax_savings()
        
        # Create or update tax calculation record
        tax_calculation, created = TaxCalculation.objects.get_or_create(
            user=request.user,
            financial_year=calculator.financial_year,
            defaults={
                'total_deductions': tax_analysis['summary']['total_eligible_deductions'],
                'tax_liability': Decimal('0'),  # This would be calculated separately
                'effective_tax_rate': Decimal('0'),
                'calculation_date': datetime.now(),
                'is_automatic': True
            }
        )
        
        if not created:
            # Update existing record
            tax_calculation.total_deductions = tax_analysis['summary']['total_eligible_deductions']
            tax_calculation.calculation_date = datetime.now()
            tax_calculation.is_automatic = True
            tax_calculation.save()
        
        return Response({
            'status': 'success',
            'message': 'Tax calculation saved successfully',
            'data': {
                'calculation_id': tax_calculation.id,
                'financial_year': calculator.financial_year,
                'total_deductions': float(tax_analysis['summary']['total_eligible_deductions'])
            }
        })
        
    except Exception as e:
        logger.error(f"Error saving tax calculation: {e}")
        return Response({
            'status': 'error',
            'message': 'Unable to save tax calculation'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tax_optimization_recommendations(request):
    """
    Get personalized tax optimization recommendations
    """
    try:
        calculator = AutomaticTaxCalculator(request.user)
        tax_analysis = calculator.calculate_comprehensive_tax_savings()
        
        # Extract recommendations from analysis
        all_recommendations = []
        
        # Section-wise recommendations
        for section, data in tax_analysis['deductions_by_section'].items():
            if 'recommendations' in data:
                section_recs = [{
                    'section': section,
                    'type': 'section_specific',
                    'recommendation': rec,
                    'priority': 'high' if 'maximize' in rec.lower() else 'medium'
                } for rec in data['recommendations']]
                all_recommendations.extend(section_recs)
        
        # Overall recommendations
        if 'recommendations' in tax_analysis:
            overall_recs = [{
                'section': 'overall',
                'type': 'general',
                'recommendation': rec,
                'priority': 'medium'
            } for rec in tax_analysis['recommendations']]
            all_recommendations.extend(overall_recs)
        
        return Response({
            'status': 'success',
            'data': {
                'recommendations': all_recommendations,
                'total_recommendations': len(all_recommendations),
                'financial_year': calculator.financial_year
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting tax optimization recommendations: {e}")
        return Response({
            'status': 'error',
            'message': 'Unable to get recommendations'
        }, status=500)

# End of views file