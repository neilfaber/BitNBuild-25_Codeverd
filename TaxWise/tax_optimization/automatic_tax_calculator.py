"""
Automatic Tax Calculator for Indian Tax System
Calculates tax deductions based on existing financial data
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Tuple
from django.db.models import Sum, Q
from bank_analyzer.models import CreditCardStatement, CreditCardTransaction
from tax_optimization.models import FinancialTransaction, Investment, TaxCalculation, UserProfile


class AutomaticTaxCalculator:
    """
    Automatically calculates Indian tax deductions from existing financial data
    """
    
    def __init__(self, user, financial_year=None):
        self.user = user
        self.financial_year = financial_year or self.get_current_financial_year()
        
        # Tax limits for FY 2024-25
        self.tax_limits = {
            '80C': Decimal('150000'),    # EPF, PPF, ELSS, etc.
            '80D': Decimal('25000'),     # Health Insurance (individual)
            '80D_SENIOR': Decimal('50000'),  # Health Insurance (senior citizen)
            '80G': None,                 # Donations (no limit)
            '24B': Decimal('200000'),    # Home Loan Interest
            '80E': None,                 # Education Loan Interest (no limit)
            '80EE': Decimal('50000'),    # First Home Buyer Interest
            '80EEA': Decimal('150000'),  # Electric Vehicle Interest
        }
        
        # Keywords for transaction categorization
        self.transaction_keywords = {
            '80C': [
                'ppf', 'public provident fund', 'provident fund', 'epf', 'employee provident fund',
                'elss', 'equity linked savings', 'lic', 'life insurance', 'insurance premium',
                'nsc', 'national savings certificate', 'tax saver', 'mutual fund sip',
                'fd', 'fixed deposit', 'recurring deposit', 'rd'
            ],
            '80D': [
                'health insurance', 'medical insurance', 'mediclaim', 'star health',
                'hdfc ergo', 'icici lombard', 'bajaj allianz', 'oriental insurance',
                'new india assurance', 'health premium', 'medical premium'
            ],
            '80G': [
                'donation', 'charity', 'charitable', 'ngv', 'trust', 'foundation',
                'relief fund', 'pm cares', 'chief minister', 'red cross', 'oxfam'
            ],
            '24B': [
                'home loan', 'housing loan', 'mortgage', 'property loan',
                'hdfc home loan', 'icici home loan', 'sbi home loan', 'axis home loan',
                'lic housing', 'pnb housing', 'home loan emi', 'housing emi'
            ],
            '80E': [
                'education loan', 'student loan', 'study loan', 'educational loan',
                'education emi', 'student emi'
            ]
        }

    def get_current_financial_year(self):
        """Get current financial year in YYYY-YY format"""
        today = date.today()
        if today.month >= 4:  # April onwards is new financial year
            start_year = today.year
            end_year = today.year + 1
        else:
            start_year = today.year - 1
            end_year = today.year
        
        return f"{start_year}-{str(end_year)[2:]}"

    def get_financial_year_dates(self):
        """Get start and end dates for financial year"""
        year_parts = self.financial_year.split('-')
        start_year = int(year_parts[0])
        end_year = int(f"20{year_parts[1]}")
        
        start_date = date(start_year, 4, 1)
        end_date = date(end_year, 3, 31)
        
        return start_date, end_date

    def categorize_transaction_by_keywords(self, description: str, merchant: str = "") -> str:
        """Categorize transaction based on description keywords"""
        text = f"{description} {merchant}".lower()
        
        for section, keywords in self.transaction_keywords.items():
            if any(keyword in text for keyword in keywords):
                return section
        
        return None

    def calculate_section_80c_deductions(self) -> Dict:
        """Calculate Section 80C deductions from existing data"""
        start_date, end_date = self.get_financial_year_dates()
        
        # Get from existing investments
        investment_80c = Investment.objects.filter(
            user=self.user,
            tax_section='80C',
            investment_date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Get from credit card transactions
        cc_transactions = CreditCardTransaction.objects.filter(
            user=self.user,
            transaction_date__range=[start_date, end_date],
            transaction_type='PURCHASE'
        )
        
        cc_80c_amount = Decimal('0')
        cc_80c_transactions = []
        
        for txn in cc_transactions:
            section = self.categorize_transaction_by_keywords(
                txn.description, 
                txn.merchant_name or ""
            )
            if section == '80C':
                cc_80c_amount += txn.transaction_amount
                cc_80c_transactions.append({
                    'date': txn.transaction_date,
                    'description': txn.description,
                    'merchant': txn.merchant_name,
                    'amount': txn.transaction_amount
                })

        # Get from bank transactions
        bank_transactions = FinancialTransaction.objects.filter(
            user=self.user,
            date__range=[start_date, end_date],
            tax_section='80C'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_80c = investment_80c + cc_80c_amount + bank_transactions
        eligible_deduction = min(total_80c, self.tax_limits['80C'])
        
        return {
            'section': '80C',
            'limit': self.tax_limits['80C'],
            'total_invested': total_80c,
            'eligible_deduction': eligible_deduction,
            'utilization_percentage': float(eligible_deduction / self.tax_limits['80C'] * 100),
            'remaining_limit': self.tax_limits['80C'] - eligible_deduction,
            'tax_savings_10': eligible_deduction * Decimal('0.10'),
            'tax_savings_20': eligible_deduction * Decimal('0.20'),
            'tax_savings_30': eligible_deduction * Decimal('0.30'),
            'sources': {
                'investments': investment_80c,
                'credit_card': cc_80c_amount,
                'bank_transactions': bank_transactions
            },
            'transactions': cc_80c_transactions,
            'recommendations': self.get_80c_recommendations(eligible_deduction)
        }

    def calculate_section_80d_deductions(self) -> Dict:
        """Calculate Section 80D (Health Insurance) deductions"""
        start_date, end_date = self.get_financial_year_dates()
        
        # Check user age for limit determination
        try:
            user_profile = UserProfile.objects.get(user=self.user)
            age = user_profile.age
            limit = self.tax_limits['80D_SENIOR'] if age >= 60 else self.tax_limits['80D']
        except UserProfile.DoesNotExist:
            limit = self.tax_limits['80D']
        
        # Get from existing investments
        investment_80d = Investment.objects.filter(
            user=self.user,
            tax_section='80D',
            investment_date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Get from credit card transactions
        cc_transactions = CreditCardTransaction.objects.filter(
            user=self.user,
            transaction_date__range=[start_date, end_date],
            transaction_type='PURCHASE'
        )
        
        cc_80d_amount = Decimal('0')
        cc_80d_transactions = []
        
        for txn in cc_transactions:
            section = self.categorize_transaction_by_keywords(
                txn.description, 
                txn.merchant_name or ""
            )
            if section == '80D':
                cc_80d_amount += txn.transaction_amount
                cc_80d_transactions.append({
                    'date': txn.transaction_date,
                    'description': txn.description,
                    'merchant': txn.merchant_name,
                    'amount': txn.transaction_amount
                })

        total_80d = investment_80d + cc_80d_amount
        eligible_deduction = min(total_80d, limit)
        
        return {
            'section': '80D',
            'limit': limit,
            'total_paid': total_80d,
            'eligible_deduction': eligible_deduction,
            'utilization_percentage': float(eligible_deduction / limit * 100),
            'remaining_limit': limit - eligible_deduction,
            'tax_savings_10': eligible_deduction * Decimal('0.10'),
            'tax_savings_20': eligible_deduction * Decimal('0.20'),
            'tax_savings_30': eligible_deduction * Decimal('0.30'),
            'sources': {
                'investments': investment_80d,
                'credit_card': cc_80d_amount
            },
            'transactions': cc_80d_transactions,
            'recommendations': self.get_80d_recommendations(eligible_deduction, limit)
        }

    def calculate_section_80g_deductions(self) -> Dict:
        """Calculate Section 80G (Donations) deductions"""
        start_date, end_date = self.get_financial_year_dates()
        
        # Get from credit card transactions
        cc_transactions = CreditCardTransaction.objects.filter(
            user=self.user,
            transaction_date__range=[start_date, end_date],
            transaction_type='PURCHASE'
        )
        
        cc_80g_amount = Decimal('0')
        cc_80g_transactions = []
        
        for txn in cc_transactions:
            section = self.categorize_transaction_by_keywords(
                txn.description, 
                txn.merchant_name or ""
            )
            if section == '80G':
                cc_80g_amount += txn.transaction_amount
                cc_80g_transactions.append({
                    'date': txn.transaction_date,
                    'description': txn.description,
                    'merchant': txn.merchant_name,
                    'amount': txn.transaction_amount
                })

        # Most 80G donations qualify for 50% or 100% deduction
        # For simplicity, assuming 50% deduction
        eligible_deduction = cc_80g_amount * Decimal('0.5')
        
        return {
            'section': '80G',
            'limit': 'No Limit',
            'total_donated': cc_80g_amount,
            'eligible_deduction': eligible_deduction,
            'deduction_percentage': 50,
            'tax_savings_10': eligible_deduction * Decimal('0.10'),
            'tax_savings_20': eligible_deduction * Decimal('0.20'),
            'tax_savings_30': eligible_deduction * Decimal('0.30'),
            'sources': {
                'credit_card': cc_80g_amount
            },
            'transactions': cc_80g_transactions,
            'recommendations': self.get_80g_recommendations(cc_80g_amount)
        }

    def calculate_section_24b_deductions(self) -> Dict:
        """Calculate Section 24(b) Home Loan Interest deductions"""
        start_date, end_date = self.get_financial_year_dates()
        
        # Get from credit card transactions (EMI payments)
        cc_transactions = CreditCardTransaction.objects.filter(
            user=self.user,
            transaction_date__range=[start_date, end_date],
            transaction_type='PURCHASE'
        )
        
        cc_24b_amount = Decimal('0')
        cc_24b_transactions = []
        
        for txn in cc_transactions:
            section = self.categorize_transaction_by_keywords(
                txn.description, 
                txn.merchant_name or ""
            )
            if section == '24B':
                # Assume 70% of EMI is interest (typical for initial years)
                interest_amount = txn.transaction_amount * Decimal('0.7')
                cc_24b_amount += interest_amount
                cc_24b_transactions.append({
                    'date': txn.transaction_date,
                    'description': txn.description,
                    'merchant': txn.merchant_name,
                    'total_emi': txn.transaction_amount,
                    'estimated_interest': interest_amount
                })

        eligible_deduction = min(cc_24b_amount, self.tax_limits['24B'])
        
        return {
            'section': '24(b)',
            'limit': self.tax_limits['24B'],
            'total_interest_paid': cc_24b_amount,
            'eligible_deduction': eligible_deduction,
            'utilization_percentage': float(eligible_deduction / self.tax_limits['24B'] * 100),
            'remaining_limit': self.tax_limits['24B'] - eligible_deduction,
            'tax_savings_10': eligible_deduction * Decimal('0.10'),
            'tax_savings_20': eligible_deduction * Decimal('0.20'),
            'tax_savings_30': eligible_deduction * Decimal('0.30'),
            'sources': {
                'credit_card_emi': cc_24b_amount
            },
            'transactions': cc_24b_transactions,
            'note': 'Interest amount estimated at 70% of EMI (typical for initial years)',
            'recommendations': self.get_24b_recommendations(eligible_deduction)
        }

    def calculate_comprehensive_tax_savings(self) -> Dict:
        """Calculate comprehensive tax savings across all sections"""
        deductions = {
            '80C': self.calculate_section_80c_deductions(),
            '80D': self.calculate_section_80d_deductions(),
            '80G': self.calculate_section_80g_deductions(),
            '24B': self.calculate_section_24b_deductions()
        }
        
        total_deductions = sum(
            d['eligible_deduction'] for d in deductions.values() 
            if isinstance(d['eligible_deduction'], Decimal)
        )
        
        # Calculate tax savings (assuming 30% tax bracket)
        tax_savings_30 = total_deductions * Decimal('0.30')
        tax_savings_20 = total_deductions * Decimal('0.20')
        tax_savings_10 = total_deductions * Decimal('0.10')
        
        return {
            'financial_year': self.financial_year,
            'deductions_by_section': deductions,
            'summary': {
                'total_eligible_deductions': total_deductions,
                'tax_savings_30_percent': tax_savings_30,
                'tax_savings_20_percent': tax_savings_20,
                'tax_savings_10_percent': tax_savings_10,
                'calculation_date': datetime.now()
            },
            'recommendations': self.get_overall_recommendations(deductions, total_deductions)
        }

    def get_80c_recommendations(self, current_deduction: Decimal) -> List[str]:
        """Get recommendations for 80C optimization"""
        remaining = self.tax_limits['80C'] - current_deduction
        recommendations = []
        
        if remaining > 0:
            recommendations.extend([
                f"You can invest ₹{remaining:,.0f} more in 80C instruments to maximize deduction",
                "Consider ELSS mutual funds for potential higher returns",
                "Increase EPF contribution if employed",
                "Consider Tax Saver Fixed Deposits for guaranteed returns"
            ])
        else:
            recommendations.append("You have maximized your 80C deductions!")
            
        return recommendations

    def get_80d_recommendations(self, current_deduction: Decimal, limit: Decimal) -> List[str]:
        """Get recommendations for 80D optimization"""
        remaining = limit - current_deduction
        recommendations = []
        
        if remaining > 0:
            recommendations.extend([
                f"You can invest ₹{remaining:,.0f} more in health insurance premiums",
                "Consider increasing health insurance coverage",
                "Add family members to health insurance policy",
                "Consider separate policies for parents (additional ₹25,000 deduction)"
            ])
        else:
            recommendations.append("You have maximized your 80D deductions!")
            
        return recommendations

    def get_80g_recommendations(self, current_donations: Decimal) -> List[str]:
        """Get recommendations for 80G optimization"""
        recommendations = [
            "Consider donating to eligible charitable organizations",
            "Check if your donations qualify for 50% or 100% deduction",
            "Keep donation receipts for tax filing",
            "PM CARES Fund donations qualify for 100% deduction"
        ]
        
        if current_donations == 0:
            recommendations.insert(0, "No donations found - consider charitable giving for tax benefits")
            
        return recommendations

    def get_24b_recommendations(self, current_deduction: Decimal) -> List[str]:
        """Get recommendations for 24B optimization"""
        remaining = self.tax_limits['24B'] - current_deduction
        recommendations = []
        
        if current_deduction == 0:
            recommendations.extend([
                "No home loan interest found",
                "Consider home loan for tax benefits and wealth creation"
            ])
        elif remaining > 0:
            recommendations.extend([
                f"You have ₹{remaining:,.0f} more room for home loan interest deduction",
                "Consider prepaying home loan strategically to optimize tax benefits"
            ])
        else:
            recommendations.append("You have maximized your home loan interest deductions!")
            
        return recommendations

    def get_overall_recommendations(self, deductions: Dict, total_deductions: Decimal) -> List[str]:
        """Get overall tax optimization recommendations"""
        recommendations = [
            f"Total tax deductions identified: ₹{total_deductions:,.0f}",
            "Review and verify all identified transactions for accuracy",
            "Consider increasing investments in underutilized sections",
            "Maintain proper documentation for all deductions"
        ]
        
        # Find sections with low utilization
        low_utilization_sections = []
        for section, data in deductions.items():
            if section != '80G' and 'utilization_percentage' in data:
                if data['utilization_percentage'] < 50:
                    low_utilization_sections.append(section)
        
        if low_utilization_sections:
            recommendations.append(
                f"Focus on optimizing: {', '.join(low_utilization_sections)} (low utilization)"
            )
        
        return recommendations