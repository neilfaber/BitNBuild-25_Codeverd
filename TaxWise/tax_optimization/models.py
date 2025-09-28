# TaxWise AI-Powered Tax Optimization Engine
# Django Models for Financial Data Management

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class UserProfile(models.Model):
    """Extended user profile for tax-specific information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pan_number = models.CharField(max_length=10, unique=True, null=True, blank=True)
    aadhaar_number = models.CharField(max_length=12, unique=True, null=True, blank=True)
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    age = models.IntegerField(validators=[MinValueValidator(18), MaxValueValidator(100)])
    preferred_tax_regime = models.CharField(
        max_length=10,
        choices=[('OLD', 'Old Regime'), ('NEW', 'New Regime')],
        default='NEW'
    )
    financial_year = models.CharField(max_length=7, default='2024-25')  # Format: YYYY-YY
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.pan_number}"

class BankAccount(models.Model):
    """User's bank account information"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=11)
    account_type = models.CharField(
        max_length=20,
        choices=[
            ('SAVINGS', 'Savings Account'),
            ('CURRENT', 'Current Account'),
            ('SALARY', 'Salary Account')
        ]
    )
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number[-4:]}"

class FinancialTransaction(models.Model):
    """Individual financial transactions from bank statements"""
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('INVESTMENT', 'Investment'),
        ('TRANSFER', 'Transfer'),
        ('EMI', 'EMI Payment'),
        ('INSURANCE', 'Insurance Premium'),
        ('TAX', 'Tax Payment'),
        ('OTHER', 'Other')
    ]
    
    INCOME_CATEGORIES = [
        ('SALARY', 'Salary'),
        ('BUSINESS', 'Business Income'),
        ('CAPITAL_GAINS', 'Capital Gains'),
        ('INTEREST', 'Interest Income'),
        ('DIVIDEND', 'Dividend'),
        ('RENTAL', 'Rental Income'),
        ('OTHER_INCOME', 'Other Income')
    ]
    
    EXPENSE_CATEGORIES = [
        ('RENT', 'House Rent'),
        ('MEDICAL', 'Medical Expenses'),
        ('EDUCATION', 'Education'),
        ('FOOD', 'Food & Dining'),
        ('TRANSPORT', 'Transportation'),
        ('UTILITIES', 'Utilities'),
        ('ENTERTAINMENT', 'Entertainment'),
        ('SHOPPING', 'Shopping'),
        ('OTHER_EXPENSE', 'Other Expenses')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Transaction Details
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    # AI-Generated Categories
    ai_category = models.CharField(max_length=50, null=True, blank=True)
    ai_subcategory = models.CharField(max_length=50, null=True, blank=True)
    ai_confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        null=True, blank=True
    )
    
    # Manual Override
    manual_category = models.CharField(max_length=50, null=True, blank=True)
    is_manually_categorized = models.BooleanField(default=False)
    
    # Tax Relevance
    is_tax_relevant = models.BooleanField(default=False)
    tax_section = models.CharField(max_length=10, null=True, blank=True)  # 80C, 80D, etc.
    is_deductible = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by_ai = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['transaction_type', 'is_tax_relevant']),
            models.Index(fields=['ai_category', 'ai_confidence_score']),
        ]

    def __str__(self):
        return f"{self.date} - {self.amount} - {self.description[:50]}"

    @property
    def final_category(self):
        """Return manual category if set, otherwise AI category"""
        return self.manual_category if self.is_manually_categorized else self.ai_category

class TaxRule(models.Model):
    """Tax rules and slabs for different regimes"""
    REGIME_CHOICES = [
        ('OLD', 'Old Tax Regime'),
        ('NEW', 'New Tax Regime')
    ]
    
    regime = models.CharField(max_length=10, choices=REGIME_CHOICES)
    financial_year = models.CharField(max_length=7)  # 2024-25
    
    # Tax Slabs
    min_income = models.DecimalField(max_digits=12, decimal_places=2)
    max_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    
    # Deduction Limits
    section_name = models.CharField(max_length=10, null=True, blank=True)  # 80C, 80D, etc.
    deduction_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['regime', 'financial_year', 'min_income', 'section_name']

    def __str__(self):
        return f"{self.regime} - {self.financial_year} - {self.min_income}-{self.max_income} @{self.tax_rate}%"

class Investment(models.Model):
    """User's investments and tax-saving instruments"""
    INVESTMENT_TYPES = [
        ('PPF', 'Public Provident Fund'),
        ('EPF', 'Employee Provident Fund'),
        ('ELSS', 'Equity Linked Savings Scheme'),
        ('NSC', 'National Savings Certificate'),
        ('TAX_SAVER_FD', 'Tax Saver Fixed Deposit'),
        ('LIFE_INSURANCE', 'Life Insurance Premium'),
        ('HEALTH_INSURANCE', 'Health Insurance Premium'),
        ('HOME_LOAN', 'Home Loan Principal'),
        ('EDUCATION_LOAN', 'Education Loan Interest'),
        ('NPS', 'National Pension System'),
        ('OTHER', 'Other Investments')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    investment_type = models.CharField(max_length=30, choices=INVESTMENT_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    investment_date = models.DateField()
    financial_year = models.CharField(max_length=7)
    
    # Tax Benefits
    tax_section = models.CharField(max_length=10)  # 80C, 80D, 80E, etc.
    eligible_deduction = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Investment Details
    institution_name = models.CharField(max_length=100, null=True, blank=True)
    policy_number = models.CharField(max_length=50, null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.investment_type} - ₹{self.amount} - {self.tax_section}"

class TaxCalculation(models.Model):
    """Calculated tax liability for a user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tax_calculations')
    financial_year = models.CharField(max_length=7)
    
    # Income Details
    gross_total_income = models.DecimalField(max_digits=12, decimal_places=2)
    salary_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    business_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    capital_gains = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Deductions
    standard_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    section_80c_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    section_80d_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Tax Calculation - Old Regime
    old_regime_taxable_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    old_regime_tax_liability = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    old_regime_cess = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    old_regime_total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Tax Calculation - New Regime
    new_regime_taxable_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    new_regime_tax_liability = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    new_regime_cess = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_regime_total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Recommended Regime
    recommended_regime = models.CharField(max_length=10, choices=[('OLD', 'Old'), ('NEW', 'New')])
    tax_savings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Metadata
    calculation_date = models.DateTimeField(auto_now_add=True)
    is_final = models.BooleanField(default=False)
    is_automatic = models.BooleanField(default=False)  # Flag for automatic calculations

    class Meta:
        unique_together = ['user', 'financial_year']
        ordering = ['-calculation_date']

    def __str__(self):
        return f"{self.user.username} - {self.financial_year} - ₹{self.recommended_regime_total_tax}"

    @property
    def recommended_regime_total_tax(self):
        if self.recommended_regime == 'OLD':
            return self.old_regime_total_tax
        return self.new_regime_total_tax

class TaxOptimizationRecommendation(models.Model):
    """AI-generated tax optimization recommendations"""
    RECOMMENDATION_TYPES = [
        ('INVESTMENT', 'Investment Recommendation'),
        ('DEDUCTION', 'Deduction Opportunity'),
        ('REGIME_SWITCH', 'Tax Regime Switch'),
        ('TIMING', 'Transaction Timing'),
        ('RESTRUCTURE', 'Income Restructuring')
    ]
    
    PRIORITY_LEVELS = [
        ('HIGH', 'High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Priority')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Financial Impact
    potential_savings = models.DecimalField(max_digits=10, decimal_places=2)
    investment_required = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    roi_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Recommendation Details
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    tax_section = models.CharField(max_length=10, null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    
    # AI Metadata
    ai_model_version = models.CharField(max_length=50)
    confidence_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    # User Interaction
    is_accepted = models.BooleanField(null=True, blank=True)  # None = pending, True/False = decision
    user_feedback = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-potential_savings', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title} - ₹{self.potential_savings} savings"

class FileUpload(models.Model):
    """Track uploaded financial documents"""
    FILE_TYPES = [
        ('BANK_STATEMENT', 'Bank Statement'),
        ('SALARY_SLIP', 'Salary Slip'),
        ('FORM_16', 'Form 16'),
        ('INVESTMENT_PROOF', 'Investment Proof'),
        ('INSURANCE_PREMIUM', 'Insurance Premium Receipt'),
        ('OTHER', 'Other Document')
    ]
    
    PROCESSING_STATUS = [
        ('UPLOADED', 'Uploaded'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIALLY_PROCESSED', 'Partially Processed')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    file_name = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='documents/%Y/%m/')
    file_size = models.BigIntegerField()  # in bytes
    
    # Processing Status
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='UPLOADED')
    processing_message = models.TextField(null=True, blank=True)
    transactions_extracted = models.IntegerField(default=0)
    
    # AI Processing
    ai_processed = models.BooleanField(default=False)
    ai_processing_time = models.FloatField(null=True, blank=True)  # in seconds
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.file_name} - {self.processing_status}"

class AIModelPerformance(models.Model):
    """Track AI model performance metrics"""
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50)
    task_type = models.CharField(max_length=50)  # classification, recommendation, etc.
    
    # Performance Metrics
    accuracy = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    precision = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    recall = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    f1_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    # Processing Metrics
    avg_processing_time = models.FloatField()  # in seconds
    total_predictions = models.IntegerField()
    successful_predictions = models.IntegerField()
    
    # Date Range
    measurement_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['model_name', 'model_version', 'measurement_date']

    def __str__(self):
        return f"{self.model_name} v{self.model_version} - {self.accuracy:.3f} accuracy"


# CIBIL Score and Credit Analysis Models

class CreditProfile(models.Model):
    """User's credit profile and CIBIL score information"""
    CREDIT_SCORE_RANGES = [
        ('POOR', 'Poor (300-549)'),
        ('FAIR', 'Fair (550-649)'),
        ('GOOD', 'Good (650-749)'),
        ('VERY_GOOD', 'Very Good (750-799)'),
        ('EXCELLENT', 'Excellent (800-900)')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credit_profile')
    
    # CIBIL Score Information
    current_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)],
        help_text="CIBIL score ranges from 300 to 900"
    )
    previous_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)],
        null=True, blank=True
    )
    score_range = models.CharField(max_length=15, choices=CREDIT_SCORE_RANGES)
    last_updated = models.DateField()
    
    # Credit History Metrics
    credit_history_length = models.IntegerField(help_text="Credit history in months")
    total_accounts = models.IntegerField(default=0)
    active_accounts = models.IntegerField(default=0)
    closed_accounts = models.IntegerField(default=0)
    
    # Credit Utilization
    total_credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_outstanding = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_utilization_ratio = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Credit utilization as percentage"
    )
    
    # Payment History
    on_time_payments = models.IntegerField(default=0)
    late_payments = models.IntegerField(default=0)
    missed_payments = models.IntegerField(default=0)
    payment_history_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=100
    )
    
    # Credit Mix
    credit_cards = models.IntegerField(default=0)
    personal_loans = models.IntegerField(default=0)
    home_loans = models.IntegerField(default=0)
    auto_loans = models.IntegerField(default=0)
    other_loans = models.IntegerField(default=0)
    
    # Recent Credit Activity
    hard_inquiries_6_months = models.IntegerField(default=0)
    hard_inquiries_12_months = models.IntegerField(default=0)
    new_accounts_6_months = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - CIBIL Score: {self.current_score}"

    @property
    def score_change(self):
        if self.previous_score:
            return self.current_score - self.previous_score
        return 0

class CreditAccount(models.Model):
    """Individual credit accounts (cards, loans, etc.)"""
    ACCOUNT_TYPES = [
        ('CREDIT_CARD', 'Credit Card'),
        ('PERSONAL_LOAN', 'Personal Loan'),
        ('HOME_LOAN', 'Home Loan'),
        ('AUTO_LOAN', 'Auto Loan'),
        ('EDUCATION_LOAN', 'Education Loan'),
        ('GOLD_LOAN', 'Gold Loan'),
        ('BUSINESS_LOAN', 'Business Loan'),
        ('OVERDRAFT', 'Overdraft'),
        ('OTHER', 'Other')
    ]
    
    ACCOUNT_STATUS = [
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('SETTLED', 'Settled'),
        ('WRITTEN_OFF', 'Written Off'),
        ('DORMANT', 'Dormant')
    ]
    
    PAYMENT_STATUS = [
        ('CURRENT', 'Current'),
        ('30_DAYS', '30 Days Late'),
        ('60_DAYS', '60 Days Late'),
        ('90_DAYS', '90 Days Late'),
        ('120_PLUS', '120+ Days Late'),
        ('DEFAULT', 'Default')
    ]

    credit_profile = models.ForeignKey(CreditProfile, on_delete=models.CASCADE, related_name='accounts')
    
    # Account Details
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)  # Masked for security
    account_status = models.CharField(max_length=15, choices=ACCOUNT_STATUS)
    
    # Credit Limits and Balances
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    available_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Account Timeline
    account_opened = models.DateField()
    account_closed = models.DateField(null=True, blank=True)
    last_payment_date = models.DateField(null=True, blank=True)
    
    # Payment Status
    current_payment_status = models.CharField(max_length=15, choices=PAYMENT_STATUS)
    days_past_due = models.IntegerField(default=0)
    
    # Account Performance
    highest_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lowest_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_type} - {self.account_number}"

    @property
    def utilization_percentage(self):
        if self.credit_limit > 0:
            return (self.current_balance / self.credit_limit) * 100
        return 0

class PaymentHistory(models.Model):
    """Monthly payment history for credit accounts"""
    PAYMENT_STATUS_CHOICES = [
        ('PAID_ON_TIME', 'Paid on Time'),
        ('LATE_1_30', 'Late 1-30 Days'),
        ('LATE_31_60', 'Late 31-60 Days'),
        ('LATE_61_90', 'Late 61-90 Days'),
        ('LATE_91_120', 'Late 91-120 Days'),
        ('LATE_120_PLUS', 'Late 120+ Days'),
        ('MISSED', 'Missed Payment'),
        ('PARTIAL', 'Partial Payment')
    ]

    credit_account = models.ForeignKey(CreditAccount, on_delete=models.CASCADE, related_name='payment_history')
    
    # Payment Details
    payment_month = models.DateField()  # First day of the month
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=15, choices=PAYMENT_STATUS_CHOICES)
    days_late = models.IntegerField(default=0)
    
    # Outstanding Balance
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['credit_account', 'payment_month']
        ordering = ['-payment_month']

    def __str__(self):
        return f"{self.credit_account.bank_name} - {self.payment_month.strftime('%b %Y')} - {self.payment_status}"

class CreditScoreHistory(models.Model):
    """Track CIBIL score changes over time"""
    credit_profile = models.ForeignKey(CreditProfile, on_delete=models.CASCADE, related_name='score_history')
    
    score_date = models.DateField()
    cibil_score = models.IntegerField(validators=[MinValueValidator(300), MaxValueValidator(900)])
    score_change = models.IntegerField(default=0)  # Change from previous score
    
    # Factors affecting score
    payment_history_impact = models.CharField(max_length=10, choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('NEUTRAL', 'Neutral')])
    credit_utilization_impact = models.CharField(max_length=10, choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('NEUTRAL', 'Neutral')])
    credit_history_impact = models.CharField(max_length=10, choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('NEUTRAL', 'Neutral')])
    credit_mix_impact = models.CharField(max_length=10, choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('NEUTRAL', 'Neutral')])
    new_credit_impact = models.CharField(max_length=10, choices=[('POSITIVE', 'Positive'), ('NEGATIVE', 'Negative'), ('NEUTRAL', 'Neutral')])
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['credit_profile', 'score_date']
        ordering = ['-score_date']

    def __str__(self):
        return f"{self.credit_profile.user.username} - {self.score_date} - {self.cibil_score}"

class CreditScoreFactors(models.Model):
    """Detailed analysis of factors affecting CIBIL score"""
    IMPACT_LEVELS = [
        ('VERY_HIGH', 'Very High Impact'),
        ('HIGH', 'High Impact'),
        ('MEDIUM', 'Medium Impact'),
        ('LOW', 'Low Impact'),
        ('VERY_LOW', 'Very Low Impact')
    ]
    
    FACTOR_TYPES = [
        ('PAYMENT_HISTORY', 'Payment History'),
        ('CREDIT_UTILIZATION', 'Credit Utilization'),
        ('CREDIT_AGE', 'Credit Age'),
        ('CREDIT_MIX', 'Credit Mix'),
        ('RECENT_INQUIRIES', 'Recent Credit Inquiries'),
        ('PUBLIC_RECORDS', 'Public Records'),
        ('ACCOUNT_STATUS', 'Account Status')
    ]

    credit_profile = models.ForeignKey(CreditProfile, on_delete=models.CASCADE, related_name='score_factors')
    
    factor_type = models.CharField(max_length=20, choices=FACTOR_TYPES)
    factor_name = models.CharField(max_length=100)
    current_value = models.CharField(max_length=100)  # e.g., "85%", "24 months", etc.
    impact_level = models.CharField(max_length=15, choices=IMPACT_LEVELS)
    is_positive = models.BooleanField()  # True if positive impact, False if negative
    
    # Scoring contribution
    points_contribution = models.IntegerField()  # Points added/subtracted from base score
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['credit_profile', 'factor_type']

    def __str__(self):
        return f"{self.credit_profile.user.username} - {self.factor_name}"

class CreditImprovementRecommendation(models.Model):
    """AI-generated recommendations to improve CIBIL score"""
    RECOMMENDATION_CATEGORIES = [
        ('PAYMENT_BEHAVIOR', 'Payment Behavior'),
        ('CREDIT_UTILIZATION', 'Credit Utilization'),
        ('CREDIT_MIX', 'Credit Mix'),
        ('ACCOUNT_MANAGEMENT', 'Account Management'),
        ('CREDIT_INQUIRIES', 'Credit Inquiries'),
        ('DEBT_CONSOLIDATION', 'Debt Consolidation')
    ]
    
    PRIORITY_LEVELS = [
        ('CRITICAL', 'Critical - Immediate Action'),
        ('HIGH', 'High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Priority')
    ]

    credit_profile = models.ForeignKey(CreditProfile, on_delete=models.CASCADE, related_name='improvement_recommendations')
    
    category = models.CharField(max_length=25, choices=RECOMMENDATION_CATEGORIES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    action_steps = models.TextField()  # JSON formatted steps
    
    # Impact Prediction
    expected_score_improvement = models.IntegerField(help_text="Expected CIBIL score improvement points")
    timeframe_months = models.IntegerField(help_text="Expected timeframe to see improvement in months")
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    
    # Implementation
    is_easy_to_implement = models.BooleanField()
    cost_involved = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # AI Metadata
    ai_confidence = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    # User Interaction
    is_accepted = models.BooleanField(null=True, blank=True)
    user_notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-expected_score_improvement']

    def __str__(self):
        return f"{self.credit_profile.user.username} - {self.title}"

class CreditScoreWhatIfScenario(models.Model):
    """What-if scenarios for CIBIL score improvement simulations"""
    credit_profile = models.ForeignKey(CreditProfile, on_delete=models.CASCADE, related_name='whatif_scenarios')
    
    scenario_name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Scenario Parameters
    payment_improvement = models.BooleanField(default=False, help_text="Improve payment history to 100%")
    reduce_utilization_to = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Target credit utilization percentage"
    )
    close_credit_cards = models.IntegerField(default=0, help_text="Number of credit cards to close")
    increase_credit_limit_by = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Amount to increase total credit limit"
    )
    wait_months = models.IntegerField(default=0, help_text="Months to wait for natural improvement")
    
    # Predicted Results
    predicted_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)],
        help_text="Predicted CIBIL score after implementing scenario"
    )
    score_improvement = models.IntegerField(help_text="Expected score improvement points")
    confidence_level = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.credit_profile.user.username} - {self.scenario_name} (+{self.score_improvement} points)"


# Smart Financial Data Ingestion Models

class FinancialDataIngestion(models.Model):
    """Main model to track financial data ingestion sessions"""
    SESSION_TYPES = [
        ('BANK_STATEMENT', 'Bank Statement Upload'),
        ('CREDIT_CARD_STATEMENT', 'Credit Card Statement'),
        ('SALARY_SLIP', 'Salary Slip'),
        ('INVESTMENT_STATEMENT', 'Investment Statement'),
        ('BULK_UPLOAD', 'Multiple Documents'),
        ('API_SYNC', 'API Data Synchronization')
    ]
    
    INGESTION_STATUS = [
        ('INITIATED', 'Ingestion Initiated'),
        ('PROCESSING', 'Processing Files'),
        ('PATTERN_RECOGNITION', 'Analyzing Patterns'),
        ('CATEGORIZATION', 'Categorizing Transactions'),
        ('VALIDATION', 'Validating Data'),
        ('COMPLETED', 'Successfully Completed'),
        ('FAILED', 'Processing Failed'),
        ('PARTIALLY_COMPLETED', 'Partially Completed')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='data_ingestions')
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Ingestion Details
    session_type = models.CharField(max_length=25, choices=SESSION_TYPES)
    session_name = models.CharField(max_length=200, help_text="User-defined name for this ingestion session")
    ingestion_status = models.CharField(max_length=25, choices=INGESTION_STATUS, default='INITIATED')
    
    # File Processing Summary
    total_files_uploaded = models.IntegerField(default=0)
    files_processed_successfully = models.IntegerField(default=0)
    files_failed = models.IntegerField(default=0)
    
    # Transaction Processing Summary
    total_transactions_extracted = models.IntegerField(default=0)
    transactions_categorized = models.IntegerField(default=0)
    transactions_with_patterns = models.IntegerField(default=0)
    duplicate_transactions_found = models.IntegerField(default=0)
    
    # AI Processing Metrics
    ai_processing_time_seconds = models.FloatField(null=True, blank=True)
    pattern_recognition_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        null=True, blank=True
    )
    
    # Status and Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processing_notes = models.TextField(blank=True, help_text="System notes about processing")
    
    # User Settings
    auto_categorize = models.BooleanField(default=True, help_text="Automatically categorize transactions using AI")
    merge_duplicates = models.BooleanField(default=True, help_text="Automatically merge duplicate transactions")
    create_patterns = models.BooleanField(default=True, help_text="Create recurring transaction patterns")

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.session_name} ({self.session_type}) - {self.ingestion_status}"
    
    @property
    def success_rate(self):
        if self.total_files_uploaded == 0:
            return 0
        return (self.files_processed_successfully / self.total_files_uploaded) * 100

class IngestionFileUpload(models.Model):
    """Individual files uploaded during an ingestion session"""
    FILE_FORMATS = [
        ('PDF', 'PDF Document'),
        ('CSV', 'CSV File'),
        ('XLSX', 'Excel File'),
        ('XLS', 'Excel File (Legacy)'),
        ('TXT', 'Text File'),
        ('JSON', 'JSON File'),
        ('XML', 'XML File')
    ]
    
    PROCESSING_STATUS = [
        ('QUEUED', 'Queued for Processing'),
        ('PROCESSING', 'Currently Processing'),
        ('PARSING', 'Parsing File Content'),
        ('EXTRACTING', 'Extracting Transactions'),
        ('VALIDATING', 'Validating Data'),
        ('COMPLETED', 'Successfully Processed'),
        ('FAILED', 'Processing Failed'),
        ('SKIPPED', 'Skipped due to Error')
    ]

    ingestion_session = models.ForeignKey(FinancialDataIngestion, on_delete=models.CASCADE, related_name='uploaded_files')
    
    # File Information
    original_filename = models.CharField(max_length=255)
    file_format = models.CharField(max_length=10, choices=FILE_FORMATS)
    file_size_bytes = models.BigIntegerField()
    file_path = models.FileField(upload_to='financial_data/%Y/%m/%d/')
    
    # File Processing
    processing_status = models.CharField(max_length=15, choices=PROCESSING_STATUS, default='QUEUED')
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error_message = models.TextField(blank=True)
    
    # Extraction Results
    transactions_extracted = models.IntegerField(default=0)
    date_range_start = models.DateField(null=True, blank=True, help_text="Earliest transaction date found")
    date_range_end = models.DateField(null=True, blank=True, help_text="Latest transaction date found")
    
    # File Content Analysis
    bank_name_detected = models.CharField(max_length=100, blank=True)
    account_number_detected = models.CharField(max_length=20, blank=True)
    file_format_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        null=True, blank=True
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} - {self.processing_status} ({self.transactions_extracted} transactions)"
    
    @property
    def processing_duration_seconds(self):
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None

class ExtractedTransaction(models.Model):
    """Transactions extracted from uploaded files before final processing"""
    EXTRACTION_STATUS = [
        ('RAW', 'Raw Extracted Data'),
        ('CLEANED', 'Data Cleaned'),
        ('CATEGORIZED', 'AI Categorized'),
        ('VALIDATED', 'User Validated'),
        ('REJECTED', 'Rejected by User'),
        ('DUPLICATE', 'Identified as Duplicate'),
        ('MERGED', 'Merged with Existing')
    ]

    file_upload = models.ForeignKey(IngestionFileUpload, on_delete=models.CASCADE, related_name='extracted_transactions')
    ingestion_session = models.ForeignKey(FinancialDataIngestion, on_delete=models.CASCADE, related_name='extracted_transactions')
    
    # Raw Extracted Data
    raw_transaction_text = models.TextField(help_text="Original text from which transaction was extracted")
    extracted_date = models.DateField()
    extracted_amount = models.DecimalField(max_digits=12, decimal_places=2)
    extracted_description = models.TextField()
    
    # AI Processing Results
    ai_predicted_category = models.CharField(max_length=50, blank=True)
    ai_predicted_subcategory = models.CharField(max_length=50, blank=True)
    ai_confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        null=True, blank=True
    )
    
    # Pattern Recognition Results
    is_recurring_transaction = models.BooleanField(default=False)
    recurring_pattern_id = models.CharField(max_length=100, blank=True)
    pattern_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        null=True, blank=True
    )
    
    # Data Quality Metrics
    extraction_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Confidence in extraction accuracy"
    )
    requires_manual_review = models.BooleanField(default=False)
    data_quality_issues = models.TextField(blank=True, help_text="Any issues found during extraction")
    
    # Processing Status
    extraction_status = models.CharField(max_length=15, choices=EXTRACTION_STATUS, default='RAW')
    is_duplicate_of = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Reference to the original transaction if this is a duplicate"
    )
    
    # Final Mapping
    final_transaction = models.ForeignKey(
        FinancialTransaction, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Reference to the final processed transaction"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-extracted_date', '-created_at']

    def __str__(self):
        return f"{self.extracted_date} - ₹{self.extracted_amount} - {self.extracted_description[:50]}"

class TransactionPattern(models.Model):
    """Detected recurring transaction patterns"""
    PATTERN_TYPES = [
        ('MONTHLY_EMI', 'Monthly EMI Payment'),
        ('MONTHLY_SIP', 'Monthly SIP Investment'),
        ('MONTHLY_RENT', 'Monthly Rent Payment'),
        ('MONTHLY_INSURANCE', 'Monthly Insurance Premium'),
        ('MONTHLY_SUBSCRIPTION', 'Monthly Subscription'),
        ('QUARTERLY_PAYMENT', 'Quarterly Payment'),
        ('ANNUAL_PAYMENT', 'Annual Payment'),
        ('WEEKLY_PAYMENT', 'Weekly Payment'),
        ('CUSTOM_RECURRING', 'Custom Recurring Pattern')
    ]
    
    PATTERN_STATUS = [
        ('DETECTED', 'Pattern Detected'),
        ('CONFIRMED', 'User Confirmed'),
        ('REJECTED', 'User Rejected'),
        ('MONITORING', 'Under Monitoring'),
        ('ARCHIVED', 'Archived Pattern')
    ]

    ingestion_session = models.ForeignKey(FinancialDataIngestion, on_delete=models.CASCADE, related_name='detected_patterns')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transaction_patterns')
    
    # Pattern Identification
    pattern_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    pattern_type = models.CharField(max_length=25, choices=PATTERN_TYPES)
    pattern_name = models.CharField(max_length=200, help_text="Human-readable pattern name")
    pattern_description = models.TextField()
    
    # Pattern Characteristics
    base_description_pattern = models.TextField(help_text="Base description pattern for matching")
    amount_range_min = models.DecimalField(max_digits=12, decimal_places=2)
    amount_range_max = models.DecimalField(max_digits=12, decimal_places=2)
    frequency_days = models.IntegerField(help_text="Average frequency in days")
    
    # Pattern Statistics
    total_occurrences = models.IntegerField(default=0)
    first_occurrence_date = models.DateField()
    last_occurrence_date = models.DateField()
    next_predicted_date = models.DateField(null=True, blank=True)
    
    # Pattern Quality
    pattern_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Confidence in pattern accuracy"
    )
    consistency_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="How consistent the pattern is"
    )
    
    # User Interaction
    pattern_status = models.CharField(max_length=15, choices=PATTERN_STATUS, default='DETECTED')
    user_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Whether to continue monitoring this pattern")
    
    # Notifications
    send_notifications = models.BooleanField(default=True, help_text="Send notifications for this pattern")
    notification_days_before = models.IntegerField(default=3, help_text="Days before predicted date to send notification")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pattern_confidence', '-total_occurrences']

    def __str__(self):
        return f"{self.user.username} - {self.pattern_name} ({self.total_occurrences} occurrences)"
    
    @property
    def average_amount(self):
        return (self.amount_range_min + self.amount_range_max) / 2

class PatternTransaction(models.Model):
    """Link between detected patterns and their associated transactions"""
    pattern = models.ForeignKey(TransactionPattern, on_delete=models.CASCADE, related_name='transactions')
    extracted_transaction = models.ForeignKey(ExtractedTransaction, on_delete=models.CASCADE, related_name='patterns')
    
    # Match Quality
    match_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Confidence that this transaction belongs to the pattern"
    )
    is_anomaly = models.BooleanField(default=False, help_text="Transaction deviates significantly from pattern")
    anomaly_reason = models.CharField(max_length=200, blank=True)
    
    # Pattern Contribution
    contributes_to_pattern = models.BooleanField(default=True, help_text="Whether this transaction strengthens the pattern")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['pattern', 'extracted_transaction']

    def __str__(self):
        return f"{self.pattern.pattern_name} - {self.extracted_transaction.extracted_date}"

class IngestionUserPreferences(models.Model):
    """User preferences for financial data ingestion"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ingestion_preferences')
    
    # Processing Preferences
    auto_categorize_threshold = models.FloatField(
        default=0.8,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Minimum confidence for automatic categorization"
    )
    duplicate_detection_sensitivity = models.CharField(
        max_length=10,
        choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')],
        default='MEDIUM'
    )
    pattern_detection_enabled = models.BooleanField(default=True)
    min_pattern_occurrences = models.IntegerField(default=3, help_text="Minimum occurrences to detect a pattern")
    
    # Notification Preferences
    notify_on_completion = models.BooleanField(default=True)
    notify_on_anomalies = models.BooleanField(default=True)
    notify_on_new_patterns = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=False)
    
    # Data Retention
    keep_raw_files_days = models.IntegerField(default=90, help_text="Days to keep original uploaded files")
    keep_extraction_logs_days = models.IntegerField(default=30, help_text="Days to keep detailed extraction logs")
    
    # Privacy Settings
    allow_ai_learning = models.BooleanField(default=True, help_text="Allow anonymized data to improve AI models")
    data_sharing_consent = models.BooleanField(default=False, help_text="Consent for anonymized data sharing for research")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Ingestion Preferences"

class IngestionAuditLog(models.Model):
    """Audit log for data ingestion activities"""
    ACTION_TYPES = [
        ('FILE_UPLOADED', 'File Uploaded'),
        ('PROCESSING_STARTED', 'Processing Started'),
        ('TRANSACTION_EXTRACTED', 'Transaction Extracted'),
        ('CATEGORY_ASSIGNED', 'Category Assigned'),
        ('PATTERN_DETECTED', 'Pattern Detected'),
        ('DUPLICATE_FOUND', 'Duplicate Found'),
        ('ERROR_OCCURRED', 'Error Occurred'),
        ('USER_OVERRIDE', 'User Override'),
        ('PROCESSING_COMPLETED', 'Processing Completed')
    ]

    ingestion_session = models.ForeignKey(FinancialDataIngestion, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ingestion_audit_logs')
    
    # Audit Details
    action_type = models.CharField(max_length=25, choices=ACTION_TYPES)
    action_description = models.TextField()
    affected_object_type = models.CharField(max_length=50, blank=True)  # e.g., 'ExtractedTransaction', 'TransactionPattern'
    affected_object_id = models.CharField(max_length=100, blank=True)
    
    # Technical Details
    processing_duration_ms = models.IntegerField(null=True, blank=True)
    memory_usage_mb = models.FloatField(null=True, blank=True)
    
    # Result
    was_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"