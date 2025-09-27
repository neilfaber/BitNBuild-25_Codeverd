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
    TaxOptimizationRecommendation, FileUpload
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