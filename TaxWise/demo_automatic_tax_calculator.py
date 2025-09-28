"""
TaxWise Automatic Tax Calculator Demo Script
Demonstrates comprehensive tax calculations from existing financial data
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TaxWise.settings')
django.setup()

from decimal import Decimal
from datetime import datetime, date, timedelta
from django.contrib.auth.models import User
from bank_analyzer.models import CreditCardStatement, CreditCardTransaction
from tax_optimization.models import FinancialTransaction, Investment, UserProfile
from tax_optimization.automatic_tax_calculator import AutomaticTaxCalculator

class TaxCalculatorDemo:
    """Comprehensive demo of automatic tax calculations"""
    
    def __init__(self):
        self.demo_user = None
        
    def setup_demo_user(self):
        """Create or get demo user with comprehensive financial data"""
        username = 'tax_demo_user'
        
        # Create or get user
        self.demo_user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': 'demo@taxwise.com',
                'first_name': 'Tax',
                'last_name': 'Demo'
            }
        )
        
        if created:
            self.demo_user.set_password('demo123')
            self.demo_user.save()
        
        # Create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=self.demo_user,
            defaults={
                'pan_number': 'DEMO123456',
                'annual_income': Decimal('1200000'),  # 12 Lakhs
                'age': 32,
                'preferred_tax_regime': 'OLD',
                'financial_year': '2024-25'
            }
        )
        
        print(f"✅ Demo user setup complete: {username}")
        return self.demo_user
    
    def create_sample_transactions(self):
        """Create comprehensive sample transactions for tax analysis"""
        if not self.demo_user:
            self.setup_demo_user()
        
        # Clear existing transactions
        CreditCardTransaction.objects.filter(user=self.demo_user).delete()
        CreditCardStatement.objects.filter(user=self.demo_user).delete()
        Investment.objects.filter(user=self.demo_user).delete()
        FinancialTransaction.objects.filter(user=self.demo_user).delete()
        
        # Create a credit card statement first
        statement = CreditCardStatement.objects.create(
            user=self.demo_user,
            statement_date=date.today() - timedelta(days=30),
            payment_due_date=date.today() + timedelta(days=20),
            total_credit_limit=Decimal('200000'),
            available_credit=Decimal('150000'),
            current_balance=Decimal('50000'),
            minimum_amount_due=Decimal('2500'),
            statement_balance=Decimal('50000'),
            card_number_last_four='1234',
            bank_name='Demo Bank',
            cardholder_name=f'{self.demo_user.first_name} {self.demo_user.last_name}'
        )
        
        transactions_created = 0
        
        # Section 80C Transactions
        section_80c_data = [
            ("PPF Contribution", 50000, "Public Provident Fund monthly contribution"),
            ("ELSS SIP", 36000, "Equity Linked Savings Scheme SIP"),
            ("LIC Premium", 25000, "Life Insurance Premium payment"),
            ("EPF Additional", 15000, "Additional Employee Provident Fund"),
            ("Tax Saver FD", 24000, "Tax Saver Fixed Deposit")
        ]
        
        for desc, amount, full_desc in section_80c_data:
            CreditCardTransaction.objects.create(
                statement=statement,
                user=self.demo_user,
                transaction_date=date.today() - timedelta(days=30),
                description=full_desc,
                merchant_name=desc,
                transaction_amount=Decimal(str(amount)),
                transaction_type='PURCHASE',
                category='INVESTMENT'
            )
            transactions_created += 1
        
        # Section 80D Transactions
        section_80d_data = [
            ("Health Insurance Premium", 15000, "Star Health Insurance Premium"),
            ("Family Health Coverage", 8000, "Additional family coverage premium")
        ]
        
        for desc, amount, full_desc in section_80d_data:
            CreditCardTransaction.objects.create(
                statement=statement,
                user=self.demo_user,
                transaction_date=date.today() - timedelta(days=45),
                description=full_desc,
                merchant_name=desc,
                transaction_amount=Decimal(str(amount)),
                transaction_type='PURCHASE',
                category='HEALTHCARE'
            )
            transactions_created += 1
        
        # Section 80G Transactions
        section_80g_data = [
            ("PM CARES Donation", 5000, "PM CARES Fund donation"),
            ("Charity Donation", 3000, "Red Cross Society donation")
        ]
        
        for desc, amount, full_desc in section_80g_data:
            CreditCardTransaction.objects.create(
                statement=statement,
                user=self.demo_user,
                transaction_date=date.today() - timedelta(days=60),
                description=full_desc,
                merchant_name=desc,
                transaction_amount=Decimal(str(amount)),
                transaction_type='PURCHASE',
                category='MISCELLANEOUS'
            )
            transactions_created += 1
        
        # Section 24B Transactions (Home Loan EMI)
        section_24b_data = [
            ("HDFC Home Loan EMI", 45000, "Home loan EMI payment"),
            ("Housing Loan EMI", 42000, "Monthly housing loan payment")
        ]
        
        for desc, amount, full_desc in section_24b_data:
            CreditCardTransaction.objects.create(
                statement=statement,
                user=self.demo_user,
                transaction_date=date.today() - timedelta(days=15),
                description=full_desc,
                merchant_name=desc,
                transaction_amount=Decimal(str(amount)),
                transaction_type='PURCHASE',
                category='UTILITIES'
            )
            transactions_created += 1
        
        # Update statement transaction count - remove this as there's no such field
        # statement.total_transactions = transactions_created
        # statement.save()
        
        # Add some investments for comparison
        Investment.objects.create(
            user=self.demo_user,
            investment_type='ELSS',
            amount=Decimal('60000'),
            investment_date=date.today() - timedelta(days=90),
            financial_year='2024-25',
            tax_section='80C',
            eligible_deduction=Decimal('60000'),
            institution_name='HDFC ELSS Fund'
        )
        
        Investment.objects.create(
            user=self.demo_user,
            investment_type='HEALTH_INSURANCE',
            amount=Decimal('18000'),
            investment_date=date.today() - timedelta(days=100),
            financial_year='2024-25',
            tax_section='80D',
            eligible_deduction=Decimal('18000'),
            institution_name='Star Health Insurance'
        )
        
        print(f"✅ Created {transactions_created} sample transactions")
        print(f"✅ Added 2 investment records")
        print(f"✅ Created credit card statement: ****{statement.card_number_last_four}")
        
        
    def run_comprehensive_analysis(self):
        """Run comprehensive tax analysis and display results"""
        if not self.demo_user:
            self.setup_demo_user()
            
        calculator = AutomaticTaxCalculator(self.demo_user)
        analysis = calculator.calculate_comprehensive_tax_savings()
        
        print("\n" + "="*80)
        print("🎯 TAXWISE AUTOMATIC TAX CALCULATOR ANALYSIS")
        print("="*80)
        
        print(f"\n📊 Financial Year: {analysis['financial_year']}")
        print(f"📅 Analysis Date: {analysis['summary']['calculation_date'].strftime('%B %d, %Y')}")
        
        # Overall Summary
        print(f"\n💰 OVERALL TAX SAVINGS SUMMARY")
        print("-" * 40)
        total_deductions = analysis['summary']['total_eligible_deductions']
        print(f"Total Eligible Deductions: ₹{total_deductions:,.2f}")
        print(f"Tax Savings (10% bracket): ₹{analysis['summary']['tax_savings_10_percent']:,.2f}")
        print(f"Tax Savings (20% bracket): ₹{analysis['summary']['tax_savings_20_percent']:,.2f}")
        print(f"Tax Savings (30% bracket): ₹{analysis['summary']['tax_savings_30_percent']:,.2f}")
        
        # Section-wise Analysis
        print(f"\n📋 SECTION-WISE BREAKDOWN")
        print("-" * 50)
        
        for section, data in analysis['deductions_by_section'].items():
            print(f"\n🔹 {section}:")
            print(f"   Eligible Deduction: ₹{data['eligible_deduction']:,.2f}")
            
            if data.get('limit') != 'No Limit':
                print(f"   Limit: ₹{data['limit']:,.2f}")
                print(f"   Utilization: {data.get('utilization_percentage', 0):.1f}%")
                print(f"   Remaining: ₹{data.get('remaining_limit', 0):,.2f}")
            
            # Show sources
            if data.get('sources'):
                print(f"   Sources:")
                for source, amount in data['sources'].items():
                    if amount > 0:
                        source_name = source.replace('_', ' ').title()
                        print(f"     - {source_name}: ₹{amount:,.2f}")
            
            # Show key transactions
            if data.get('transactions'):
                print(f"   Recent Transactions ({len(data['transactions'])} total):")
                for i, txn in enumerate(data['transactions'][:3], 1):
                    # Handle different amount field names based on section
                    if section == '24B' and 'estimated_interest' in txn:
                        amount = txn['estimated_interest']
                    else:
                        amount = txn.get('amount', txn.get('transaction_amount', 0))
                    print(f"     {i}. {txn['description'][:40]} - ₹{amount:,.2f}")
                    
                if len(data['transactions']) > 3:
                    print(f"     ... and {len(data['transactions']) - 3} more")
        
        # Recommendations
        if analysis.get('recommendations'):
            print(f"\n💡 KEY RECOMMENDATIONS")
            print("-" * 30)
            for i, rec in enumerate(analysis['recommendations'][:5], 1):
                print(f"{i}. {rec}")
        
        # Tax Optimization Opportunities
        print(f"\n🚀 OPTIMIZATION OPPORTUNITIES")
        print("-" * 35)
        
        for section, data in analysis['deductions_by_section'].items():
            if data.get('utilization_percentage', 100) < 90 and data.get('remaining_limit', 0) > 1000:
                remaining = data['remaining_limit']
                potential_savings = remaining * Decimal('0.3')  # 30% bracket
                print(f"• {section}: Invest ₹{remaining:,.0f} more → Save ₹{potential_savings:,.0f}")
        
        return analysis
    
    def generate_section_analysis(self, section):
        """Generate detailed analysis for a specific section"""
        if not self.demo_user:
            self.setup_demo_user()
            
        calculator = AutomaticTaxCalculator(self.demo_user)
        
        section_methods = {
            '80C': calculator.calculate_section_80c_deductions,
            '80D': calculator.calculate_section_80d_deductions,
            '80G': calculator.calculate_section_80g_deductions,
            '24B': calculator.calculate_section_24b_deductions
        }
        
        if section not in section_methods:
            print(f"❌ Invalid section: {section}")
            return
        
        analysis = section_methods[section]()
        
        print(f"\n🎯 DETAILED ANALYSIS - SECTION {section}")
        print("="*50)
        
        print(f"Eligible Deduction: ₹{analysis['eligible_deduction']:,.2f}")
        
        if analysis.get('limit') != 'No Limit':
            print(f"Maximum Limit: ₹{analysis['limit']:,.2f}")
            print(f"Utilization: {analysis.get('utilization_percentage', 0):.1f}%")
            print(f"Remaining Capacity: ₹{analysis.get('remaining_limit', 0):,.2f}")
        
        # Tax savings at different brackets
        deduction = analysis['eligible_deduction']
        print(f"\nTax Savings Potential:")
        print(f"• 10% bracket: ₹{deduction * Decimal('0.1'):,.2f}")
        print(f"• 20% bracket: ₹{deduction * Decimal('0.2'):,.2f}")
        print(f"• 30% bracket: ₹{deduction * Decimal('0.3'):,.2f}")
        
        # Detailed transactions
        if analysis.get('transactions'):
            print(f"\n📋 All Transactions ({len(analysis['transactions'])}):")
            for i, txn in enumerate(analysis['transactions'], 1):
                date_str = txn['date'].strftime('%b %d, %Y')
                # Handle different amount field names based on section
                if section == '24B' and 'estimated_interest' in txn:
                    amount = txn['estimated_interest']
                else:
                    amount = txn.get('amount', txn.get('transaction_amount', 0))
                print(f"{i:2d}. {date_str} - {txn['description'][:35]} - ₹{amount:,.2f}")
        
        # Recommendations
        if analysis.get('recommendations'):
            print(f"\n💡 Optimization Recommendations:")
            for i, rec in enumerate(analysis['recommendations'], 1):
                print(f"{i}. {rec}")
        
        return analysis
    
    def demo_workflow(self):
        """Complete demo workflow"""
        print("🚀 Starting TaxWise Automatic Tax Calculator Demo...")
        
        # Setup
        self.setup_demo_user()
        self.create_sample_transactions()
        
        # Run analysis
        analysis = self.run_comprehensive_analysis()
        
        # Section-wise deep dive
        print(f"\n" + "="*80)
        print("🔍 SECTION-WISE DEEP DIVE")
        print("="*80)
        
        for section in ['80C', '80D', '80G', '24B']:
            self.generate_section_analysis(section)
        
        # Summary
        total_savings_30 = analysis['summary']['tax_savings_30_percent']
        print(f"\n" + "="*80)
        print("🎉 DEMO SUMMARY")
        print("="*80)
        print(f"✅ User Profile: Created with realistic financial data")
        print(f"✅ Transactions: Generated across all major tax sections")
        print(f"✅ Analysis: Comprehensive automatic calculations completed")
        print(f"✅ Potential Savings: Up to ₹{total_savings_30:,.2f} in 30% tax bracket")
        print(f"✅ System Status: Fully operational with AI-powered insights")
        
        print(f"\n🌟 The Automatic Tax Calculator successfully:")
        print(f"   • Analyzed existing financial transactions")
        print(f"   • Automatically categorized tax-relevant expenses")
        print(f"   • Calculated section-wise deductions with limits")
        print(f"   • Provided optimization recommendations")
        print(f"   • Generated comprehensive tax savings analysis")
        
        print(f"\n🎯 Access the web interface at: http://127.0.0.1:8000/tax-ai/auto-calculator/")
        print(f"👤 Login with: username='{self.demo_user.username}', password='demo123'")

def main():
    """Run the complete demo"""
    demo = TaxCalculatorDemo()
    demo.demo_workflow()

if __name__ == "__main__":
    main()