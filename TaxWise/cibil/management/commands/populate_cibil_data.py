"""
Django management command to populate database with sample credit card data for CIBIL analysis

Usage:
    python manage.py populate_cibil_data --user_id=1
    python manage.py populate_cibil_data --username=admin
    python manage.py populate_cibil_data --create_user=testuser
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from bank_analyzer.models import CreditCardStatement, CreditCardTransaction, CreditCardFee, CreditCardInterest
from cibil.models import CIBILScore


class Command(BaseCommand):
    help = 'Populate database with sample credit card data for CIBIL analysis demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user_id',
            type=int,
            help='User ID to create data for',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username to create data for',
        )
        parser.add_argument(
            '--create_user',
            type=str,
            help='Create a new user with this username',
        )
        parser.add_argument(
            '--months',
            type=int,
            default=12,
            help='Number of months of data to generate (default: 12)',
        )
        parser.add_argument(
            '--cards',
            type=int,
            default=3,
            help='Number of credit cards to simulate (default: 3)',
        )
        parser.add_argument(
            '--scenario',
            choices=['excellent', 'good', 'fair', 'poor'],
            default='good',
            help='Credit behavior scenario to simulate (default: good)',
        )

    def handle(self, *args, **options):
        # Get or create user
        user = self.get_user(options)
        months = options['months']
        num_cards = options['cards']
        scenario = options['scenario']

        self.stdout.write(f"Creating credit card data for user: {user.username}")
        self.stdout.write(f"Scenario: {scenario} | Months: {months} | Cards: {num_cards}")

        # Clear existing data
        self.clear_existing_data(user)

        # Generate credit card data based on scenario
        cards_data = self.generate_cards_config(num_cards, scenario)
        
        for card_index, card_config in enumerate(cards_data):
            self.stdout.write(f"\nGenerating data for {card_config['bank']} card...")
            
            for month_offset in range(months):
                statement_date = datetime.now() - timedelta(days=30 * month_offset)
                self.create_monthly_statement(user, card_config, statement_date, scenario, month_offset)
            
            self.stdout.write(f"✓ Created {months} statements for {card_config['bank']}")

        # Generate CIBIL score based on the data
        self.generate_cibil_score(user, scenario)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Successfully created {months} months of data for {num_cards} credit cards!'
            )
        )
        self.stdout.write(f"🔗 View CIBIL dashboard: http://127.0.0.1:8000/cibil/dashboard/")

    def get_user(self, options):
        """Get or create user based on options"""
        if options['create_user']:
            username = options['create_user']
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': username.title(),
                    'is_active': True
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f"✓ Created new user: {username}")
            return user
        
        elif options['user_id']:
            try:
                return User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                raise CommandError(f'User with ID {options["user_id"]} does not exist.')
        
        elif options['username']:
            try:
                return User.objects.get(username=options['username'])
            except User.DoesNotExist:
                raise CommandError(f'User "{options["username"]}" does not exist.')
        
        else:
            raise CommandError('Please specify --user_id, --username, or --create_user')

    def clear_existing_data(self, user):
        """Clear existing credit card and CIBIL data for user"""
        CreditCardStatement.objects.filter(user=user).delete()
        CreditCardTransaction.objects.filter(user=user).delete()
        CIBILScore.objects.filter(user=user).delete()
        self.stdout.write("✓ Cleared existing data")

    def generate_cards_config(self, num_cards, scenario):
        """Generate credit card configurations based on scenario"""
        banks = [
            {'bank': 'HDFC Bank', 'card_type': 'Visa', 'last_four': '1234'},
            {'bank': 'ICICI Bank', 'card_type': 'Mastercard', 'last_four': '5678'},
            {'bank': 'SBI Bank', 'card_type': 'Visa', 'last_four': '9012'},
            {'bank': 'Axis Bank', 'card_type': 'Mastercard', 'last_four': '3456'},
            {'bank': 'Kotak Bank', 'card_type': 'Visa', 'last_four': '7890'}
        ]

        cards = []
        scenario_configs = {
            'excellent': {
                'credit_limits': [300000, 250000, 200000, 150000, 100000],
                'utilization_range': (5, 25),
                'late_payment_prob': 0.02
            },
            'good': {
                'credit_limits': [200000, 150000, 100000, 75000, 50000],
                'utilization_range': (15, 45),
                'late_payment_prob': 0.05
            },
            'fair': {
                'credit_limits': [100000, 75000, 50000, 40000, 30000],
                'utilization_range': (35, 65),
                'late_payment_prob': 0.12
            },
            'poor': {
                'credit_limits': [50000, 40000, 30000, 25000, 20000],
                'utilization_range': (60, 90),
                'late_payment_prob': 0.25
            }
        }

        config = scenario_configs[scenario]
        
        for i in range(num_cards):
            bank_info = banks[i % len(banks)]
            cards.append({
                **bank_info,
                'credit_limit': config['credit_limits'][i % len(config['credit_limits'])],
                'utilization_range': config['utilization_range'],
                'late_payment_prob': config['late_payment_prob']
            })
        
        return cards

    def create_monthly_statement(self, user, card_config, statement_date, scenario, month_offset):
        """Create a monthly credit card statement with transactions"""
        
        # Calculate statement period
        billing_end = statement_date.date()
        billing_start = billing_end - timedelta(days=30)
        payment_due = billing_end + timedelta(days=25)

        # Calculate balances based on scenario and age of data
        credit_limit = Decimal(str(card_config['credit_limit']))
        
        # Older statements have slightly different utilization
        utilization_factor = random.uniform(*card_config['utilization_range']) / 100
        if month_offset > 6:  # Older data shows improvement over time for good scenarios
            if scenario in ['excellent', 'good']:
                utilization_factor *= max(0.7, 1 - (month_offset * 0.02))
        
        current_balance = credit_limit * Decimal(str(utilization_factor))
        available_credit = credit_limit - current_balance
        
        # Previous balance (with some variation)
        previous_balance = current_balance * Decimal(str(random.uniform(0.8, 1.2)))
        
        # Minimum payment calculation
        minimum_payment = max(
            Decimal('500'),  # Minimum ₹500
            current_balance * Decimal('0.05')  # 5% of balance
        )

        # Create the statement
        statement = CreditCardStatement.objects.create(
            user=user,
            card_number_last_four=card_config['last_four'],
            cardholder_name=f"{user.first_name} {user.last_name}".strip() or user.username.title(),
            bank_name=card_config['bank'],
            card_type=card_config['card_type'],
            statement_date=billing_end,
            billing_period_start=billing_start,
            billing_period_end=billing_end,
            payment_due_date=payment_due,
            previous_balance=previous_balance,
            current_balance=current_balance,
            statement_balance=current_balance,
            minimum_amount_due=minimum_payment,
            total_amount_due=current_balance,
            total_credit_limit=credit_limit,
            available_credit=available_credit,
            credit_utilization_percentage=float(utilization_factor * 100),
            processing_status='PROCESSED',
            ai_confidence_score=0.95
        )

        # Generate transactions for this statement
        self.create_transactions(statement, card_config, scenario, billing_start, billing_end)
        
        # Update statement totals based on transactions
        self.update_statement_totals(statement)

        return statement

    def create_transactions(self, statement, card_config, scenario, start_date, end_date):
        """Generate realistic credit card transactions"""
        
        # Transaction templates with realistic Indian spending patterns
        transaction_templates = {
            'PURCHASE': [
                ('Amazon India', 'ONLINE', 'SHOPPING'),
                ('Flipkart', 'ONLINE', 'SHOPPING'),
                ('Big Bazaar', 'GROCERY', 'GROCERY'),
                ('McDonald\'s', 'DINING', 'DINING'),
                ('Domino\'s Pizza', 'DINING', 'DINING'),
                ('Indian Oil Petrol Pump', 'FUEL', 'FUEL'),
                ('Reliance Trends', 'SHOPPING', 'SHOPPING'),
                ('BookMyShow', 'ENTERTAINMENT', 'ENTERTAINMENT'),
                ('Uber', 'TRANSPORT', 'TRANSPORT'),
                ('Zomato', 'DINING', 'DINING'),
                ('DMart', 'GROCERY', 'GROCERY'),
                ('Westside', 'SHOPPING', 'SHOPPING'),
                ('PVR Cinemas', 'ENTERTAINMENT', 'ENTERTAINMENT'),
                ('Lifestyle Store', 'SHOPPING', 'SHOPPING'),
                ('Cafe Coffee Day', 'DINING', 'DINING'),
                ('Spencer\'s Retail', 'GROCERY', 'GROCERY'),
                ('Shell Petrol Pump', 'FUEL', 'FUEL'),
                ('Myntra', 'ONLINE', 'SHOPPING'),
                ('Swiggy', 'DINING', 'DINING'),
                ('Metro Cash & Carry', 'GROCERY', 'GROCERY')
            ]
        }

        # Generate 15-35 transactions per month based on scenario
        transaction_counts = {
            'excellent': random.randint(20, 35),
            'good': random.randint(18, 30),
            'fair': random.randint(15, 25),
            'poor': random.randint(12, 20)
        }
        
        num_transactions = transaction_counts.get(scenario, 20)
        
        total_purchases = Decimal('0')
        
        for i in range(num_transactions):
            # Random transaction date within billing period
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            transaction_date = start_date + timedelta(days=random_days)
            
            # Select random transaction template
            merchant, merchant_cat, category = random.choice(transaction_templates['PURCHASE'])
            
            # Generate amount based on category and scenario
            amount = self.generate_transaction_amount(category, scenario)
            total_purchases += amount
            
            # Create transaction
            CreditCardTransaction.objects.create(
                statement=statement,
                user=statement.user,
                transaction_date=transaction_date,
                posting_date=transaction_date + timedelta(days=random.randint(0, 2)),
                description=f"{merchant} Purchase",
                merchant_name=merchant,
                merchant_category=merchant_cat,
                transaction_amount=amount,
                billing_amount=amount,
                transaction_type='PURCHASE',
                category=category,
                currency='INR',
                reward_points_earned=int(amount / 100),  # 1 point per ₹100
                cashback_earned=amount * Decimal('0.01'),  # 1% cashback
                reward_rate=1.0,
                is_verified=True
            )

        # Add payment transaction (based on payment behavior)
        payment_date = end_date + timedelta(days=random.randint(1, 30))
        payment_behavior = self.get_payment_behavior(scenario)
        
        payment_amount = total_purchases * Decimal(str(payment_behavior['payment_ratio']))
        
        # Sometimes add late payment fee
        if random.random() < card_config['late_payment_prob']:
            payment_date += timedelta(days=random.randint(1, 15))  # Late payment
            # Add late fee
            CreditCardFee.objects.create(
                statement=statement,
                user=statement.user,
                fee_type='LATE_PAYMENT',
                fee_description='Late Payment Fee',
                fee_amount=Decimal('500'),
                fee_date=payment_date,
                is_reversed=False
            )

        if payment_amount > 0:
            CreditCardTransaction.objects.create(
                statement=statement,
                user=statement.user,
                transaction_date=payment_date,
                posting_date=payment_date,
                description=f"Payment - Thank You",
                transaction_amount=-payment_amount,  # Negative for payment
                billing_amount=-payment_amount,
                transaction_type='PAYMENT',
                category='TRANSFER',
                currency='INR',
                is_verified=True
            )

    def generate_transaction_amount(self, category, scenario):
        """Generate realistic transaction amounts based on category and scenario"""
        
        base_amounts = {
            'DINING': (200, 1500),
            'SHOPPING': (500, 8000),
            'GROCERY': (800, 3000),
            'FUEL': (1000, 3000),
            'TRANSPORT': (50, 500),
            'ENTERTAINMENT': (300, 1200),
            'ONLINE': (300, 5000)
        }
        
        min_amt, max_amt = base_amounts.get(category, (100, 1000))
        
        # Adjust based on scenario
        scenario_multipliers = {
            'excellent': 1.3,
            'good': 1.0,
            'fair': 0.8,
            'poor': 0.6
        }
        
        multiplier = scenario_multipliers.get(scenario, 1.0)
        min_amt = int(min_amt * multiplier)
        max_amt = int(max_amt * multiplier)
        
        return Decimal(str(random.randint(min_amt, max_amt)))

    def get_payment_behavior(self, scenario):
        """Get payment behavior patterns based on scenario"""
        behaviors = {
            'excellent': {'payment_ratio': random.uniform(0.95, 1.0)},  # Full payment
            'good': {'payment_ratio': random.uniform(0.85, 1.0)},  # Mostly full payment
            'fair': {'payment_ratio': random.uniform(0.25, 0.85)},  # Partial payments
            'poor': {'payment_ratio': random.uniform(0.05, 0.35)}   # Minimum payments
        }
        return behaviors.get(scenario, behaviors['good'])

    def update_statement_totals(self, statement):
        """Update statement totals based on transactions"""
        transactions = statement.transactions.all()
        
        total_purchases = sum(
            t.transaction_amount for t in transactions 
            if t.transaction_type == 'PURCHASE'
        )
        
        total_payments = sum(
            abs(t.transaction_amount) for t in transactions 
            if t.transaction_type == 'PAYMENT'
        )
        
        total_fees = CreditCardFee.objects.filter(statement=statement).aggregate(
            total=models.Sum('fee_amount')
        )['total'] or Decimal('0')
        
        # Update statement
        statement.total_purchases = total_purchases
        statement.total_payments = total_payments
        statement.total_fees = total_fees
        statement.reward_points_earned = sum(t.reward_points_earned for t in transactions)
        statement.cashback_earned = sum(t.cashback_earned for t in transactions)
        statement.save()

    def generate_cibil_score(self, user, scenario):
        """Generate a CIBIL score based on the scenario"""
        
        score_ranges = {
            'excellent': random.randint(750, 850),
            'good': random.randint(650, 749),
            'fair': random.randint(550, 649),
            'poor': random.randint(350, 549)
        }
        
        calculated_score = score_ranges[scenario]
        
        # Determine score range
        if calculated_score >= 750:
            score_range = 'EXCELLENT'
        elif calculated_score >= 650:
            score_range = 'GOOD'
        elif calculated_score >= 550:
            score_range = 'FAIR'
        else:
            score_range = 'POOR'

        # Get actual data from statements for calculations
        statements = CreditCardStatement.objects.filter(user=user)
        
        if statements.exists():
            avg_utilization = statements.aggregate(
                avg_util=models.Avg('credit_utilization_percentage')
            )['avg_util'] or 0
            
            total_credit_limit = statements.aggregate(
                total_limit=models.Sum('total_credit_limit')
            )['total_limit'] or 0
            
            # Count late payments based on fees
            late_payments = CreditCardFee.objects.filter(
                statement__user=user,
                fee_type='LATE_PAYMENT'
            ).count()
            
        else:
            avg_utilization = 30.0
            total_credit_limit = 150000
            late_payments = 0

        # Create CIBIL score record
        CIBILScore.objects.create(
            user=user,
            calculated_score=calculated_score,
            score_range=score_range,
            payment_history_score=random.uniform(0.7, 1.0),
            credit_utilization_score=random.uniform(0.6, 0.95),
            credit_history_length_score=random.uniform(0.5, 0.9),
            credit_mix_score=random.uniform(0.6, 0.85),
            new_credit_score=random.uniform(0.7, 0.95),
            payment_history_percentage=random.uniform(85.0, 99.5),
            average_credit_utilization=avg_utilization,
            credit_history_months=random.randint(12, 60),
            total_credit_limit=total_credit_limit,
            total_outstanding_balance=total_credit_limit * Decimal(str(avg_utilization / 100)),
            late_payments_count=late_payments,
            missed_payments_count=max(0, late_payments - random.randint(0, 2)),
            calculation_date=timezone.now(),
            data_source_period_start=(timezone.now() - timedelta(days=365)).date(),
            data_source_period_end=timezone.now().date()
        )
        
        self.stdout.write(f"✓ Generated CIBIL score: {calculated_score} ({score_range})")