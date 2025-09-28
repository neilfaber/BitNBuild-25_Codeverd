"""
Comprehensive Database Population Script for Automatic Tax Calculator Demo
Creates realistic financial transaction data across multiple users and tax sections
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, date, timedelta
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TaxWise.settings')
django.setup()

from django.contrib.auth.models import User
from bank_analyzer.models import CreditCardStatement, CreditCardTransaction
from tax_optimization.models import FinancialTransaction, Investment, UserProfile
from cibil.models import CIBILScore

class TaxCalculatorDataPopulator:
    """Comprehensive data populator for automatic tax calculator demonstration"""
    
    def __init__(self):
        self.created_users = []
        self.created_statements = []
        self.created_transactions = []
        self.created_investments = []
        
    def clean_existing_data(self):
        """Clean existing demo data"""
        print("🧹 Cleaning existing demo data...")
        
        # Delete demo users and their data
        demo_users = User.objects.filter(username__startswith='demo_')
        for user in demo_users:
            CreditCardTransaction.objects.filter(user=user).delete()
            CreditCardStatement.objects.filter(user=user).delete()
            Investment.objects.filter(user=user).delete()
            FinancialTransaction.objects.filter(user=user).delete()
            CIBILScore.objects.filter(user=user).delete()
            UserProfile.objects.filter(user=user).delete()
            
        demo_users.delete()
        print("✅ Cleaned existing demo data")
        
    def create_user_profiles(self):
        """Create diverse user profiles for comprehensive testing"""
        print("👥 Creating user profiles...")
        
        user_profiles = [
            {
                'username': 'demo_young_professional',
                'email': 'young@taxwise.demo',
                'first_name': 'Arjun',
                'last_name': 'Sharma',
                'annual_income': Decimal('800000'),  # 8 LPA
                'age': 26,
                'pan_number': 'DEMO123001',
                'profile_type': 'Young Professional - High Growth Potential'
            },
            {
                'username': 'demo_senior_executive',
                'email': 'senior@taxwise.demo',
                'first_name': 'Priya',
                'last_name': 'Patel',
                'annual_income': Decimal('1500000'),  # 15 LPA
                'age': 42,
                'pan_number': 'DEMO123002',
                'profile_type': 'Senior Executive - Tax Optimization Focus'
            },
            {
                'username': 'demo_business_owner',
                'email': 'business@taxwise.demo',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'annual_income': Decimal('2500000'),  # 25 LPA
                'age': 35,
                'pan_number': 'DEMO123003',
                'profile_type': 'Business Owner - Complex Tax Structure'
            },
            {
                'username': 'demo_retiree',
                'email': 'retiree@taxwise.demo',
                'first_name': 'Sunita',
                'last_name': 'Agarwal',
                'annual_income': Decimal('600000'),  # 6 LPA
                'age': 62,
                'pan_number': 'DEMO123004',
                'profile_type': 'Senior Citizen - Health & Investment Focus'
            },
            {
                'username': 'demo_freelancer',
                'email': 'freelancer@taxwise.demo',
                'first_name': 'Vikash',
                'last_name': 'Singh',
                'annual_income': Decimal('1200000'),  # 12 LPA
                'age': 29,
                'pan_number': 'DEMO123005',
                'profile_type': 'Freelancer - Variable Income'
            }
        ]
        
        for profile_data in user_profiles:
            # Create user
            user = User.objects.create_user(
                username=profile_data['username'],
                email=profile_data['email'],
                first_name=profile_data['first_name'],
                last_name=profile_data['last_name'],
                password='demo123'
            )
            
            # Create user profile
            UserProfile.objects.create(
                user=user,
                pan_number=profile_data['pan_number'],
                annual_income=profile_data['annual_income'],
                age=profile_data['age'],
                preferred_tax_regime='OLD',
                financial_year='2024-25'
            )
            
            self.created_users.append({
                'user': user,
                'profile_type': profile_data['profile_type'],
                'annual_income': profile_data['annual_income'],
                'age': profile_data['age']
            })
            
        print(f"✅ Created {len(self.created_users)} user profiles")
        
    def create_credit_card_statements(self):
        """Create credit card statements for each user"""
        print("💳 Creating credit card statements...")
        
        for user_data in self.created_users:
            user = user_data['user']
            
            # Create multiple statements (last 6 months)
            for month_offset in range(6):
                statement_date = date.today() - timedelta(days=30 * month_offset)
                
                statement = CreditCardStatement.objects.create(
                    user=user,
                    statement_date=statement_date,
                    billing_period_start=statement_date - timedelta(days=30),
                    billing_period_end=statement_date,
                    payment_due_date=statement_date + timedelta(days=20),
                    card_number_last_four=f"{1234 + month_offset}",
                    cardholder_name=f"{user.first_name} {user.last_name}",
                    bank_name=random.choice(['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak']),
                    card_type=random.choice(['Visa', 'Mastercard', 'Rupay']),
                    total_credit_limit=Decimal(str(random.randint(200000, 500000))),
                    available_credit=Decimal(str(random.randint(100000, 300000))),
                    current_balance=Decimal(str(random.randint(50000, 150000))),
                    statement_balance=Decimal(str(random.randint(40000, 120000))),
                    minimum_amount_due=Decimal(str(random.randint(2000, 8000))),
                    total_amount_due=Decimal(str(random.randint(40000, 120000))),
                    credit_utilization_percentage=random.uniform(20, 80)
                )
                
                self.created_statements.append({
                    'statement': statement,
                    'user': user,
                    'user_data': user_data
                })
                
        print(f"✅ Created {len(self.created_statements)} credit card statements")
        
    def create_section_80c_transactions(self, statement_data):
        """Create Section 80C transactions (Investment deductions)"""
        user = statement_data['user']
        statement = statement_data['statement']
        user_data = statement_data['user_data']
        
        # Different 80C patterns based on user profile
        if 'young_professional' in user.username:
            transactions = [
                ('SIP Investment', 'ELSS SIP - HDFC Tax Saver Fund', random.randint(5000, 15000)),
                ('PPF Contribution', 'Public Provident Fund deposit', random.randint(12500, 25000)),
                ('LIC Premium', 'Life Insurance Premium payment', random.randint(15000, 30000)),
            ]
        elif 'senior_executive' in user.username:
            transactions = [
                ('ELSS Investment', 'Equity Linked Savings Scheme', random.randint(25000, 50000)),
                ('PPF Contribution', 'PPF annual contribution', random.randint(50000, 100000)),
                ('NSC Investment', 'National Savings Certificate', random.randint(25000, 50000)),
                ('Tax Saver FD', 'Tax Saver Fixed Deposit', random.randint(20000, 40000)),
            ]
        elif 'business_owner' in user.username:
            transactions = [
                ('EPF Contribution', 'Employee Provident Fund', random.randint(75000, 150000)),
                ('ULIP Premium', 'Unit Linked Insurance Plan', random.randint(50000, 100000)),
                ('Infrastructure Bonds', 'Tax saving infrastructure bonds', random.randint(25000, 50000)),
            ]
        elif 'retiree' in user.username:
            transactions = [
                ('PPF Contribution', 'Public Provident Fund', random.randint(25000, 75000)),
                ('Senior Citizens Scheme', 'SCSS Investment', random.randint(50000, 100000)),
                ('NSC Investment', 'National Savings Certificate', random.randint(15000, 40000)),
            ]
        else:  # freelancer
            transactions = [
                ('ELSS SIP', 'Tax Saver Mutual Fund SIP', random.randint(10000, 25000)),
                ('PPF Deposit', 'Public Provident Fund', random.randint(20000, 50000)),
                ('Life Insurance', 'Term Life Insurance Premium', random.randint(12000, 25000)),
            ]
            
        created_transactions = []
        for merchant, description, base_amount in transactions:
            # Add some variation
            amount = base_amount + random.randint(-2000, 2000)
            amount = max(1000, amount)  # Ensure positive
            
            transaction = CreditCardTransaction.objects.create(
                statement=statement,
                user=user,
                transaction_date=statement.statement_date - timedelta(days=random.randint(1, 25)),
                description=description,
                merchant_name=merchant,
                transaction_amount=Decimal(str(amount)),
                transaction_type='PURCHASE',
                category='INVESTMENT'
            )
            created_transactions.append(transaction)
            
        return created_transactions
        
    def create_section_80d_transactions(self, statement_data):
        """Create Section 80D transactions (Health Insurance)"""
        user = statement_data['user']
        statement = statement_data['statement']
        user_data = statement_data['user_data']
        
        # Health insurance based on age and profile
        if user_data['age'] >= 60:
            # Senior citizen - higher limits
            transactions = [
                ('Health Insurance', 'Senior Citizen Health Insurance Premium', random.randint(25000, 45000)),
                ('Family Floater', 'Family Health Insurance Policy', random.randint(15000, 25000)),
            ]
        elif 'business_owner' in user.username or 'senior_executive' in user.username:
            # Higher income - comprehensive coverage
            transactions = [
                ('Health Insurance', 'Premium Health Insurance Policy', random.randint(18000, 35000)),
                ('Critical Illness', 'Critical Illness Insurance', random.randint(8000, 15000)),
                ('Parents Insurance', 'Parents Health Insurance Premium', random.randint(12000, 20000)),
            ]
        else:
            # Standard coverage
            transactions = [
                ('Health Insurance', 'Basic Health Insurance Premium', random.randint(8000, 18000)),
                ('Family Coverage', 'Family Health Insurance', random.randint(5000, 12000)),
            ]
            
        created_transactions = []
        for merchant, description, base_amount in transactions:
            # Some months might not have health insurance payments
            if random.random() > 0.7:  # 30% chance of payment in any given month
                amount = base_amount + random.randint(-1000, 1000)
                amount = max(1000, amount)
                
                transaction = CreditCardTransaction.objects.create(
                    statement=statement,
                    user=user,
                    transaction_date=statement.statement_date - timedelta(days=random.randint(1, 25)),
                    description=description,
                    merchant_name=merchant,
                    transaction_amount=Decimal(str(amount)),
                    transaction_type='PURCHASE',
                    category='HEALTHCARE'
                )
                created_transactions.append(transaction)
                
        return created_transactions
        
    def create_section_80g_transactions(self, statement_data):
        """Create Section 80G transactions (Donations)"""
        user = statement_data['user']
        statement = statement_data['statement']
        
        # Donation patterns
        donation_options = [
            ('PM CARES Fund', 'PM CARES Fund donation', random.randint(2000, 10000)),
            ('Red Cross Society', 'Indian Red Cross Society donation', random.randint(1000, 5000)),
            ('Charitable Trust', 'Educational Trust donation', random.randint(2000, 8000)),
            ('Religious Donation', 'Temple/Religious institution donation', random.randint(1000, 15000)),
            ('NGO Donation', 'Child welfare NGO donation', random.randint(1500, 6000)),
            ('Disaster Relief', 'Natural disaster relief fund', random.randint(2000, 12000)),
        ]
        
        created_transactions = []
        # Random chance of donations (40% chance)
        if random.random() < 0.4:
            # Choose 1-2 donations
            selected_donations = random.sample(donation_options, random.randint(1, 2))
            
            for merchant, description, base_amount in selected_donations:
                amount = base_amount + random.randint(-500, 500)
                amount = max(500, amount)
                
                transaction = CreditCardTransaction.objects.create(
                    statement=statement,
                    user=user,
                    transaction_date=statement.statement_date - timedelta(days=random.randint(1, 25)),
                    description=description,
                    merchant_name=merchant,
                    transaction_amount=Decimal(str(amount)),
                    transaction_type='PURCHASE',
                    category='MISCELLANEOUS'
                )
                created_transactions.append(transaction)
                
        return created_transactions
        
    def create_section_24b_transactions(self, statement_data):
        """Create Section 24(b) transactions (Home Loan Interest)"""
        user = statement_data['user']
        statement = statement_data['statement']
        user_data = statement_data['user_data']
        
        # Home loan based on income level
        if user_data['annual_income'] > Decimal('2000000'):
            # High income - premium home loan
            emi_amount = random.randint(75000, 125000)
        elif user_data['annual_income'] > Decimal('1000000'):
            # Middle-high income
            emi_amount = random.randint(45000, 75000)
        else:
            # Standard home loan
            emi_amount = random.randint(25000, 45000)
            
        # 70% chance of having home loan
        if random.random() < 0.7:
            banks = ['HDFC Home Loan', 'SBI Home Loan', 'ICICI Home Loan', 'Axis Home Loan', 'LIC Housing Finance']
            selected_bank = random.choice(banks)
            
            transaction = CreditCardTransaction.objects.create(
                statement=statement,
                user=user,
                transaction_date=statement.statement_date - timedelta(days=random.randint(1, 10)),
                description=f'{selected_bank} EMI payment',
                merchant_name=selected_bank,
                transaction_amount=Decimal(str(emi_amount)),
                transaction_type='PURCHASE',
                category='UTILITIES'
            )
            
            return [transaction]
            
        return []
        
    def create_investment_records(self):
        """Create investment records for comparison with credit card data"""
        print("📊 Creating investment records...")
        
        for user_data in self.created_users:
            user = user_data['user']
            
            # Section 80C Investments
            investments_80c = [
                {
                    'type': 'PPF',
                    'amount': random.randint(50000, 150000),
                    'institution': 'SBI PPF Account',
                    'days_ago': random.randint(30, 300)
                },
                {
                    'type': 'ELSS',
                    'amount': random.randint(25000, 100000),
                    'institution': 'HDFC Tax Saver Fund',
                    'days_ago': random.randint(60, 200)
                },
            ]
            
            for inv in investments_80c:
                Investment.objects.create(
                    user=user,
                    investment_type=inv['type'],
                    amount=Decimal(str(inv['amount'])),
                    investment_date=date.today() - timedelta(days=inv['days_ago']),
                    financial_year='2024-25',
                    tax_section='80C',
                    eligible_deduction=Decimal(str(inv['amount'])),
                    institution_name=inv['institution']
                )
                self.created_investments.append(inv)
                
            # Section 80D Investments
            if random.random() < 0.8:  # 80% have health insurance investments
                health_amount = random.randint(15000, 35000)
                if user_data['age'] >= 60:
                    health_amount = random.randint(25000, 50000)
                    
                Investment.objects.create(
                    user=user,
                    investment_type='HEALTH_INSURANCE',
                    amount=Decimal(str(health_amount)),
                    investment_date=date.today() - timedelta(days=random.randint(30, 365)),
                    financial_year='2024-25',
                    tax_section='80D',
                    eligible_deduction=Decimal(str(health_amount)),
                    institution_name=random.choice(['Star Health', 'HDFC Ergo', 'ICICI Lombard', 'Bajaj Allianz'])
                )
                self.created_investments.append({'type': 'Health Insurance', 'amount': health_amount})
                
        print(f"✅ Created {len(self.created_investments)} investment records")
        
    def create_comprehensive_transactions(self):
        """Create comprehensive transactions across all tax sections"""
        print("💰 Creating comprehensive tax-relevant transactions...")
        
        transaction_count = 0
        
        for statement_data in self.created_statements:
            # Create transactions for each section
            transactions_80c = self.create_section_80c_transactions(statement_data)
            transactions_80d = self.create_section_80d_transactions(statement_data)
            transactions_80g = self.create_section_80g_transactions(statement_data)
            transactions_24b = self.create_section_24b_transactions(statement_data)
            
            all_transactions = transactions_80c + transactions_80d + transactions_80g + transactions_24b
            self.created_transactions.extend(all_transactions)
            transaction_count += len(all_transactions)
            
            # Add some regular non-tax transactions for realistic data
            regular_transactions = self.create_regular_transactions(statement_data)
            self.created_transactions.extend(regular_transactions)
            transaction_count += len(regular_transactions)
            
        print(f"✅ Created {transaction_count} total transactions")
        
    def create_regular_transactions(self, statement_data):
        """Create regular non-tax transactions for realistic credit card statements"""
        user = statement_data['user']
        statement = statement_data['statement']
        
        regular_categories = [
            ('DINING', ['Restaurant', 'Food Delivery', 'Cafe']),
            ('SHOPPING', ['Amazon', 'Flipkart', 'Mall Shopping']),
            ('GROCERY', ['Big Bazaar', 'DMart', 'Reliance Fresh']),
            ('FUEL', ['Petrol Pump', 'HP Fuel', 'Bharat Petroleum']),
            ('UTILITIES', ['Electricity Bill', 'Phone Bill', 'Internet Bill']),
            ('ENTERTAINMENT', ['Movie Tickets', 'Netflix', 'Spotify']),
        ]
        
        transactions = []
        
        # Create 5-15 regular transactions per statement
        for _ in range(random.randint(5, 15)):
            category, merchants = random.choice(regular_categories)
            merchant = random.choice(merchants)
            
            # Amount based on category
            if category == 'DINING':
                amount = random.randint(300, 2500)
            elif category == 'SHOPPING':
                amount = random.randint(500, 8000)
            elif category == 'GROCERY':
                amount = random.randint(1000, 5000)
            elif category == 'FUEL':
                amount = random.randint(800, 3000)
            elif category == 'UTILITIES':
                amount = random.randint(500, 2000)
            else:  # ENTERTAINMENT
                amount = random.randint(200, 1500)
                
            transaction = CreditCardTransaction.objects.create(
                statement=statement,
                user=user,
                transaction_date=statement.statement_date - timedelta(days=random.randint(1, 28)),
                description=f'{merchant} payment',
                merchant_name=merchant,
                transaction_amount=Decimal(str(amount)),
                transaction_type='PURCHASE',
                category=category
            )
            transactions.append(transaction)
            
        return transactions
        
    def create_cibil_scores(self):
        """Create CIBIL scores for demonstration"""
        print("📈 Creating CIBIL scores...")
        
        for user_data in self.created_users:
            user = user_data['user']
            
            # Score based on profile type
            if 'senior_executive' in user.username or 'business_owner' in user.username:
                base_score = random.randint(750, 850)
            elif 'young_professional' in user.username:
                base_score = random.randint(650, 750)
            elif 'retiree' in user.username:
                base_score = random.randint(700, 800)
            else:  # freelancer
                base_score = random.randint(600, 720)
                
            # Determine score range
            if base_score >= 750:
                score_range = 'Excellent'
            elif base_score >= 700:
                score_range = 'Good'
            elif base_score >= 650:
                score_range = 'Fair'
            else:
                score_range = 'Poor'
                
            CIBILScore.objects.create(
                user=user,
                calculated_score=base_score,
                score_range=score_range.upper(),
                payment_history_score=random.uniform(700, 900),
                credit_utilization_score=random.uniform(600, 850),
                credit_history_length_score=random.uniform(650, 800),
                credit_mix_score=random.uniform(700, 850),
                new_credit_score=random.uniform(650, 800),
                payment_history_percentage=random.uniform(85, 100),
                average_credit_utilization=random.uniform(20, 80),
                credit_history_months=random.randint(12, 120),
                total_credit_limit=Decimal(str(random.randint(200000, 1000000))),
                total_outstanding_balance=Decimal(str(random.randint(50000, 300000))),
                late_payments_count=random.randint(0, 3),
                missed_payments_count=random.randint(0, 1),
                overlimit_instances=random.randint(0, 2),
                calculation_date=datetime.now()
            )
            
        print(f"✅ Created CIBIL scores for {len(self.created_users)} users")
        
    def generate_summary_report(self):
        """Generate a comprehensive summary report"""
        print("\n" + "="*80)
        print("🎯 DATABASE POPULATION COMPLETE - SUMMARY REPORT")
        print("="*80)
        
        print(f"\n👥 USERS CREATED: {len(self.created_users)}")
        for i, user_data in enumerate(self.created_users, 1):
            user = user_data['user']
            print(f"{i:2d}. {user.username:25} | {user.first_name} {user.last_name:15} | {user_data['profile_type']}")
        
        print(f"\n💳 CREDIT CARD STATEMENTS: {len(self.created_statements)}")
        statements_per_user = len(self.created_statements) // len(self.created_users)
        print(f"    • {statements_per_user} statements per user (6 months of data)")
        
        print(f"\n💰 TRANSACTIONS CREATED: {len(self.created_transactions)}")
        
        # Analyze transactions by tax sections
        tax_relevant_transactions = 0
        section_counts = {'80C': 0, '80D': 0, '80G': 0, '24B': 0, 'Regular': 0}
        
        for transaction in self.created_transactions:
            if any(keyword in transaction.description.lower() for keyword in 
                   ['ppf', 'elss', 'lic', 'insurance', 'tax saver', 'provident']):
                section_counts['80C'] += 1
                tax_relevant_transactions += 1
            elif any(keyword in transaction.description.lower() for keyword in 
                     ['health insurance', 'medical insurance', 'mediclaim']):
                section_counts['80D'] += 1
                tax_relevant_transactions += 1
            elif any(keyword in transaction.description.lower() for keyword in 
                     ['donation', 'charity', 'pm cares', 'relief fund']):
                section_counts['80G'] += 1
                tax_relevant_transactions += 1
            elif any(keyword in transaction.description.lower() for keyword in 
                     ['home loan', 'housing loan', 'emi']):
                section_counts['24B'] += 1
                tax_relevant_transactions += 1
            else:
                section_counts['Regular'] += 1
                
        print(f"    • Tax-relevant transactions: {tax_relevant_transactions}")
        print(f"    • Section 80C (Investments): {section_counts['80C']}")
        print(f"    • Section 80D (Health Insurance): {section_counts['80D']}")
        print(f"    • Section 80G (Donations): {section_counts['80G']}")
        print(f"    • Section 24(b) (Home Loans): {section_counts['24B']}")
        print(f"    • Regular transactions: {section_counts['Regular']}")
        
        print(f"\n📊 INVESTMENT RECORDS: {len(self.created_investments)}")
        
        print(f"\n🎯 AUTOMATIC TAX CALCULATOR TESTING:")
        print(f"    • Access URL: http://127.0.0.1:8000/tax-ai/auto-calculator/")
        print(f"    • Demo Users Created: {len(self.created_users)}")
        print(f"    • Password for all demo users: demo123")
        
        print(f"\n📈 RECOMMENDED TESTING SEQUENCE:")
        print(f"    1. Login with any demo user (e.g., demo_young_professional)")
        print(f"    2. Navigate to Tax Optimizer → Auto Calculator")
        print(f"    3. View comprehensive tax analysis")
        print(f"    4. Check section-wise breakdowns")
        print(f"    5. Review optimization recommendations")
        print(f"    6. Test with different user profiles for varied results")
        
        print(f"\n🌟 FEATURES DEMONSTRATED:")
        print(f"    ✅ Automatic transaction categorization")
        print(f"    ✅ Section-wise tax calculations (80C, 80D, 80G, 24B)")
        print(f"    ✅ Investment vs Credit Card transaction comparison")
        print(f"    ✅ Tax savings calculations across brackets")
        print(f"    ✅ Utilization percentage and remaining limits")
        print(f"    ✅ Personalized optimization recommendations")
        print(f"    ✅ Multi-user profiles with diverse financial patterns")
        
        print("\n" + "="*80)
        print("🎉 DATABASE READY FOR COMPREHENSIVE TAX CALCULATOR TESTING!")
        print("="*80)
        
    def populate_database(self):
        """Main method to populate the entire database"""
        print("🚀 Starting Comprehensive Database Population for Automatic Tax Calculator...")
        print(f"📅 Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n")
        
        # Execute population steps
        self.clean_existing_data()
        self.create_user_profiles()
        self.create_credit_card_statements()
        self.create_comprehensive_transactions()
        self.create_investment_records()
        self.create_cibil_scores()
        self.generate_summary_report()

def main():
    """Run the comprehensive database population"""
    populator = TaxCalculatorDataPopulator()
    populator.populate_database()

if __name__ == "__main__":
    main()