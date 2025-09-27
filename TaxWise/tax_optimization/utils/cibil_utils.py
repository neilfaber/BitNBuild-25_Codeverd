"""
CIBIL Score Calculation and Analysis Utilities
AI-powered credit score advisor with what-if scenario modeling
"""

import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
import random
import math

from django.db.models import Avg, Sum, Count, Max, Min
from django.utils import timezone

from ..models import (
    CreditProfile, CreditAccount, PaymentHistory, CreditScoreHistory,
    CreditScoreFactors, CreditImprovementRecommendation, CreditScoreWhatIfScenario
)


class CIBILScoreCalculator:
    """
    Advanced CIBIL Score calculation engine based on industry-standard factors
    """
    
    # CIBIL Score Factor Weights (based on real CIBIL methodology)
    WEIGHTS = {
        'payment_history': 0.35,      # 35% - Most important
        'credit_utilization': 0.30,   # 30% - Very important  
        'credit_history_length': 0.15, # 15% - Important
        'credit_mix': 0.10,           # 10% - Moderately important
        'recent_credit': 0.10         # 10% - Moderately important
    }
    
    # Score ranges for different factors
    SCORE_RANGES = {
        'excellent': (800, 900),
        'very_good': (750, 799),
        'good': (650, 749),
        'fair': (550, 649),
        'poor': (300, 549)
    }

    def __init__(self, credit_profile):
        self.credit_profile = credit_profile
        self.accounts = credit_profile.accounts.all()
        
    def calculate_comprehensive_score(self) -> Dict:
        """Calculate CIBIL score with detailed breakdown"""
        
        # Calculate individual factor scores
        payment_score = self._calculate_payment_history_score()
        utilization_score = self._calculate_credit_utilization_score()
        history_score = self._calculate_credit_history_score()
        mix_score = self._calculate_credit_mix_score()
        inquiry_score = self._calculate_recent_credit_score()
        
        # Calculate weighted final score
        final_score = (
            payment_score * self.WEIGHTS['payment_history'] +
            utilization_score * self.WEIGHTS['credit_utilization'] +
            history_score * self.WEIGHTS['credit_history_length'] +
            mix_score * self.WEIGHTS['credit_mix'] +
            inquiry_score * self.WEIGHTS['recent_credit']
        )
        
        # Ensure score is within valid range
        final_score = max(300, min(900, int(final_score)))
        
        return {
            'overall_score': final_score,
            'score_range': self._get_score_range(final_score),
            'factor_scores': {
                'payment_history': {
                    'score': payment_score,
                    'weight': self.WEIGHTS['payment_history'],
                    'contribution': payment_score * self.WEIGHTS['payment_history'],
                    'status': self._get_factor_status(payment_score)
                },
                'credit_utilization': {
                    'score': utilization_score,
                    'weight': self.WEIGHTS['credit_utilization'],
                    'contribution': utilization_score * self.WEIGHTS['credit_utilization'],
                    'status': self._get_factor_status(utilization_score)
                },
                'credit_history': {
                    'score': history_score,
                    'weight': self.WEIGHTS['credit_history_length'],
                    'contribution': history_score * self.WEIGHTS['credit_history_length'],
                    'status': self._get_factor_status(history_score)
                },
                'credit_mix': {
                    'score': mix_score,
                    'weight': self.WEIGHTS['credit_mix'],
                    'contribution': mix_score * self.WEIGHTS['credit_mix'],
                    'status': self._get_factor_status(mix_score)
                },
                'recent_credit': {
                    'score': inquiry_score,
                    'weight': self.WEIGHTS['recent_credit'],
                    'contribution': inquiry_score * self.WEIGHTS['recent_credit'],
                    'status': self._get_factor_status(inquiry_score)
                }
            },
            'improvement_areas': self._identify_improvement_areas({
                'payment_history': payment_score,
                'credit_utilization': utilization_score,
                'credit_history': history_score,
                'credit_mix': mix_score,
                'recent_credit': inquiry_score
            })
        }

    def _calculate_payment_history_score(self) -> float:
        """Calculate payment history score (35% weight)"""
        if self.credit_profile.payment_history_percentage >= 95:
            return 850
        elif self.credit_profile.payment_history_percentage >= 90:
            return 800
        elif self.credit_profile.payment_history_percentage >= 80:
            return 750
        elif self.credit_profile.payment_history_percentage >= 70:
            return 700
        elif self.credit_profile.payment_history_percentage >= 60:
            return 650
        elif self.credit_profile.payment_history_percentage >= 50:
            return 600
        else:
            return 500

    def _calculate_credit_utilization_score(self) -> float:
        """Calculate credit utilization score (30% weight)"""
        utilization = float(self.credit_profile.credit_utilization_ratio)
        
        if utilization <= 10:
            return 850
        elif utilization <= 30:
            return 800
        elif utilization <= 50:
            return 750
        elif utilization <= 70:
            return 700
        elif utilization <= 90:
            return 650
        else:
            return 600

    def _calculate_credit_history_score(self) -> float:
        """Calculate credit history length score (15% weight)"""
        history_months = self.credit_profile.credit_history_length
        
        if history_months >= 120:  # 10+ years
            return 850
        elif history_months >= 84:  # 7+ years
            return 800
        elif history_months >= 60:  # 5+ years
            return 750
        elif history_months >= 36:  # 3+ years
            return 700
        elif history_months >= 24:  # 2+ years
            return 650
        elif history_months >= 12:  # 1+ year
            return 600
        else:
            return 550

    def _calculate_credit_mix_score(self) -> float:
        """Calculate credit mix diversity score (10% weight)"""
        total_types = (
            (1 if self.credit_profile.credit_cards > 0 else 0) +
            (1 if self.credit_profile.personal_loans > 0 else 0) +
            (1 if self.credit_profile.home_loans > 0 else 0) +
            (1 if self.credit_profile.auto_loans > 0 else 0) +
            (1 if self.credit_profile.other_loans > 0 else 0)
        )
        
        if total_types >= 4:
            return 850
        elif total_types == 3:
            return 800
        elif total_types == 2:
            return 750
        elif total_types == 1:
            return 700
        else:
            return 650

    def _calculate_recent_credit_score(self) -> float:
        """Calculate recent credit inquiries score (10% weight)"""
        inquiries_6m = self.credit_profile.hard_inquiries_6_months
        inquiries_12m = self.credit_profile.hard_inquiries_12_months
        
        if inquiries_6m == 0 and inquiries_12m <= 1:
            return 850
        elif inquiries_6m <= 1 and inquiries_12m <= 3:
            return 800
        elif inquiries_6m <= 2 and inquiries_12m <= 5:
            return 750
        elif inquiries_6m <= 3 and inquiries_12m <= 7:
            return 700
        else:
            return 650

    def _get_score_range(self, score: int) -> str:
        """Get score range category"""
        for range_name, (min_score, max_score) in self.SCORE_RANGES.items():
            if min_score <= score <= max_score:
                return range_name.upper()
        return 'UNKNOWN'

    def _get_factor_status(self, score: float) -> str:
        """Get factor performance status"""
        if score >= 800:
            return 'EXCELLENT'
        elif score >= 750:
            return 'VERY_GOOD'
        elif score >= 700:
            return 'GOOD'
        elif score >= 650:
            return 'FAIR'
        else:
            return 'POOR'

    def _identify_improvement_areas(self, factor_scores: Dict) -> List[str]:
        """Identify areas that need the most improvement"""
        improvement_areas = []
        
        for factor, score in factor_scores.items():
            if score < 700:
                improvement_areas.append(factor)
        
        # Sort by lowest scores first
        improvement_areas.sort(key=lambda x: factor_scores[x])
        
        return improvement_areas


class CIBILRecommendationEngine:
    """
    AI-powered recommendation engine for CIBIL score improvement
    """
    
    def __init__(self, credit_profile):
        self.credit_profile = credit_profile
        self.calculator = CIBILScoreCalculator(credit_profile)
        
    def generate_recommendations(self) -> List[Dict]:
        """Generate personalized CIBIL improvement recommendations"""
        
        score_analysis = self.calculator.calculate_comprehensive_score()
        recommendations = []
        
        # Payment History Recommendations
        if score_analysis['factor_scores']['payment_history']['score'] < 750:
            recommendations.extend(self._get_payment_history_recommendations())
            
        # Credit Utilization Recommendations  
        if score_analysis['factor_scores']['credit_utilization']['score'] < 750:
            recommendations.extend(self._get_utilization_recommendations())
            
        # Credit History Recommendations
        if score_analysis['factor_scores']['credit_history']['score'] < 750:
            recommendations.extend(self._get_credit_history_recommendations())
            
        # Credit Mix Recommendations
        if score_analysis['factor_scores']['credit_mix']['score'] < 750:
            recommendations.extend(self._get_credit_mix_recommendations())
            
        # Recent Credit Recommendations
        if score_analysis['factor_scores']['recent_credit']['score'] < 750:
            recommendations.extend(self._get_recent_credit_recommendations())
        
        # Sort by expected impact
        recommendations.sort(key=lambda x: x['expected_score_improvement'], reverse=True)
        
        return recommendations

    def _get_payment_history_recommendations(self) -> List[Dict]:
        """Get payment history improvement recommendations"""
        recommendations = []
        
        payment_percent = self.credit_profile.payment_history_percentage
        
        if payment_percent < 95:
            recommendations.append({
                'category': 'PAYMENT_BEHAVIOR',
                'title': 'Set Up Automatic Payments',
                'description': 'Set up autopay for at least the minimum amount on all credit cards and loans to ensure you never miss a payment.',
                'action_steps': [
                    'Contact your bank to set up autopay',
                    'Choose minimum payment or full payment option',
                    'Set autopay date 3-5 days before due date',
                    'Monitor account regularly for sufficient balance'
                ],
                'expected_score_improvement': 50,
                'timeframe_months': 3,
                'priority': 'CRITICAL',
                'is_easy_to_implement': True,
                'cost_involved': 0,
                'ai_confidence': 0.9
            })
        
        if self.credit_profile.late_payments > 0:
            recommendations.append({
                'category': 'PAYMENT_BEHAVIOR',
                'title': 'Contact Creditors for Goodwill Deletions',
                'description': 'If you have a good payment history overall, contact creditors to request removal of late payment marks as a goodwill gesture.',
                'action_steps': [
                    'Identify accounts with late payments',
                    'Write goodwill letters to creditors',
                    'Explain circumstances and show improved payment behavior',
                    'Follow up after 30 days if no response'
                ],
                'expected_score_improvement': 30,
                'timeframe_months': 2,
                'priority': 'HIGH',
                'is_easy_to_implement': True,
                'cost_involved': 0,
                'ai_confidence': 0.7
            })
        
        return recommendations

    def _get_utilization_recommendations(self) -> List[Dict]:
        """Get credit utilization improvement recommendations"""
        recommendations = []
        
        utilization = float(self.credit_profile.credit_utilization_ratio)
        
        if utilization > 30:
            recommendations.append({
                'category': 'CREDIT_UTILIZATION',
                'title': 'Reduce Credit Card Balances Below 30%',
                'description': f'Your current utilization is {utilization}%. Reduce it to below 30% for significant score improvement.',
                'action_steps': [
                    'Calculate 30% of total credit limit',
                    'Pay down highest utilization cards first',
                    'Consider multiple payments per month',
                    'Track utilization regularly'
                ],
                'expected_score_improvement': 40,
                'timeframe_months': 2,
                'priority': 'HIGH',
                'is_easy_to_implement': True,
                'cost_involved': float(self.credit_profile.total_outstanding * Decimal('0.3')),
                'ai_confidence': 0.85
            })
        
        if utilization > 10:
            recommendations.append({
                'category': 'CREDIT_UTILIZATION',
                'title': 'Request Credit Limit Increases',
                'description': 'Increasing your credit limits without increasing balances will improve your utilization ratio.',
                'action_steps': [
                    'Contact credit card companies',
                    'Request limit increases on cards with good payment history',
                    'Avoid using the additional credit',
                    'Wait 6 months between requests'
                ],
                'expected_score_improvement': 25,
                'timeframe_months': 1,
                'priority': 'MEDIUM',
                'is_easy_to_implement': True,
                'cost_involved': 0,
                'ai_confidence': 0.75
            })
        
        return recommendations

    def _get_credit_history_recommendations(self) -> List[Dict]:
        """Get credit history length recommendations"""
        recommendations = []
        
        history_months = self.credit_profile.credit_history_length
        
        if history_months < 60:  # Less than 5 years
            recommendations.append({
                'category': 'ACCOUNT_MANAGEMENT',
                'title': 'Keep Old Credit Cards Active',
                'description': 'Keep your oldest credit cards open and use them occasionally to maintain credit history length.',
                'action_steps': [
                    'Identify your oldest credit cards',
                    'Make small purchases monthly',
                    'Pay off balances immediately',
                    'Avoid closing old accounts'
                ],
                'expected_score_improvement': 15,
                'timeframe_months': 12,
                'priority': 'MEDIUM',
                'is_easy_to_implement': True,
                'cost_involved': 0,
                'ai_confidence': 0.8
            })
        
        return recommendations

    def _get_credit_mix_recommendations(self) -> List[Dict]:
        """Get credit mix improvement recommendations"""
        recommendations = []
        
        total_types = (
            (1 if self.credit_profile.credit_cards > 0 else 0) +
            (1 if self.credit_profile.personal_loans > 0 else 0) +
            (1 if self.credit_profile.home_loans > 0 else 0) +
            (1 if self.credit_profile.auto_loans > 0 else 0) +
            (1 if self.credit_profile.other_loans > 0 else 0)
        )
        
        if total_types < 2:
            recommendations.append({
                'category': 'CREDIT_MIX',
                'title': 'Diversify Your Credit Portfolio',
                'description': 'Having different types of credit accounts shows you can manage various forms of credit responsibly.',
                'action_steps': [
                    'Consider a small personal loan if you only have credit cards',
                    'Look into a secured credit card if you only have loans',
                    'Make payments on time for all account types',
                    'Avoid taking unnecessary credit just for mix'
                ],
                'expected_score_improvement': 20,
                'timeframe_months': 6,
                'priority': 'LOW',
                'is_easy_to_implement': False,
                'cost_involved': 0,
                'ai_confidence': 0.65
            })
        
        return recommendations

    def _get_recent_credit_recommendations(self) -> List[Dict]:
        """Get recent credit inquiry recommendations"""
        recommendations = []
        
        inquiries_6m = self.credit_profile.hard_inquiries_6_months
        
        if inquiries_6m > 2:
            recommendations.append({
                'category': 'CREDIT_INQUIRIES',
                'title': 'Limit New Credit Applications',
                'description': f'You have {inquiries_6m} hard inquiries in the last 6 months. Avoid new credit applications for a while.',
                'action_steps': [
                    'Avoid applying for new credit cards or loans',
                    'Wait at least 6 months between applications',
                    'Use soft inquiry tools to check your eligibility first',
                    'Focus on improving existing accounts'
                ],
                'expected_score_improvement': 15,
                'timeframe_months': 6,
                'priority': 'MEDIUM',
                'is_easy_to_implement': True,
                'cost_involved': 0,
                'ai_confidence': 0.8
            })
        
        return recommendations


class CIBILWhatIfAnalyzer:
    """
    What-if scenario analyzer for CIBIL score predictions
    """
    
    def __init__(self, credit_profile):
        self.credit_profile = credit_profile
        self.calculator = CIBILScoreCalculator(credit_profile)
        
    def analyze_scenario(self, scenario_params: Dict) -> Dict:
        """Analyze a what-if scenario and predict score changes"""
        
        # Create a copy of current credit profile
        modified_profile = self._create_modified_profile(scenario_params)
        
        # Calculate new score with modified profile
        modified_calculator = CIBILScoreCalculator(modified_profile)
        new_analysis = modified_calculator.calculate_comprehensive_score()
        
        # Get current score for comparison
        current_analysis = self.calculator.calculate_comprehensive_score()
        
        return {
            'scenario_name': scenario_params.get('name', 'Custom Scenario'),
            'current_score': current_analysis['overall_score'],
            'predicted_score': new_analysis['overall_score'],
            'score_improvement': new_analysis['overall_score'] - current_analysis['overall_score'],
            'current_factors': current_analysis['factor_scores'],
            'predicted_factors': new_analysis['factor_scores'],
            'confidence_level': self._calculate_confidence(scenario_params),
            'timeframe_months': scenario_params.get('timeframe_months', 6),
            'implementation_difficulty': self._assess_difficulty(scenario_params)
        }

    def _create_modified_profile(self, scenario_params: Dict):
        """Create a modified credit profile based on scenario parameters"""
        # This would create a copy of the credit profile with modifications
        # For simulation purposes, we'll modify key attributes
        
        modified_profile = self.credit_profile
        
        # Apply scenario modifications
        if scenario_params.get('improve_payments', False):
            modified_profile.payment_history_percentage = 100
            modified_profile.late_payments = 0
            modified_profile.missed_payments = 0
            
        if 'target_utilization' in scenario_params:
            modified_profile.credit_utilization_ratio = Decimal(str(scenario_params['target_utilization']))
            
        if 'increase_credit_limit' in scenario_params:
            increase = Decimal(str(scenario_params['increase_credit_limit']))
            modified_profile.total_credit_limit += increase
            # Recalculate utilization
            if modified_profile.total_credit_limit > 0:
                modified_profile.credit_utilization_ratio = (
                    modified_profile.total_outstanding / modified_profile.total_credit_limit * 100
                )
                
        if 'wait_months' in scenario_params:
            # Simulate natural improvement over time
            months = scenario_params['wait_months']
            modified_profile.credit_history_length += months
            
        return modified_profile

    def _calculate_confidence(self, scenario_params: Dict) -> float:
        """Calculate confidence level for the scenario prediction"""
        base_confidence = 0.8
        
        # Reduce confidence for more complex scenarios
        if len(scenario_params) > 3:
            base_confidence -= 0.1
            
        # Reduce confidence for long timeframes
        if scenario_params.get('timeframe_months', 0) > 12:
            base_confidence -= 0.1
            
        return max(0.5, base_confidence)

    def _assess_difficulty(self, scenario_params: Dict) -> str:
        """Assess implementation difficulty"""
        if scenario_params.get('cost_involved', 0) > 50000:
            return 'HIGH'
        elif len(scenario_params) > 2:
            return 'MEDIUM' 
        else:
            return 'LOW'

    def generate_common_scenarios(self) -> List[Dict]:
        """Generate common what-if scenarios"""
        scenarios = []
        
        # Scenario 1: Perfect payment history
        scenarios.append(self.analyze_scenario({
            'name': 'Perfect Payment History',
            'improve_payments': True,
            'timeframe_months': 6
        }))
        
        # Scenario 2: Reduce utilization to 10%
        current_utilization = float(self.credit_profile.credit_utilization_ratio)
        if current_utilization > 10:
            scenarios.append(self.analyze_scenario({
                'name': 'Reduce Utilization to 10%',
                'target_utilization': 10,
                'timeframe_months': 2
            }))
        
        # Scenario 3: Increase credit limit by 50%
        scenarios.append(self.analyze_scenario({
            'name': 'Increase Credit Limits by 50%',
            'increase_credit_limit': float(self.credit_profile.total_credit_limit * Decimal('0.5')),
            'timeframe_months': 1
        }))
        
        # Scenario 4: Wait and let time improve score
        scenarios.append(self.analyze_scenario({
            'name': 'Natural Improvement (12 months)',
            'wait_months': 12,
            'timeframe_months': 12
        }))
        
        # Scenario 5: Combined approach
        scenarios.append(self.analyze_scenario({
            'name': 'Combined Approach',
            'improve_payments': True,
            'target_utilization': 10,
            'timeframe_months': 6
        }))
        
        return scenarios


def analyze_credit_from_financial_data(user, transactions) -> Dict:
    """
    Analyze credit behavior from financial transaction data
    This simulates extracting credit patterns from bank statements
    """
    
    # Identify credit-related transactions
    credit_transactions = []
    emi_payments = []
    credit_card_payments = []
    
    for transaction in transactions:
        description_lower = transaction.description.lower()
        
        # Identify EMI payments
        if any(keyword in description_lower for keyword in ['emi', 'loan', 'equitas', 'hdfc loan', 'sbi loan']):
            emi_payments.append(transaction)
            
        # Identify credit card payments
        if any(keyword in description_lower for keyword in ['credit card', 'cc payment', 'card payment']):
            credit_card_payments.append(transaction)
    
    # Calculate payment regularity
    total_expected_payments = len(set([t.date.replace(day=1) for t in emi_payments + credit_card_payments]))
    actual_payments = len(emi_payments) + len(credit_card_payments)
    
    payment_regularity = (actual_payments / max(total_expected_payments, 1)) * 100
    
    # Estimate credit utilization from spending patterns
    monthly_credit_spending = {}
    monthly_payments = {}
    
    for transaction in transactions:
        month = transaction.date.replace(day=1)
        
        if transaction.transaction_type == 'EXPENSE' and transaction.amount > 500:
            # Assume larger expenses might be on credit
            if month not in monthly_credit_spending:
                monthly_credit_spending[month] = 0
            monthly_credit_spending[month] += float(transaction.amount)
            
        if transaction in credit_card_payments:
            if month not in monthly_payments:
                monthly_payments[month] = 0
            monthly_payments[month] += float(transaction.amount)
    
    # Estimate utilization (simplified)
    avg_spending = sum(monthly_credit_spending.values()) / max(len(monthly_credit_spending), 1)
    avg_payments = sum(monthly_payments.values()) / max(len(monthly_payments), 1)
    
    estimated_utilization = max(0, min(100, ((avg_spending - avg_payments) / avg_spending * 100) if avg_spending > 0 else 0))
    
    return {
        'payment_regularity': payment_regularity,
        'estimated_utilization': estimated_utilization,
        'emi_payment_count': len(emi_payments),
        'credit_card_payment_count': len(credit_card_payments),
        'avg_monthly_emi': sum([float(t.amount) for t in emi_payments]) / max(len(emi_payments), 1) if emi_payments else 0,
        'credit_discipline_score': min(100, payment_regularity * 0.6 + (100 - estimated_utilization) * 0.4)
    }