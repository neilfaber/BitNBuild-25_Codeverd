# cibil/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import json

class CibilProfile(models.Model):
    """
    Main profile model for storing user's CIBIL information
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='cibil_profile'
    )
    current_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)],
        null=True, 
        blank=True,
        help_text="Current CIBIL score (300-900)"
    )
    score_updated_at = models.DateTimeField(null=True, blank=True)
    
    # Personal Information
    pan_number = models.CharField(
        max_length=10, 
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
                message='Enter a valid PAN number (e.g., ABCDE1234F)'
            )
        ]
    )
    date_of_birth = models.DateField()
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+91[6-9]\d{9}$',
                message='Enter a valid Indian mobile number'
            )
        ]
    )
    
    # Score tracking
    target_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)],
        null=True,
        blank=True,
        help_text="Target CIBIL score to achieve"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'cibil_profile'
        verbose_name = 'CIBIL Profile'
        verbose_name_plural = 'CIBIL Profiles'

    def __str__(self):
        return f"{self.user.username} - CIBIL Profile (Score: {self.current_score or 'N/A'})"

    @property
    def age(self):
        """Calculate age from date of birth"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def score_category(self):
        """Return score category based on current score"""
        if not self.current_score:
            return "No Score"
        elif self.current_score >= 750:
            return "Excellent"
        elif self.current_score >= 700:
            return "Good"
        elif self.current_score >= 650:
            return "Fair"
        elif self.current_score >= 600:
            return "Poor"
        else:
            return "Very Poor"

    def update_score(self, new_score, factors_affecting=None):
        """Update current score and create history entry"""
        if factors_affecting is None:
            factors_affecting = {}
        
        # Create history entry
        CibilScoreHistory.objects.create(
            cibil_profile=self,
            score=new_score,
            score_date=timezone.now().date(),
            factors_affecting=factors_affecting
        )
        
        # Update current score
        self.current_score = new_score
        self.score_updated_at = timezone.now()
        self.save()

class CreditAccount(models.Model):
    """
    Model for storing credit accounts (loans, credit cards, etc.)
    """
    ACCOUNT_TYPES = [
        ('CREDIT_CARD', 'Credit Card'),
        ('PERSONAL_LOAN', 'Personal Loan'),
        ('HOME_LOAN', 'Home Loan'),
        ('AUTO_LOAN', 'Auto Loan'),
        ('EDUCATION_LOAN', 'Education Loan'),
        ('BUSINESS_LOAN', 'Business Loan'),
        ('GOLD_LOAN', 'Gold Loan'),
        ('OVERDRAFT', 'Overdraft'),
        ('OTHER', 'Other'),
    ]
    
    ACCOUNT_STATUS = [
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('WRITTEN_OFF', 'Written Off'),
        ('SETTLED', 'Settled'),
        ('RESTRUCTURED', 'Restructured'),
    ]
    
    cibil_profile = models.ForeignKey(
        CibilProfile, 
        on_delete=models.CASCADE, 
        related_name='credit_accounts'
    )
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)  # Masked for security
    
    # Financial Information
    credit_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Credit limit (for revolving accounts like credit cards)"
    )
    current_balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Current outstanding balance"
    )
    original_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Original loan amount (for term loans)"
    )
    monthly_installment = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Monthly EMI/installment amount"
    )
    
    # Account Dates
    account_opened_date = models.DateField()
    account_closed_date = models.DateField(null=True, blank=True)
    last_payment_date = models.DateField(null=True, blank=True)
    
    # Status
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS, default='ACTIVE')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cibil_credit_account'
        verbose_name = 'Credit Account'
        verbose_name_plural = 'Credit Accounts'
        unique_together = ['cibil_profile', 'bank_name', 'account_number']

    def __str__(self):
        return f"{self.bank_name} - {self.get_account_type_display()} (****{self.account_number[-4:]})"

    @property
    def credit_utilization(self):
        """Calculate credit utilization percentage for revolving accounts"""
        if self.credit_limit and self.credit_limit > 0 and self.account_type in ['CREDIT_CARD', 'OVERDRAFT']:
            return min(100, (self.current_balance / self.credit_limit) * 100)
        return 0

    @property
    def account_age_months(self):
        """Calculate account age in months"""
        end_date = self.account_closed_date or date.today()
        months = (end_date.year - self.account_opened_date.year) * 12
        months += end_date.month - self.account_opened_date.month
        return max(0, months)

    @property
    def is_delinquent(self):
        """Check if account has recent delinquencies"""
        recent_payments = self.payment_history.filter(
            payment_date__gte=date.today() - timedelta(days=90)
        ).exclude(payment_status='ON_TIME')
        return recent_payments.exists()

class PaymentHistory(models.Model):
    """
    Model for tracking payment history of credit accounts
    """
    PAYMENT_STATUS = [
        ('ON_TIME', 'On Time'),
        ('30_DAYS_LATE', '30 Days Late'),
        ('60_DAYS_LATE', '60 Days Late'),
        ('90_DAYS_LATE', '90 Days Late'),
        ('120_DAYS_LATE', '120+ Days Late'),
        ('MISSED', 'Missed Payment'),
        ('PARTIAL', 'Partial Payment'),
    ]
    
    credit_account = models.ForeignKey(
        CreditAccount, 
        on_delete=models.CASCADE, 
        related_name='payment_history'
    )
    payment_date = models.DateField()
    due_date = models.DateField()
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS)
    
    # Additional information
    late_fee_charged = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0,
        help_text="Late fee charged for delayed payment"
    )
    interest_charged = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0,
        help_text="Interest charged on outstanding amount"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cibil_payment_history'
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment Histories'
        ordering = ['-payment_date']
        unique_together = ['credit_account', 'due_date']

    def __str__(self):
        return f"{self.credit_account} - {self.payment_date} - {self.get_payment_status_display()}"

    @property
    def days_late(self):
        """Calculate number of days payment was late"""
        if self.payment_status == 'ON_TIME':
            return 0
        elif self.payment_status == '30_DAYS_LATE':
            return 30
        elif self.payment_status == '60_DAYS_LATE':
            return 60
        elif self.payment_status == '90_DAYS_LATE':
            return 90
        elif self.payment_status == '120_DAYS_LATE':
            return 120
        return 0

    @property
    def payment_percentage(self):
        """Calculate what percentage of due amount was paid"""
        if self.due_amount > 0:
            return min(100, (self.paid_amount / self.due_amount) * 100)
        return 0

class CibilScoreHistory(models.Model):
    """
    Model for tracking CIBIL score changes over time
    """
    cibil_profile = models.ForeignKey(
        CibilProfile, 
        on_delete=models.CASCADE, 
        related_name='score_history'
    )
    score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)]
    )
    score_date = models.DateField()
    
    # Factors that affected the score
    factors_affecting = models.JSONField(
        default=dict,
        help_text="JSON object containing factors that affected the score change"
    )
    
    # Score breakdown
    payment_history_score = models.IntegerField(null=True, blank=True)
    credit_utilization_score = models.IntegerField(null=True, blank=True)
    credit_history_length_score = models.IntegerField(null=True, blank=True)
    credit_mix_score = models.IntegerField(null=True, blank=True)
    new_credit_score = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cibil_score_history'
        verbose_name = 'CIBIL Score History'
        verbose_name_plural = 'CIBIL Score Histories'
        ordering = ['-score_date']
        unique_together = ['cibil_profile', 'score_date']

    def __str__(self):
        return f"{self.cibil_profile.user.username} - {self.score} - {self.score_date}"

    @property
    def score_change(self):
        """Calculate score change from previous entry"""
        previous_score = CibilScoreHistory.objects.filter(
            cibil_profile=self.cibil_profile,
            score_date__lt=self.score_date
        ).order_by('-score_date').first()
        
        if previous_score:
            return self.score - previous_score.score
        return 0

class CibilRecommendation(models.Model):
    """
    Model for storing personalized recommendations to improve CIBIL score
    """
    PRIORITY_LEVELS = [
        ('HIGH', 'High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Priority'),
    ]
    
    RECOMMENDATION_TYPES = [
        ('PAYMENT_BEHAVIOR', 'Payment Behavior'),
        ('CREDIT_UTILIZATION', 'Credit Utilization'),
        ('CREDIT_MIX', 'Credit Mix'),
        ('CREDIT_HISTORY', 'Credit History Length'),
        ('NEW_CREDIT', 'New Credit Inquiries'),
        ('ACCOUNT_MANAGEMENT', 'Account Management'),
        ('DEBT_REDUCTION', 'Debt Reduction'),
    ]
    
    cibil_profile = models.ForeignKey(
        CibilProfile, 
        on_delete=models.CASCADE, 
        related_name='recommendations'
    )
    recommendation_type = models.CharField(max_length=30, choices=RECOMMENDATION_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    action_steps = models.JSONField(
        default=list,
        help_text="List of specific action steps to implement this recommendation"
    )
    
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    potential_score_impact = models.IntegerField(
        help_text="Potential score improvement points (estimated)"
    )
    estimated_timeline = models.CharField(
        max_length=50,
        help_text="Estimated time to see impact (e.g., '3-6 months')"
    )
    
    # Status tracking
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    user_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cibil_recommendation'
        verbose_name = 'CIBIL Recommendation'
        verbose_name_plural = 'CIBIL Recommendations'
        ordering = ['priority', '-potential_score_impact', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"

    def mark_completed(self):
        """Mark recommendation as completed"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()

class WhatIfScenario(models.Model):
    """
    Model for storing what-if scenario analyses
    """
    cibil_profile = models.ForeignKey(
        CibilProfile, 
        on_delete=models.CASCADE, 
        related_name='scenarios'
    )
    scenario_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Scenario parameters
    scenario_data = models.JSONField(
        help_text="JSON object containing scenario parameters and assumptions"
    )
    
    # Results
    current_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)]
    )
    projected_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(900)]
    )
    score_improvement = models.IntegerField()
    time_to_achieve = models.IntegerField(
        help_text="Estimated months to achieve this score"
    )
    
    # Detailed breakdown
    factor_improvements = models.JSONField(
        default=dict,
        help_text="Breakdown of how each factor contributes to the improvement"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cibil_what_if_scenario'
        verbose_name = 'What-If Scenario'
        verbose_name_plural = 'What-If Scenarios'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.scenario_name} - Projected: {self.projected_score} (+{self.score_improvement})"

    def save(self, *args, **kwargs):
        # Calculate score improvement
        self.score_improvement = self.projected_score - self.current_score
        super().save(*args, **kwargs)

class CreditInquiry(models.Model):
    """
    Model for tracking credit inquiries (hard and soft)
    """
    INQUIRY_TYPES = [
        ('HARD', 'Hard Inquiry'),
        ('SOFT', 'Soft Inquiry'),
    ]
    
    INQUIRY_PURPOSES = [
        ('CREDIT_CARD', 'Credit Card Application'),
        ('PERSONAL_LOAN', 'Personal Loan'),
        ('HOME_LOAN', 'Home Loan'),
        ('AUTO_LOAN', 'Auto Loan'),
        ('BUSINESS_LOAN', 'Business Loan'),
        ('ACCOUNT_REVIEW', 'Account Review'),
        ('PRE_APPROVED', 'Pre-approved Offer'),
        ('OTHER', 'Other'),
    ]
    
    cibil_profile = models.ForeignKey(
        CibilProfile, 
        on_delete=models.CASCADE, 
        related_name='credit_inquiries'
    )
    inquiry_type = models.CharField(max_length=10, choices=INQUIRY_TYPES)
    inquiry_purpose = models.CharField(max_length=20, choices=INQUIRY_PURPOSES)
    inquiring_entity = models.CharField(max_length=100)
    inquiry_date = models.DateField()
    
    # Additional details
    inquiry_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Amount for which credit was sought"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cibil_credit_inquiry'
        verbose_name = 'Credit Inquiry'
        verbose_name_plural = 'Credit Inquiries'
        ordering = ['-inquiry_date']

    def __str__(self):
        return f"{self.inquiring_entity} - {self.get_inquiry_purpose_display()} - {self.inquiry_date}"

    @property
    def is_recent(self):
        """Check if inquiry is within last 12 months"""
        return self.inquiry_date >= date.today() - timedelta(days=365)

class AlertSettings(models.Model):
    """
    Model for managing user alert preferences
    """
    cibil_profile = models.OneToOneField(
        CibilProfile, 
        on_delete=models.CASCADE, 
        related_name='alert_settings'
    )
    
    # Email alerts
    email_score_updates = models.BooleanField(default=True)
    email_payment_reminders = models.BooleanField(default=True)
    email_recommendations = models.BooleanField(default=True)
    email_monthly_summary = models.BooleanField(default=True)
    
    # SMS alerts
    sms_score_updates = models.BooleanField(default=False)
    sms_payment_reminders = models.BooleanField(default=True)
    
    # App notifications
    app_score_updates = models.BooleanField(default=True)
    app_payment_reminders = models.BooleanField(default=True)
    app_recommendations = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cibil_alert_settings'
        verbose_name = 'Alert Settings'
        verbose_name_plural = 'Alert Settings'

    def __str__(self):
        return f"Alert Settings - {self.cibil_profile.user.username}"