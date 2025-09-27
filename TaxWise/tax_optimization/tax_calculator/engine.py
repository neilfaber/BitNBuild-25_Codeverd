"""
Indian Tax Calculation Engine
Supports both Old and New Tax Regimes for FY 2024-25
"""

import logging
from typing import Dict, List, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TaxSlab:
    """Represents a tax slab with income range and rate"""
    min_income: Decimal
    max_income: Optional[Decimal]
    rate: Decimal  # in percentage
    
    def __post_init__(self):
        self.min_income = Decimal(str(self.min_income))
        if self.max_income is not None:
            self.max_income = Decimal(str(self.max_income))
        self.rate = Decimal(str(self.rate))

@dataclass
class DeductionLimit:
    """Represents deduction limits for various sections"""
    section: str
    limit: Optional[Decimal]
    description: str
    
    def __post_init__(self):
        if self.limit is not None:
            self.limit = Decimal(str(self.limit))

class TaxCalculatorEngine:
    """Core tax calculation engine for Indian Income Tax"""
    
    def __init__(self, financial_year: str = "2024-25"):
        self.financial_year = financial_year
        self.setup_tax_slabs()
        self.setup_deduction_limits()
    
    def setup_tax_slabs(self):
        """Setup tax slabs for both regimes"""
        
        # Old Tax Regime Slabs (FY 2024-25)
        self.old_regime_slabs = [
            TaxSlab(0, 250000, 0),      # No tax up to 2.5 lakh
            TaxSlab(250000, 500000, 5), # 5% from 2.5 to 5 lakh
            TaxSlab(500000, 1000000, 20), # 20% from 5 to 10 lakh
            TaxSlab(1000000, None, 30)   # 30% above 10 lakh
        ]
        
        # New Tax Regime Slabs (FY 2024-25)
        self.new_regime_slabs = [
            TaxSlab(0, 300000, 0),      # No tax up to 3 lakh
            TaxSlab(300000, 600000, 5), # 5% from 3 to 6 lakh
            TaxSlab(600000, 900000, 10), # 10% from 6 to 9 lakh
            TaxSlab(900000, 1200000, 15), # 15% from 9 to 12 lakh
            TaxSlab(1200000, 1500000, 20), # 20% from 12 to 15 lakh
            TaxSlab(1500000, None, 30)   # 30% above 15 lakh
        ]
        
        # Senior Citizen Slabs (60+ years) - Old Regime
        self.senior_citizen_old_slabs = [
            TaxSlab(0, 300000, 0),      # No tax up to 3 lakh
            TaxSlab(300000, 500000, 5), # 5% from 3 to 5 lakh
            TaxSlab(500000, 1000000, 20), # 20% from 5 to 10 lakh
            TaxSlab(1000000, None, 30)   # 30% above 10 lakh
        ]
        
        # Super Senior Citizen Slabs (80+ years) - Old Regime
        self.super_senior_citizen_old_slabs = [
            TaxSlab(0, 500000, 0),      # No tax up to 5 lakh
            TaxSlab(500000, 1000000, 20), # 20% from 5 to 10 lakh
            TaxSlab(1000000, None, 30)   # 30% above 10 lakh
        ]
    
    def setup_deduction_limits(self):
        """Setup deduction limits for various sections"""
        
        # Old Regime Deductions (FY 2024-25)
        self.old_regime_deductions = {
            '80C': DeductionLimit('80C', 150000, 'Investment in PPF, EPF, ELSS, Insurance Premium, etc.'),
            '80D': DeductionLimit('80D', 25000, 'Health Insurance Premium (Self & Family)'),
            '80D_PARENTS': DeductionLimit('80D', 25000, 'Health Insurance Premium (Parents)'),
            '80D_SENIOR': DeductionLimit('80D', 50000, 'Health Insurance Premium (Senior Citizen Parents)'),
            '80E': DeductionLimit('80E', None, 'Interest on Education Loan (No Limit)'),
            '80G': DeductionLimit('80G', None, 'Donations to Charitable Institutions'),
            '80GG': DeductionLimit('80GG', 60000, 'House Rent (if HRA not received)'),
            '80CCD1B': DeductionLimit('80CCD1B', 50000, 'Additional NPS Contribution'),
            '80TTA': DeductionLimit('80TTA', 10000, 'Interest on Savings Account'),
            '80TTB': DeductionLimit('80TTB', 50000, 'Interest on Deposits (Senior Citizens)'),
            'STANDARD': DeductionLimit('STANDARD', 50000, 'Standard Deduction'),
        }
        
        # New Regime Deductions (Very Limited)
        self.new_regime_deductions = {
            'STANDARD': DeductionLimit('STANDARD', 50000, 'Standard Deduction'),
            '80CCD2': DeductionLimit('80CCD2', None, 'Employer NPS Contribution (10% of Basic)'),
        }
    
    def get_applicable_slabs(self, regime: str, age: int = 25) -> List[TaxSlab]:
        """Get applicable tax slabs based on regime and age"""
        if regime.upper() == 'OLD':
            if age >= 80:
                return self.super_senior_citizen_old_slabs
            elif age >= 60:
                return self.senior_citizen_old_slabs
            else:
                return self.old_regime_slabs
        else:  # New regime
            return self.new_regime_slabs
    
    def calculate_tax_on_income(self, taxable_income: Decimal, regime: str, age: int = 25) -> Dict:
        """Calculate income tax based on slabs"""
        taxable_income = Decimal(str(taxable_income))
        slabs = self.get_applicable_slabs(regime, age)
        
        total_tax = Decimal('0')
        tax_breakdown = []
        remaining_income = taxable_income
        
        for slab in slabs:
            if remaining_income <= 0:
                break
            
            # Calculate taxable amount in this slab
            slab_min = slab.min_income
            slab_max = slab.max_income or remaining_income + slab_min
            
            if remaining_income + slab_min <= slab_min:
                continue
            
            # Income applicable to this slab
            slab_income = min(remaining_income, slab_max - slab_min)
            slab_tax = slab_income * slab.rate / 100
            
            if slab_tax > 0:
                tax_breakdown.append({
                    'slab_range': f"₹{slab_min:,.0f} - ₹{slab_max:,.0f}" if slab_max else f"Above ₹{slab_min:,.0f}",
                    'rate': f"{slab.rate}%",
                    'taxable_income': slab_income,
                    'tax': slab_tax
                })
            
            total_tax += slab_tax
            remaining_income -= slab_income
        
        return {
            'total_tax': total_tax,
            'tax_breakdown': tax_breakdown,
            'effective_rate': (total_tax / taxable_income * 100) if taxable_income > 0 else Decimal('0')
        }
    
    def calculate_cess_and_surcharge(self, tax_amount: Decimal, taxable_income: Decimal) -> Dict:
        """Calculate Health and Education Cess and Surcharge"""
        tax_amount = Decimal(str(tax_amount))
        taxable_income = Decimal(str(taxable_income))
        
        # Health and Education Cess: 4% of tax
        cess = tax_amount * Decimal('0.04')
        
        # Surcharge calculation
        surcharge = Decimal('0')
        if taxable_income > Decimal('5000000'):  # 50 lakh
            if taxable_income <= Decimal('10000000'):  # 1 crore
                surcharge = tax_amount * Decimal('0.10')  # 10%
            elif taxable_income <= Decimal('20000000'):  # 2 crore
                surcharge = tax_amount * Decimal('0.15')  # 15%
            elif taxable_income <= Decimal('50000000'):  # 5 crore
                surcharge = tax_amount * Decimal('0.25')  # 25%
            else:  # Above 5 crore
                surcharge = tax_amount * Decimal('0.37')  # 37%
        
        return {
            'cess': cess,
            'surcharge': surcharge,
            'total_additional': cess + surcharge
        }
    
    def calculate_deductions(self, income_details: Dict, deduction_details: Dict, regime: str) -> Dict:
        """Calculate applicable deductions based on regime"""
        regime = regime.upper()
        
        if regime == 'NEW':
            # New regime has very limited deductions
            applicable_deductions = self.new_regime_deductions
        else:
            # Old regime has full deductions
            applicable_deductions = self.old_regime_deductions
        
        total_deductions = Decimal('0')
        deduction_breakdown = {}
        
        # Standard Deduction (applicable to both regimes)
        if 'salary_income' in income_details and income_details['salary_income'] > 0:
            standard_deduction = min(
                applicable_deductions['STANDARD'].limit,
                Decimal(str(income_details['salary_income']))
            )
            total_deductions += standard_deduction
            deduction_breakdown['STANDARD'] = {
                'claimed': standard_deduction,
                'limit': applicable_deductions['STANDARD'].limit,
                'description': applicable_deductions['STANDARD'].description
            }
        
        # Process other deductions (only for old regime)
        if regime == 'OLD':
            # Section 80C
            if '80C' in deduction_details:
                section_80c = min(
                    applicable_deductions['80C'].limit,
                    Decimal(str(deduction_details['80C']))
                )
                total_deductions += section_80c
                deduction_breakdown['80C'] = {
                    'claimed': section_80c,
                    'limit': applicable_deductions['80C'].limit,
                    'description': applicable_deductions['80C'].description
                }
            
            # Section 80D (Health Insurance)
            if '80D' in deduction_details:
                section_80d = min(
                    applicable_deductions['80D'].limit,
                    Decimal(str(deduction_details['80D']))
                )
                total_deductions += section_80d
                deduction_breakdown['80D'] = {
                    'claimed': section_80d,
                    'limit': applicable_deductions['80D'].limit,
                    'description': applicable_deductions['80D'].description
                }
            
            # Other deductions...
            for section in ['80E', '80G', '80GG', '80CCD1B', '80TTA']:
                if section in deduction_details:
                    limit = applicable_deductions[section].limit
                    claimed_amount = Decimal(str(deduction_details[section]))
                    
                    if limit is None:  # No limit (like 80E)
                        deduction_amount = claimed_amount
                    else:
                        deduction_amount = min(limit, claimed_amount)
                    
                    total_deductions += deduction_amount
                    deduction_breakdown[section] = {
                        'claimed': deduction_amount,
                        'limit': limit,
                        'description': applicable_deductions[section].description
                    }
        
        return {
            'total_deductions': total_deductions,
            'deduction_breakdown': deduction_breakdown
        }
    
    def calculate_complete_tax(self, income_details: Dict, deduction_details: Dict, 
                             age: int = 25, regime: str = 'NEW') -> Dict:
        """Calculate complete tax liability for both regimes"""
        
        # Calculate for both regimes
        old_regime_calc = self._calculate_tax_for_regime(
            income_details, deduction_details, age, 'OLD'
        )
        
        new_regime_calc = self._calculate_tax_for_regime(
            income_details, deduction_details, age, 'NEW'
        )
        
        # Determine recommended regime
        old_total = old_regime_calc['total_tax_liability']
        new_total = new_regime_calc['total_tax_liability']
        
        if old_total < new_total:
            recommended_regime = 'OLD'
            tax_savings = new_total - old_total
        else:
            recommended_regime = 'NEW'
            tax_savings = old_total - new_total
        
        return {
            'old_regime': old_regime_calc,
            'new_regime': new_regime_calc,
            'recommended_regime': recommended_regime,
            'tax_savings': tax_savings,
            'calculation_date': datetime.now().isoformat()
        }
    
    def _calculate_tax_for_regime(self, income_details: Dict, deduction_details: Dict, 
                                age: int, regime: str) -> Dict:
        """Calculate tax for a specific regime"""
        
        # Calculate Gross Total Income
        gross_total_income = Decimal('0')
        income_breakdown = {}
        
        for income_type, amount in income_details.items():
            amount = Decimal(str(amount))
            gross_total_income += amount
            income_breakdown[income_type] = amount
        
        # Calculate Deductions
        deduction_calc = self.calculate_deductions(income_details, deduction_details, regime)
        total_deductions = deduction_calc['total_deductions']
        
        # Calculate Taxable Income
        taxable_income = max(Decimal('0'), gross_total_income - total_deductions)
        
        # Calculate Tax
        tax_calc = self.calculate_tax_on_income(taxable_income, regime, age)
        base_tax = tax_calc['total_tax']
        
        # Calculate Cess and Surcharge
        additional_calc = self.calculate_cess_and_surcharge(base_tax, taxable_income)
        
        # Total Tax Liability
        total_tax_liability = base_tax + additional_calc['total_additional']
        
        return {
            'regime': regime,
            'gross_total_income': gross_total_income,
            'income_breakdown': income_breakdown,
            'total_deductions': total_deductions,
            'deduction_breakdown': deduction_calc['deduction_breakdown'],
            'taxable_income': taxable_income,
            'base_tax': base_tax,
            'cess': additional_calc['cess'],
            'surcharge': additional_calc['surcharge'],
            'total_tax_liability': total_tax_liability,
            'effective_tax_rate': (total_tax_liability / gross_total_income * 100) if gross_total_income > 0 else Decimal('0'),
            'tax_breakdown': tax_calc['tax_breakdown']
        }
    
    def generate_tax_summary(self, calculation_result: Dict) -> str:
        """Generate a human-readable tax summary"""
        old = calculation_result['old_regime']
        new = calculation_result['new_regime']
        recommended = calculation_result['recommended_regime']
        savings = calculation_result['tax_savings']
        
        summary = f"""
        TAX CALCULATION SUMMARY (FY {self.financial_year})
        {'='*50}
        
        GROSS TOTAL INCOME: ₹{old['gross_total_income']:,.0f}
        
        OLD TAX REGIME:
        - Taxable Income: ₹{old['taxable_income']:,.0f}
        - Total Deductions: ₹{old['total_deductions']:,.0f}
        - Tax Liability: ₹{old['total_tax_liability']:,.0f}
        - Effective Rate: {old['effective_tax_rate']:.2f}%
        
        NEW TAX REGIME:
        - Taxable Income: ₹{new['taxable_income']:,.0f}
        - Total Deductions: ₹{new['total_deductions']:,.0f}
        - Tax Liability: ₹{new['total_tax_liability']:,.0f}
        - Effective Rate: {new['effective_tax_rate']:.2f}%
        
        RECOMMENDATION:
        - Choose: {recommended} TAX REGIME
        - Tax Savings: ₹{savings:,.0f}
        """
        
        return summary

# Global tax calculator instance
tax_calculator = TaxCalculatorEngine()