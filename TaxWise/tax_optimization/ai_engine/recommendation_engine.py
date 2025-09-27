"""
AI-Powered Tax Optimization Recommendation Engine
Generates personalized tax-saving recommendations based on user's financial profile
"""

import logging
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Recommendation:
    """Represents a tax optimization recommendation"""
    title: str
    description: str
    recommendation_type: str
    priority: str
    potential_savings: Decimal
    investment_required: Decimal
    tax_section: Optional[str]
    deadline: Optional[date]
    roi_percentage: Optional[Decimal]
    confidence_score: float
    implementation_steps: List[str]
    
    def __post_init__(self):
        self.potential_savings = Decimal(str(self.potential_savings))
        self.investment_required = Decimal(str(self.investment_required))
        if self.roi_percentage:
            self.roi_percentage = Decimal(str(self.roi_percentage))

class RuleBasedRecommendationEngine:
    """Rule-based recommendation engine for tax optimization"""
    
    def __init__(self):
        self.current_year = datetime.now().year
        self.financial_year_end = date(self.current_year, 3, 31)
        
        # Investment options with expected returns and tax benefits
        self.investment_options = {
            'PPF': {
                'name': 'Public Provident Fund',
                'tax_section': '80C',
                'max_limit': 150000,
                'expected_return': 7.1,  # Current PPF rate
                'lock_in': 15,  # years
                'tax_free_maturity': True
            },
            'ELSS': {
                'name': 'Equity Linked Savings Scheme',
                'tax_section': '80C',
                'max_limit': 150000,
                'expected_return': 12.0,  # Historical average
                'lock_in': 3,  # years
                'tax_free_maturity': False
            },
            'NPS': {
                'name': 'National Pension System',
                'tax_section': '80C',
                'additional_section': '80CCD1B',
                'max_limit': 150000,
                'additional_limit': 50000,
                'expected_return': 10.0,
                'lock_in': 60,  # until retirement
                'tax_free_maturity': False
            },
            'TERM_INSURANCE': {
                'name': 'Term Life Insurance',
                'tax_section': '80C',
                'max_limit': 150000,
                'expected_return': 0,  # Pure protection
                'lock_in': 0,
                'tax_free_maturity': True
            },
            'HEALTH_INSURANCE': {
                'name': 'Health Insurance',
                'tax_section': '80D',
                'max_limit': 25000,  # Self and family
                'parents_limit': 25000,  # Parents
                'senior_parents_limit': 50000,  # Senior citizen parents
                'expected_return': 0,  # Pure protection
                'lock_in': 1  # year
            }
        }
    
    def analyze_current_investments(self, user_profile: Dict, investments: List[Dict]) -> Dict:
        """Analyze user's current investment portfolio"""
        analysis = {
            'total_80c_invested': Decimal('0'),
            '80c_remaining': Decimal('150000'),
            'total_80d_invested': Decimal('0'),
            '80d_remaining': Decimal('25000'),
            'investment_breakdown': {},
            'gaps': []
        }
        
        for investment in investments:
            section = investment.get('tax_section', '')
            amount = Decimal(str(investment.get('amount', 0)))
            
            if section == '80C':
                analysis['total_80c_invested'] += amount
            elif section == '80D':
                analysis['total_80d_invested'] += amount
            
            inv_type = investment.get('investment_type', 'Other')
            analysis['investment_breakdown'][inv_type] = analysis['investment_breakdown'].get(inv_type, 0) + amount
        
        # Calculate remaining limits
        analysis['80c_remaining'] = max(Decimal('0'), Decimal('150000') - analysis['total_80c_invested'])
        analysis['80d_remaining'] = max(Decimal('0'), Decimal('25000') - analysis['total_80d_invested'])
        
        # Identify gaps
        if analysis['80c_remaining'] > 0:
            analysis['gaps'].append({
                'section': '80C',
                'amount': analysis['80c_remaining'],
                'description': f"₹{analysis['80c_remaining']:,.0f} remaining in Section 80C investments"
            })
        
        if analysis['80d_remaining'] > 0:
            analysis['gaps'].append({
                'section': '80D',
                'amount': analysis['80d_remaining'],
                'description': f"₹{analysis['80d_remaining']:,.0f} remaining in Section 80D (Health Insurance)"
            })
        
        return analysis
    
    def generate_80c_recommendations(self, user_profile: Dict, remaining_80c: Decimal, 
                                   income: Decimal) -> List[Recommendation]:
        """Generate Section 80C investment recommendations"""
        recommendations = []
        
        if remaining_80c <= 0:
            return recommendations
        
        age = user_profile.get('age', 30)
        risk_tolerance = user_profile.get('risk_tolerance', 'medium')  # high/medium/low
        
        # PPF Recommendation
        if remaining_80c > 0:
            ppf_amount = min(remaining_80c, Decimal('150000'))
            tax_savings = self._calculate_tax_savings(ppf_amount, income)
            
            recommendations.append(Recommendation(
                title="Invest in Public Provident Fund (PPF)",
                description=f"Invest ₹{ppf_amount:,.0f} in PPF for guaranteed returns and tax savings. "
                          f"Current interest rate: 7.1% per annum with 15-year lock-in.",
                recommendation_type="INVESTMENT",
                priority="HIGH",
                potential_savings=tax_savings,
                investment_required=ppf_amount,
                tax_section="80C",
                deadline=self.financial_year_end,
                roi_percentage=Decimal('7.1'),
                confidence_score=0.95,
                implementation_steps=[
                    "Open PPF account in any bank or post office",
                    f"Invest ₹{ppf_amount:,.0f} before March 31st",
                    "Set up automatic monthly SIP for future years",
                    "Keep investment receipts for tax filing"
                ]
            ))
        
        # ELSS Recommendation (for higher risk tolerance)
        if risk_tolerance in ['medium', 'high'] and remaining_80c > 50000:
            elss_amount = min(remaining_80c, Decimal('100000'))
            tax_savings = self._calculate_tax_savings(elss_amount, income)
            
            recommendations.append(Recommendation(
                title="Invest in ELSS Mutual Funds",
                description=f"Invest ₹{elss_amount:,.0f} in Equity Linked Savings Scheme for higher returns. "
                          f"Expected return: 12% per annum with only 3-year lock-in.",
                recommendation_type="INVESTMENT",
                priority="MEDIUM" if risk_tolerance == 'medium' else "HIGH",
                potential_savings=tax_savings,
                investment_required=elss_amount,
                tax_section="80C",
                deadline=self.financial_year_end,
                roi_percentage=Decimal('12.0'),
                confidence_score=0.85,
                implementation_steps=[
                    "Choose top-performing ELSS funds",
                    f"Start SIP of ₹{elss_amount/12:,.0f} per month",
                    "Monitor fund performance annually",
                    "Stay invested for at least 3 years"
                ]
            ))
        
        # NPS Recommendation
        if age < 50 and remaining_80c > 0:
            nps_amount = min(remaining_80c, Decimal('50000'))
            additional_nps = Decimal('50000')  # 80CCD1B
            total_tax_savings = self._calculate_tax_savings(nps_amount + additional_nps, income)
            
            recommendations.append(Recommendation(
                title="National Pension System (NPS) Investment",
                description=f"Invest ₹{nps_amount:,.0f} under 80C + ₹{additional_nps:,.0f} under 80CCD1B. "
                          f"Total deduction: ₹{nps_amount + additional_nps:,.0f}",
                recommendation_type="INVESTMENT",
                priority="MEDIUM",
                potential_savings=total_tax_savings,
                investment_required=nps_amount + additional_nps,
                tax_section="80C",
                deadline=self.financial_year_end,
                roi_percentage=Decimal('10.0'),
                confidence_score=0.80,
                implementation_steps=[
                    "Open NPS account online",
                    "Choose investment mix based on age",
                    f"Invest ₹{nps_amount + additional_nps:,.0f} before March 31st",
                    "Review and rebalance annually"
                ]
            ))
        
        return recommendations
    
    def generate_80d_recommendations(self, user_profile: Dict, remaining_80d: Decimal, 
                                   income: Decimal) -> List[Recommendation]:
        """Generate Section 80D health insurance recommendations"""
        recommendations = []
        
        if remaining_80d <= 0:
            return recommendations
        
        age = user_profile.get('age', 30)
        has_parents = user_profile.get('has_parents', True)
        parents_age = user_profile.get('parents_age', 55)
        
        # Health Insurance for Self and Family
        if remaining_80d > 0:
            insurance_amount = min(remaining_80d, Decimal('25000'))
            tax_savings = self._calculate_tax_savings(insurance_amount, income)
            
            recommendations.append(Recommendation(
                title="Health Insurance for Self and Family",
                description=f"Get comprehensive health insurance coverage with premium up to ₹{insurance_amount:,.0f}. "
                          f"Provides both health protection and tax savings.",
                recommendation_type="INVESTMENT",
                priority="HIGH",
                potential_savings=tax_savings,
                investment_required=insurance_amount,
                tax_section="80D",
                deadline=self.financial_year_end,
                roi_percentage=None,
                confidence_score=0.95,
                implementation_steps=[
                    "Compare health insurance policies online",
                    "Choose family floater policy with adequate sum assured",
                    f"Pay premium of ₹{insurance_amount:,.0f} annually",
                    "Keep premium receipts for tax filing"
                ]
            ))
        
        # Health Insurance for Parents
        if has_parents and parents_age >= 60:
            parent_limit = Decimal('50000') if parents_age >= 60 else Decimal('25000')
            parent_tax_savings = self._calculate_tax_savings(parent_limit, income)
            
            recommendations.append(Recommendation(
                title="Health Insurance for Parents",
                description=f"Get health insurance for parents with premium up to ₹{parent_limit:,.0f}. "
                          f"{'Senior citizen benefit' if parents_age >= 60 else 'Standard rate'} applies.",
                recommendation_type="INVESTMENT",
                priority="HIGH",
                potential_savings=parent_tax_savings,
                investment_required=parent_limit,
                tax_section="80D",
                deadline=self.financial_year_end,
                roi_percentage=None,
                confidence_score=0.90,
                implementation_steps=[
                    "Research senior citizen health insurance policies",
                    "Check for pre-existing condition coverage",
                    f"Budget ₹{parent_limit:,.0f} for annual premium",
                    "Consider family health insurance plan"
                ]
            ))
        
        return recommendations
    
    def generate_regime_recommendation(self, tax_calculation: Dict) -> Optional[Recommendation]:
        """Recommend optimal tax regime"""
        old_regime = tax_calculation.get('old_regime', {})
        new_regime = tax_calculation.get('new_regime', {})
        
        old_tax = old_regime.get('total_tax_liability', Decimal('0'))
        new_tax = new_regime.get('total_tax_liability', Decimal('0'))
        
        if abs(old_tax - new_tax) < 1000:  # Difference less than ₹1000
            return None  # No strong recommendation
        
        if old_tax < new_tax:
            # Old regime is better
            savings = new_tax - old_tax
            return Recommendation(
                title="Choose Old Tax Regime",
                description=f"Old tax regime saves ₹{savings:,.0f} compared to new regime. "
                          f"Take advantage of deductions under sections 80C, 80D, etc.",
                recommendation_type="REGIME_SWITCH",
                priority="HIGH",
                potential_savings=savings,
                investment_required=Decimal('0'),
                tax_section=None,
                deadline=date(self.current_year, 3, 31),
                roi_percentage=None,
                confidence_score=0.90,
                implementation_steps=[
                    "Continue with old tax regime",
                    "Maximize deductions under various sections",
                    "File ITR using old regime provisions",
                    "Plan investments for next year"
                ]
            )
        else:
            # New regime is better
            savings = old_tax - new_tax
            return Recommendation(
                title="Switch to New Tax Regime",
                description=f"New tax regime saves ₹{savings:,.0f} compared to old regime. "
                          f"No need to make tax-saving investments.",
                recommendation_type="REGIME_SWITCH",
                priority="HIGH",
                potential_savings=savings,
                investment_required=Decimal('0'),
                tax_section=None,
                deadline=date(self.current_year, 7, 31),  # Before filing ITR
                roi_percentage=None,
                confidence_score=0.90,
                implementation_steps=[
                    "Opt for new tax regime in Form 10-IE",
                    "File ITR using new regime provisions",
                    "Focus on maximizing income rather than deductions",
                    "Review decision annually"
                ]
            )
    
    def generate_timing_recommendations(self, user_profile: Dict, 
                                      current_investments: List[Dict]) -> List[Recommendation]:
        """Generate timing-based recommendations"""
        recommendations = []
        current_date = datetime.now().date()
        days_to_year_end = (self.financial_year_end - current_date).days
        
        # Year-end investment rush warning
        if days_to_year_end < 60:  # Less than 2 months left
            recommendations.append(Recommendation(
                title="Complete Tax-Saving Investments Before Year End",
                description=f"Only {days_to_year_end} days left in the financial year! "
                          f"Complete your tax-saving investments to avoid last-minute rush.",
                recommendation_type="TIMING",
                priority="HIGH",
                potential_savings=Decimal('0'),  # Avoid loss of deductions
                investment_required=Decimal('0'),
                tax_section=None,
                deadline=self.financial_year_end,
                roi_percentage=None,
                confidence_score=1.0,
                implementation_steps=[
                    "Review remaining deduction limits",
                    "Make lump-sum investments if needed",
                    "Keep all investment receipts ready",
                    "Plan SIPs for next financial year"
                ]
            ))
        
        # SIP recommendation for better averaging
        elif days_to_year_end > 200:  # Early in the financial year
            recommendations.append(Recommendation(
                title="Start Monthly SIPs for Tax Saving",
                description="Start systematic investment plans (SIPs) early in the year "
                          "for better rupee cost averaging and disciplined investing.",
                recommendation_type="TIMING",
                priority="MEDIUM",
                potential_savings=Decimal('5000'),  # Estimated benefit from averaging
                investment_required=Decimal('0'),
                tax_section=None,
                deadline=None,
                roi_percentage=None,
                confidence_score=0.80,
                implementation_steps=[
                    "Calculate monthly SIP amounts for each section",
                    "Set up auto-debit for SIPs",
                    "Review and adjust monthly",
                    "Track progress towards annual limits"
                ]
            ))
        
        return recommendations
    
    def _calculate_tax_savings(self, investment_amount: Decimal, annual_income: Decimal) -> Decimal:
        """Calculate approximate tax savings from investment"""
        # Simplified tax bracket calculation
        if annual_income <= 300000:
            return Decimal('0')  # No tax, no savings
        elif annual_income <= 600000:
            return investment_amount * Decimal('0.05')  # 5% tax bracket
        elif annual_income <= 900000:
            return investment_amount * Decimal('0.10')  # 10% tax bracket
        elif annual_income <= 1200000:
            return investment_amount * Decimal('0.15')  # 15% tax bracket
        elif annual_income <= 1500000:
            return investment_amount * Decimal('0.20')  # 20% tax bracket
        else:
            return investment_amount * Decimal('0.30')  # 30% tax bracket
    
    def generate_comprehensive_recommendations(self, user_profile: Dict, 
                                             current_investments: List[Dict],
                                             tax_calculation: Dict) -> List[Recommendation]:
        """Generate comprehensive tax optimization recommendations"""
        recommendations = []
        
        # Analyze current investments
        investment_analysis = self.analyze_current_investments(user_profile, current_investments)
        annual_income = Decimal(str(user_profile.get('annual_income', 0)))
        
        # Generate Section 80C recommendations
        if investment_analysis['80c_remaining'] > 0:
            recommendations.extend(
                self.generate_80c_recommendations(
                    user_profile, 
                    investment_analysis['80c_remaining'], 
                    annual_income
                )
            )
        
        # Generate Section 80D recommendations
        if investment_analysis['80d_remaining'] > 0:
            recommendations.extend(
                self.generate_80d_recommendations(
                    user_profile, 
                    investment_analysis['80d_remaining'], 
                    annual_income
                )
            )
        
        # Generate regime recommendation
        regime_rec = self.generate_regime_recommendation(tax_calculation)
        if regime_rec:
            recommendations.append(regime_rec)
        
        # Generate timing recommendations
        recommendations.extend(
            self.generate_timing_recommendations(user_profile, current_investments)
        )
        
        # Sort by priority and potential savings
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        recommendations.sort(
            key=lambda x: (priority_order.get(x.priority, 0), x.potential_savings),
            reverse=True
        )
        
        return recommendations

# Global recommendation engine instance
recommendation_engine = RuleBasedRecommendationEngine()