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