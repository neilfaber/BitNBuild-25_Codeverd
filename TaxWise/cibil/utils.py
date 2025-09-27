# cibil/utils.py
import math
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Avg, Count, Q, Sum, Max, Min, F
from django.utils import timezone
from typing import Dict, List, Tuple, Optional

from .models import (
    CibilProfile, CreditAccount, PaymentHistory, 
    CibilScoreHistory, CibilRecommendation, WhatIfScenario,
    CreditInquiry
)

# ==================== CIBIL SCORE CALCULATOR ====================

class CibilScoreCalculator:
    """
    Advanced CIBIL score calculation engine based on industry standards
    """
    
    # CIBIL Score Factor Weights (industry standard approximation)
    PAYMENT_HISTORY_WEIGHT = 0.35      # 35% - Most important
    CREDIT_UTILIZATION_WEIGHT = 0.30   # 30% - Second most important
    CREDIT_HISTORY_LENGTH_WEIGHT = 0.15 # 15% - Age of accounts
    CREDIT_MIX_WEIGHT = 0.10           # 10% - Types of credit
    NEW_CREDIT_WEIGHT = 0.10           # 10% - Recent inquiries
    
    # Score ranges
    MIN_SCORE = 300
    MAX_SCORE = 900
    
    def __init__(self, cibil_profile):
        self.profile = cibil_profile
        self.credit_accounts = CreditAccount.objects.filter(cibil_profile=cibil_profile)
        self.active_accounts = self.credit_accounts.filter(account_status='ACTIVE')
        self.factor_scores = {}
        self.factor_breakdown = {}
    
    def calculate_comprehensive_score(self) -> int:
        """Calculate comprehensive CIBIL score based on all factors"""
        if not self.active_accounts.exists():
            return self.MIN_SCORE  # No credit history
        
        # Calculate individual factor scores
        payment_score = self._calculate_payment_history_factor()
        utilization_score = self._calculate_credit_utilization_factor()
        history_score = self._calculate_credit_history_length_factor()
        mix_score = self._calculate_credit_mix_factor()
        inquiry_score = self._calculate_new_credit_factor()
        
        # Store factor scores for analysis
        self.factor_scores = {
            'payment_history': payment_score,
            'credit_utilization': utilization_score,
            'credit_history_length': history_score,
            'credit_mix': mix_score,
            'new_credit': inquiry_score
        }
        
        # Calculate weighted total score
        total_score = (
            payment_score * self.PAYMENT_HISTORY_WEIGHT +
            utilization_score * self.CREDIT_UTILIZATION_WEIGHT +
            history_score * self.CREDIT_HISTORY_LENGTH_WEIGHT +
            mix_score * self.CREDIT_MIX_WEIGHT +
            inquiry_score * self.NEW_CREDIT_WEIGHT
        )
        
        # Normalize to CIBIL range (300-900)
        final_score = int(self.MIN_SCORE + (total_score / 100) * (self.MAX_SCORE - self.MIN_SCORE))
        
        return max(self.MIN_SCORE, min(self.MAX_SCORE, final_score))
    
    def _calculate_payment_history_factor(self) -> float:
        """Calculate payment history factor (35% of score)"""
        # Get payment history for last 24 months (more weight to recent payments)
        two_years_ago = date.today() - timedelta(days=730)
        recent_payments = PaymentHistory.objects.filter(
            credit_account__cibil_profile=self.profile,
            payment_date__gte=two_years_ago
        )
        
        if not recent_payments.exists():
            return 50.0  # Average score for no history
        
        # Calculate on-time payment percentage
        total_payments = recent_payments.count()
        on_time_payments = recent_payments.filter(payment_status='ON_TIME').count()
        
        # Weight recent payments (last 6 months) more heavily
        six_months_ago = date.today() - timedelta(days=180)
        recent_6m = recent_payments.filter(payment_date__gte=six_months_ago)
        
        if recent_6m.exists():
            recent_on_time = recent_6m.filter(payment_status='ON_TIME').count()
            recent_total = recent_6m.count()
            recent_percentage = recent_on_time / recent_total
            overall_percentage = on_time_payments / total_payments
            
            # 70% weight to recent, 30% to overall
            weighted_percentage = (recent_percentage * 0.7) + (overall_percentage * 0.3)
        else:
            weighted_percentage = on_time_payments / total_payments
        
        # Penalize severely late payments
        severely_late = recent_payments.filter(
            payment_status__in=['90_DAYS_LATE', '120_DAYS_LATE']
        ).count()
        late_penalty = min(30, severely_late * 5)  # -5 points per severely late payment
        
        # Convert to 0-100 scale
        base_score = weighted_percentage * 100
        final_score = max(0, base_score - late_penalty)
        
        self.factor_breakdown['payment_history'] = {
            'on_time_percentage': round(weighted_percentage * 100, 1),
            'total_payments': total_payments,
            'severely_late_payments': severely_late,
            'score': round(final_score, 1)
        }
        
        return final_score
    
    def _calculate_credit_utilization_factor(self) -> float:
        """Calculate credit utilization factor (30% of score)"""
        revolving_accounts = self.active_accounts.filter(
            account_type__in=['CREDIT_CARD', 'OVERDRAFT']
        )
        
        if not revolving_accounts.exists():
            return 70.0  # Neutral score for no revolving credit
        
        # Calculate overall utilization
        total_limit = sum(
            acc.credit_limit or 0 for acc in revolving_accounts 
            if acc.credit_limit
        )
        total_balance = sum(acc.current_balance for acc in revolving_accounts)
        
        if total_limit == 0:
            return 50.0  # No credit limit data
        
        overall_utilization = (total_balance / total_limit) * 100
        
        # Calculate per-account utilization penalties
        high_util_accounts = sum(
            1 for acc in revolving_accounts 
            if acc.credit_utilization > 30
        )
        maxed_out_accounts = sum(
            1 for acc in revolving_accounts 
            if acc.credit_utilization > 90
        )
        
        # Scoring logic (lower utilization = higher score)
        if overall_utilization <= 10:
            base_score = 95
        elif overall_utilization <= 30:
            base_score = 85 - (overall_utilization - 10) * 1.5
        elif overall_utilization <= 50:
            base_score = 55 - (overall_utilization - 30) * 1.0
        elif overall_utilization <= 75:
            base_score = 35 - (overall_utilization - 50) * 0.8
        else:
            base_score = 15 - (overall_utilization - 75) * 0.4
        
        # Apply penalties
        penalty = (high_util_accounts * 5) + (maxed_out_accounts * 10)
        final_score = max(0, base_score - penalty)
        
        self.factor_breakdown['credit_utilization'] = {
            'overall_utilization': round(overall_utilization, 1),
            'high_util_accounts': high_util_accounts,
            'maxed_out_accounts': maxed_out_accounts,
            'score': round(final_score, 1)
        }
        
        return final_score
    
    def _calculate_credit_history_length_factor(self) -> float:
        """Calculate credit history length factor (15% of score)"""
        if not self.credit_accounts.exists():
            return 20.0  # Very low score for no history
        
        # Find oldest account
        oldest_date = self.credit_accounts.aggregate(
            oldest=Min('account_opened_date')
        )['oldest']
        
        if not oldest_date:
            return 20.0
        
        # Calculate age in months
        today = date.today()
        months_diff = (today.year - oldest_date.year) * 12 + today.month - oldest_date.month
        
        # Calculate average age of accounts
        total_months = 0
        account_count = 0
        
        for account in self.credit_accounts:
            if account.account_opened_date:
                acc_months = (today.year - account.account_opened_date.year) * 12 + \
                           today.month - account.account_opened_date.month
                total_months += acc_months
                account_count += 1
        
        avg_age_months = total_months / account_count if account_count > 0 else 0
        
        # Scoring logic
        oldest_years = months_diff / 12
        avg_years = avg_age_months / 12
        
        if oldest_years >= 15:
            oldest_score = 100
        elif oldest_years >= 10:
            oldest_score = 85 + (oldest_years - 10) * 3
        elif oldest_years >= 5:
            oldest_score = 60 + (oldest_years - 5) * 5
        elif oldest_years >= 2:
            oldest_score = 30 + (oldest_years - 2) * 10
        else:
            oldest_score = oldest_years * 15
        
        if avg_years >= 10:
            avg_score = 100
        elif avg_years >= 5:
            avg_score = 70 + (avg_years - 5) * 6
        elif avg_years >= 2:
            avg_score = 40 + (avg_years - 2) * 10
        else:
            avg_score = avg_years * 20
        
        # Weight oldest account more heavily
        final_score = (oldest_score * 0.6) + (avg_score * 0.4)
        
        self.factor_breakdown['credit_history_length'] = {
            'oldest_account_years': round(oldest_years, 1),
            'average_age_years': round(avg_years, 1),
            'score': round(final_score, 1)
        }
        
        return final_score
    
    def _calculate_credit_mix_factor(self) -> float:
        """Calculate credit mix factor (10% of score)"""
        account_types = set(self.active_accounts.values_list('account_type', flat=True))
        
        # Define credit categories
        revolving_types = {'CREDIT_CARD', 'OVERDRAFT'}
        installment_types = {
            'PERSONAL_LOAN', 'HOME_LOAN', 'AUTO_LOAN', 
            'EDUCATION_LOAN', 'BUSINESS_LOAN', 'GOLD_LOAN'
        }
        
        has_revolving = bool(account_types & revolving_types)
        has_installment = bool(account_types & installment_types)
        
        total_types = len(account_types)
        
        # Scoring logic
        if has_revolving and has_installment and total_types >= 3:
            score = 95  # Excellent mix
        elif has_revolving and has_installment:
            score = 80  # Good mix
        elif has_revolving or has_installment:
            score = 60  # Limited but some mix
        elif total_types >= 2:
            score = 50  # Some variety
        elif total_types == 1:
            score = 30  # Single type
        else:
            score = 10  # No active accounts
        
        self.factor_breakdown['credit_mix'] = {
            'total_account_types': total_types,
            'has_revolving_credit': has_revolving,
            'has_installment_credit': has_installment,
            'account_types': list(account_types),
            'score': score
        }
        
        return float(score)
    
    def _calculate_new_credit_factor(self) -> float:
        """Calculate new credit inquiries factor (10% of score)"""
        # Get hard inquiries from last 24 months
        two_years_ago = date.today() - timedelta(days=730)
        hard_inquiries = CreditInquiry.objects.filter(
            cibil_profile=self.profile,
            inquiry_type='HARD',
            inquiry_date__gte=two_years_ago
        )
        
        # Weight recent inquiries more heavily
        six_months_ago = date.today() - timedelta(days=180)
        recent_inquiries = hard_inquiries.filter(inquiry_date__gte=six_months_ago)
        older_inquiries = hard_inquiries.filter(inquiry_date__lt=six_months_ago)
        
        # Calculate weighted inquiry count
        weighted_inquiries = (recent_inquiries.count() * 1.5) + (older_inquiries.count() * 0.8)
        
        # Check for new accounts opened recently
        new_accounts = self.active_accounts.filter(
            account_opened_date__gte=six_months_ago
        ).count()
        
        # Scoring logic (fewer inquiries = higher score)
        if weighted_inquiries == 0:
            base_score = 90
        elif weighted_inquiries <= 2:
            base_score = 80 - (weighted_inquiries * 5)
        elif weighted_inquiries <= 5:
            base_score = 70 - ((weighted_inquiries - 2) * 8)
        elif weighted_inquiries <= 10:
            base_score = 46 - ((weighted_inquiries - 5) * 5)
        else:
            base_score = max(5, 21 - ((weighted_inquiries - 10) * 2))
        
        # Penalty for too many new accounts
        new_account_penalty = min(20, new_accounts * 8)
        final_score = max(0, base_score - new_account_penalty)
        
        self.factor_breakdown['new_credit'] = {
            'hard_inquiries_24m': hard_inquiries.count(),
            'hard_inquiries_6m': recent_inquiries.count(),
            'new_accounts_6m': new_accounts,
            'weighted_inquiry_score': round(weighted_inquiries, 1),
            'score': round(final_score, 1)
        }
        
        return final_score
    
    def calculate_scenario_score(self, scenario_data: dict) -> int:
        """Calculate projected score for a what-if scenario"""
        # Start with current calculated score
        base_score = self.calculate_comprehensive_score()
        
        # Apply scenario modifications
        score_adjustment = 0
        
        # Credit utilization changes
        if 'target_credit_utilization' in scenario_data:
            target_util = float(scenario_data['target_credit_utilization'])
            current_util = self._get_current_utilization()
            
            if target_util < current_util:
                # Improvement in utilization
                util_improvement = current_util - target_util
                if util_improvement >= 20:
                    score_adjustment += 40
                elif util_improvement >= 10:
                    score_adjustment += 25
                elif util_improvement >= 5:
                    score_adjustment += 15
                else:
                    score_adjustment += util_improvement * 2
        
        # Payment behavior improvements
        if 'target_on_time_percentage' in scenario_data:
            target_payment = float(scenario_data['target_on_time_percentage'])
            current_payment = self._get_current_payment_percentage()
            
            if target_payment > current_payment:
                payment_improvement = target_payment - current_payment
                score_adjustment += payment_improvement * 0.8
        
        # New accounts impact
        if 'new_accounts_to_add' in scenario_data:
            new_accounts = int(scenario_data['new_accounts_to_add'])
            if new_accounts > 0:
                score_adjustment -= new_accounts * 8  # Temporary negative impact
        
        # Account closure impact
        if 'accounts_to_close' in scenario_data:
            accounts_to_close = int(scenario_data['accounts_to_close'])
            if accounts_to_close > 0:
                score_adjustment -= accounts_to_close * 12  # Negative impact
        
        # Debt reduction impact
        if 'debt_reduction_amount' in scenario_data:
            debt_reduction = float(scenario_data['debt_reduction_amount'])
            current_balance = sum(acc.current_balance for acc in self.active_accounts)
            
            if debt_reduction > 0 and current_balance > 0:
                reduction_percentage = (debt_reduction / current_balance) * 100
                score_adjustment += min(50, reduction_percentage * 0.6)
        
        projected_score = base_score + int(score_adjustment)
        return max(self.MIN_SCORE, min(self.MAX_SCORE, projected_score))
    
    def estimate_time_to_achieve(self, target_score: int) -> int:
        """Estimate months needed to achieve target score"""
        current_score = self.profile.current_score or self.calculate_comprehensive_score()
        score_gap = target_score - current_score
        
        if score_gap <= 0:
            return 0
        
        # Base timeline estimation
        if score_gap <= 25:
            return 3  # 3 months
        elif score_gap <= 50:
            return 6  # 6 months
        elif score_gap <= 100:
            return 12  # 12 months
        elif score_gap <= 150:
            return 18  # 18 months
        else:
            return 24  # 24+ months
    
    def get_factor_breakdown(self) -> dict:
        """Get detailed breakdown of score factors"""
        return self.factor_breakdown
    
    def _get_current_utilization(self) -> float:
        """Get current overall credit utilization"""
        revolving_accounts = self.active_accounts.filter(
            account_type__in=['CREDIT_CARD', 'OVERDRAFT']
        )
        
        total_limit = sum(acc.credit_limit or 0 for acc in revolving_accounts)
        total_balance = sum(acc.current_balance for acc in revolving_accounts)
        
        return (total_balance / total_limit * 100) if total_limit > 0 else 0
    
    def _get_current_payment_percentage(self) -> float:
        """Get current on-time payment percentage"""
        six_months_ago = date.today() - timedelta(days=180)
        recent_payments = PaymentHistory.objects.filter(
            credit_account__cibil_profile=self.profile,
            payment_date__gte=six_months_ago
        )
        
        if not recent_payments.exists():
            return 100.0  # Assume good if no history
        
        on_time = recent_payments.filter(payment_status='ON_TIME').count()
        total = recent_payments.count()
        
        return (on_time / total * 100) if total > 0 else 100.0

# ==================== RECOMMENDATION ENGINE ====================

class RecommendationEngine:
    """
    AI-powered recommendation engine for CIBIL score improvement
    """
    
    def __init__(self, cibil_profile):
        self.profile = cibil_profile
        self.calculator = CibilScoreCalculator(cibil_profile)
        self.current_score = cibil_profile.current_score or self.calculator.calculate_comprehensive_score()
    
    def generate_recommendations(self) -> List[Dict]:
        """Generate personalized recommendations"""
        try:
            if not self.profile:
                raise ValueError("CIBIL profile is required")
                
            recommendations = []
            
            # Calculate factor scores for analysis
            self.calculator.calculate_comprehensive_score()
            factor_breakdown = self.calculator.get_factor_breakdown()
            
            if not factor_breakdown:
                raise ValueError("Unable to calculate score factors")
                
            # Generate recommendations...
            recommendations.extend(self._generate_payment_recommendations(factor_breakdown))
            recommendations.extend(self._generate_utilization_recommendations(factor_breakdown))
            recommendations.extend(self._generate_history_recommendations(factor_breakdown))
            recommendations.extend(self._generate_mix_recommendations(factor_breakdown))
            recommendations.extend(self._generate_inquiry_recommendations(factor_breakdown))
            
            # Save recommendations
            if recommendations:
                self._save_recommendations(recommendations)
                
            return recommendations
            
        except Exception as e:
            print(f"Error generating recommendations: {str(e)}")
            return []
    
    def _generate_payment_recommendations(self, factor_breakdown: dict) -> List[Dict]:
        """Generate payment behavior recommendations"""
        recommendations = []
        payment_data = factor_breakdown.get('payment_history', {})
        on_time_percentage = payment_data.get('on_time_percentage', 100)
        
        if on_time_percentage < 95:
            recommendations.append({
                'type': 'PAYMENT_BEHAVIOR',
                'priority': 'HIGH',
                'title': 'Set Up Automatic Payments',
                'description': f'Your on-time payment rate is {on_time_percentage:.1f}%. Setting up auto-pay for at least minimum amounts will improve your payment history.',
                'impact': min(50, int((95 - on_time_percentage) * 1.2)),
                'timeline': '1-3 months',
                'action_steps': [
                    'Set up auto-pay for minimum amounts on all credit cards',
                    'Set up auto-pay for EMI accounts',
                    'Set payment date 2-3 days before due date',
                    'Monitor auto-payments monthly'
                ]
            })
        
        if on_time_percentage < 85:
            recommendations.append({
                'type': 'PAYMENT_BEHAVIOR',
                'priority': 'HIGH',
                'title': 'Clear All Overdue Amounts Immediately',
                'description': 'You have late payments affecting your score significantly. Clear all overdue amounts and maintain consistency.',
                'impact': min(60, int((85 - on_time_percentage) * 1.5)),
                'timeline': 'Immediate',
                'action_steps': [
                    'List all accounts with overdue amounts',
                    'Pay all overdue amounts immediately',
                    'Call banks to request goodwill adjustments',
                    'Set up payment reminders'
                ]
            })
        
        return recommendations
    
    def _generate_utilization_recommendations(self, factor_breakdown: dict) -> List[Dict]:
        """Generate credit utilization recommendations"""
        recommendations = []
        util_data = factor_breakdown.get('credit_utilization', {})
        overall_util = util_data.get('overall_utilization', 0)
        high_util_accounts = util_data.get('high_util_accounts', 0)
        
        if overall_util > 30:
            recommendations.append({
                'type': 'CREDIT_UTILIZATION',
                'priority': 'HIGH',
                'title': 'Reduce Credit Utilization Below 30%',
                'description': f'Your credit utilization is {overall_util:.1f}%. Reducing it below 30% will significantly improve your score.',
                'impact': min(45, int((overall_util - 30) * 1.8)),
                'timeline': '2-4 months',
                'action_steps': [
                    'Pay down high-balance credit cards first',
                    'Consider balance transfer to lower-rate cards',
                    'Make multiple payments per month',
                    'Request credit limit increases on existing cards'
                ]
            })
        
        if overall_util > 10 and overall_util <= 30:
            recommendations.append({
                'type': 'CREDIT_UTILIZATION',
                'priority': 'MEDIUM',
                'title': 'Optimize Credit Utilization Below 10%',
                'description': f'Your utilization of {overall_util:.1f}% is good, but reducing it below 10% can boost your score further.',
                'impact': min(25, int((overall_util - 10) * 1.2)),
                'timeline': '3-6 months',
                'action_steps': [
                    'Pay down balances strategically',
                    'Time payments before statement closing',
                    'Spread balances across multiple cards',
                    'Keep old cards active with small purchases'
                ]
            })
        
        if high_util_accounts > 0:
            recommendations.append({
                'type': 'CREDIT_UTILIZATION',
                'priority': 'HIGH',
                'title': 'Address High-Utilization Individual Accounts',
                'description': f'You have {high_util_accounts} accounts with >30% utilization. Individual account utilization also affects your score.',
                'impact': min(30, high_util_accounts * 12),
                'timeline': '2-3 months',
                'action_steps': [
                    'Identify highest utilization accounts',
                    'Focus debt paydown on these accounts first',
                    'Consider temporary balance transfers',
                    'Avoid closing these accounts after paydown'
                ]
            })
        
        return recommendations
    
    def _generate_history_recommendations(self, factor_breakdown: dict) -> List[Dict]:
        """Generate credit history length recommendations"""
        recommendations = []
        history_data = factor_breakdown.get('credit_history_length', {})
        oldest_years = history_data.get('oldest_account_years', 0)
        avg_years = history_data.get('average_age_years', 0)
        
        if oldest_years < 5:
            recommendations.append({
                'type': 'CREDIT_HISTORY',
                'priority': 'MEDIUM',
                'title': 'Maintain Oldest Credit Accounts',
                'description': f'Your oldest account is {oldest_years:.1f} years old. Keep old accounts open to build credit history.',
                'impact': min(20, int((5 - oldest_years) * 8)),
                'timeline': '6-12 months',
                'action_steps': [
                    'Identify your oldest credit account',
                    'Keep the account active with small purchases',
                    'Pay off the balance monthly',
                    'Never close your oldest account'
                ]
            })
        
        if avg_years < 3:
            recommendations.append({
                'type': 'CREDIT_HISTORY',
                'priority': 'MEDIUM',
                'title': 'Avoid Closing Old Credit Cards',
                'description': f'Your average account age is {avg_years:.1f} years. Avoid closing old accounts to maintain history length.',
                'impact': min(15, int((3 - avg_years) * 10)),
                'timeline': '3-6 months',
                'action_steps': [
                    'Review all old credit cards',
                    'Keep cards active with occasional use',
                    'Pay annual fees on valuable old cards',
                    'Consider product changes instead of closures'
                ]
            })
        
        return recommendations
    
    def _generate_mix_recommendations(self, factor_breakdown: dict) -> List[Dict]:
        """Generate credit mix recommendations"""
        recommendations = []
        mix_data = factor_breakdown.get('credit_mix', {})
        has_revolving = mix_data.get('has_revolving_credit', False)
        has_installment = mix_data.get('has_installment_credit', False)
        total_types = mix_data.get('total_account_types', 0)
        
        if not has_revolving and has_installment:
            recommendations.append({
                'type': 'CREDIT_MIX',
                'priority': 'LOW',
                'title': 'Consider Adding a Credit Card',
                'description': 'You have installment loans but no revolving credit. A credit card can improve your credit mix.',
                'impact': 15,
                'timeline': '3-6 months',
                'action_steps': [
                    'Research secured credit cards if needed',
                    'Apply for a basic credit card',
                    'Use it for small purchases only',
                    'Pay off balance monthly'
                ]
            })
        
        if has_revolving and not has_installment and self.current_score > 650:
            recommendations.append({
                'type': 'CREDIT_MIX',
                'priority': 'LOW',
                'title': 'Consider Adding an Installment Loan',
                'description': 'You only have revolving credit. Adding an installment loan can diversify your credit mix.',
                'impact': 12,
                'timeline': '6-12 months',
                'action_steps': [
                    'Consider a small personal loan if needed',
                    'Look into auto loan for vehicle purchase',
                    'Ensure you can afford the payments',
                    'Don\'t take unnecessary debt just for mix'
                ]
            })
        
        return recommendations
    
    def _generate_inquiry_recommendations(self, factor_breakdown: dict) -> List[Dict]:
        """Generate new credit inquiry recommendations"""
        recommendations = []
        inquiry_data = factor_breakdown.get('new_credit', {})
        inquiries_6m = inquiry_data.get('hard_inquiries_6m', 0)
        inquiries_24m = inquiry_data.get('hard_inquiries_24m', 0)
        
        if inquiries_6m > 2:
            recommendations.append({
                'type': 'NEW_CREDIT',
                'priority': 'MEDIUM',
                'title': 'Avoid New Credit Applications',
                'description': f'You have {inquiries_6m} hard inquiries in the last 6 months. Avoid new applications for now.',
                'impact': min(25, inquiries_6m * 8),
                'timeline': '6-12 months',
                'action_steps': [
                    'Avoid applying for new credit for 6 months',
                    'Focus on improving existing accounts',
                    'If needed, shop for rates within 14-day windows',
                    'Check your credit report for unauthorized inquiries'
                ]
            })
        
        if inquiries_24m > 6:
            recommendations.append({
                'type': 'NEW_CREDIT',
                'priority': 'HIGH',
                'title': 'Significantly Reduce Credit Applications',
                'description': f'You have {inquiries_24m} hard inquiries in 24 months. This is hurting your score significantly.',
                'impact': min(35, (inquiries_24m - 6) * 5),
                'timeline': '12-24 months',
                'action_steps': [
                    'Stop all non-essential credit applications',
                    'Wait for older inquiries to age off (24 months)',
                    'Focus on managing existing credit well',
                    'Consider pre-approved offers only if needed'
                ]
            })
        
        return recommendations
    
    def _save_recommendations(self, recommendations: List[Dict]):
        """Save recommendations to database"""
        try:
            # Clear old incomplete recommendations of the same type
            existing_types = [rec['type'] for rec in recommendations]
            CibilRecommendation.objects.filter(
                cibil_profile=self.profile,
                completed=False,
                recommendation_type__in=existing_types
            ).delete()
            
            # Save new recommendations
            for rec in recommendations:
                CibilRecommendation.objects.create(
                    cibil_profile=self.profile,
                    recommendation_type=rec['type'],
                    priority=rec['priority'],
                    title=rec['title'],
                    description=rec['description'],
                    expected_impact=rec['impact'],
                    timeline=rec['timeline'],
                    action_steps=rec['action_steps'],
                    completed=False
                )
        except Exception as e:
            # Log the error
            print(f"Error saving recommendations: {str(e)}")
            # Re-raise the exception
            raise