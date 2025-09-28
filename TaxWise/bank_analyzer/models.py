# analyzer/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal

class UploadedDocument(models.Model):
    file = models.FileField(upload_to='uploads/')
    filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    raw_response = models.TextField(blank=True, null=True)      # raw text response from Gemini
    analysis_json = models.JSONField(blank=True, null=True)     # stored parsed JSON if Gemini returns JSON

    def __str__(self):
        return self.filename or f"Upload {self.pk}"

class UploadedPDF(models.Model):
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_pdfs', null=True, blank=True)
    analysis_result = models.JSONField(blank=True, null=True)  # Store the analysis result

    def __str__(self):
        return f"PDF {self.id} - {self.file.name}"

class BankTransaction(models.Model):
    """Model to store individual bank transactions with debit/credit classification"""
    
    TRANSACTION_TYPES = [
        ('DEBIT', 'Debit'),
        ('CREDIT', 'Credit'),
    ]
    
    CATEGORY_CHOICES = [
        ('RECURRING_INCOME', 'Recurring Income'),
        ('EMI', 'EMI/Loan'),
        ('SIP', 'SIP/Investment'),
        ('RENT', 'Rent/Utilities'),
        ('INSURANCE', 'Insurance'),
        ('FOOD', 'Food & Dining'),
        ('TRANSPORT', 'Transport'),
        ('SHOPPING', 'Shopping'),
        ('ENTERTAINMENT', 'Entertainment'),
        ('HEALTHCARE', 'Healthcare'),
        ('EDUCATION', 'Education'),
        ('MISCELLANEOUS', 'Miscellaneous'),
    ]
    
    # Basic transaction info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_transactions')
    uploaded_pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    
    # Transaction details
    transaction_date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    
    # Categorization
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='MISCELLANEOUS')
    ai_confidence = models.FloatField(default=0.0, help_text="AI confidence score for categorization (0-1)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Analysis flags
    is_recurring = models.BooleanField(default=False, help_text="Whether this appears to be a recurring transaction")
    is_verified = models.BooleanField(default=False, help_text="Whether user has verified this transaction")
    
    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.transaction_date} - {self.description[:50]} - ₹{self.amount} ({self.transaction_type})"
    
    @property
    def is_debit(self):
        """Check if transaction is a debit"""
        return self.transaction_type == 'DEBIT'
    
    @property
    def is_credit(self):
        """Check if transaction is a credit"""
        return self.transaction_type == 'CREDIT'

class TransactionSummary(models.Model):
    """Model to store monthly/yearly transaction summaries for quick analytics"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transaction_summaries')
    uploaded_pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE, related_name='summaries', null=True, blank=True)
    
    # Time period
    month = models.IntegerField()
    year = models.IntegerField()
    
    # Summary statistics
    total_credits = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_debits = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # credits - debits
    
    # Transaction counts
    credit_count = models.IntegerField(default=0)
    debit_count = models.IntegerField(default=0)
    total_transactions = models.IntegerField(default=0)
    
    # Category breakdowns (stored as JSON for flexibility)
    category_breakdown = models.JSONField(default=dict, help_text="Breakdown by category")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'month', 'year', 'uploaded_pdf']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.user.username} - {self.month}/{self.year} - Net: ₹{self.net_amount}"


# ============================================
# CREDIT CARD STATEMENT MODELS
# ============================================

class CreditCardStatement(models.Model):
    """Model to store credit card statement information"""
    
    STATEMENT_TYPES = [
        ('MONTHLY', 'Monthly Statement'),
        ('ANNUAL', 'Annual Statement'),
    ]
    
    # Basic info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_card_statements')
    uploaded_pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE, related_name='credit_card_statement', null=True, blank=True)
    
    # Card and Account Info
    card_number_last_four = models.CharField(max_length=4, blank=True, help_text="Last 4 digits of card number")
    cardholder_name = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(max_length=255, blank=True)
    card_type = models.CharField(max_length=100, blank=True, help_text="e.g., Visa, Mastercard, Rupay")
    
    # Statement Period
    statement_date = models.DateField(null=True, blank=True)
    billing_period_start = models.DateField(null=True, blank=True)
    billing_period_end = models.DateField(null=True, blank=True)
    payment_due_date = models.DateField(null=True, blank=True)
    
    # Account Summary
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statement_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    minimum_amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Credit Limit Information
    total_credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    available_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_utilization_percentage = models.FloatField(default=0.0, help_text="Percentage of credit limit used")
    
    # Summary Statistics
    total_purchases = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_interest = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_credits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Reward Information
    reward_points_earned = models.IntegerField(default=0)
    reward_points_redeemed = models.IntegerField(default=0)
    cashback_earned = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Processing Info
    raw_analysis_result = models.JSONField(blank=True, null=True, help_text="Raw AI analysis result")
    processing_status = models.CharField(max_length=20, default='PROCESSED')
    ai_confidence_score = models.FloatField(default=0.0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-statement_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'statement_date']),
            models.Index(fields=['user', 'card_number_last_four']),
        ]
    
    def __str__(self):
        card_info = f"****{self.card_number_last_four}" if self.card_number_last_four else "Credit Card"
        return f"{self.user.username} - {card_info} - {self.statement_date} - ₹{self.statement_balance}"
    
    @property
    def credit_utilization(self):
        """Calculate credit utilization percentage"""
        if self.total_credit_limit > 0:
            return (float(self.current_balance) / float(self.total_credit_limit)) * 100
        return 0.0

class CreditCardTransaction(models.Model):
    """Model to store individual credit card transactions"""
    
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase'),
        ('PAYMENT', 'Payment'),
        ('CREDIT', 'Credit/Refund'),
        ('FEE', 'Fee'),
        ('INTEREST', 'Interest Charge'),
        ('CASH_ADVANCE', 'Cash Advance'),
        ('BALANCE_TRANSFER', 'Balance Transfer'),
    ]
    
    CATEGORY_CHOICES = [
        ('DINING', 'Dining & Restaurants'),
        ('SHOPPING', 'Shopping & Retail'),
        ('GROCERY', 'Grocery & Supermarket'),
        ('FUEL', 'Fuel & Gas'),
        ('TRANSPORT', 'Transport & Travel'),
        ('ENTERTAINMENT', 'Entertainment'),
        ('HEALTHCARE', 'Healthcare & Medical'),
        ('UTILITIES', 'Utilities & Bills'),
        ('EDUCATION', 'Education'),
        ('ONLINE', 'Online Services'),
        ('ATM', 'ATM & Cash'),
        ('TRANSFER', 'Transfer & Banking'),
        ('INSURANCE', 'Insurance'),
        ('INVESTMENT', 'Investment'),
        ('MISCELLANEOUS', 'Miscellaneous'),
    ]
    
    # Basic transaction info
    statement = models.ForeignKey(CreditCardStatement, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_card_transactions')
    
    # Transaction details
    transaction_date = models.DateField()
    posting_date = models.DateField(null=True, blank=True, help_text="Date when transaction was posted")
    description = models.TextField()
    merchant_name = models.CharField(max_length=255, blank=True)
    merchant_category = models.CharField(max_length=100, blank=True)
    
    # Amount information
    transaction_amount = models.DecimalField(max_digits=12, decimal_places=2)
    billing_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    # Categorization
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='MISCELLANEOUS')
    ai_predicted_category = models.CharField(max_length=20, blank=True)
    ai_confidence_score = models.FloatField(default=0.0)
    
    # Transaction specific info
    reference_number = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=3, default='INR')
    foreign_currency_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    exchange_rate = models.FloatField(null=True, blank=True)
    
    # Reward information
    reward_points_earned = models.IntegerField(default=0)
    cashback_earned = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    reward_rate = models.FloatField(default=0.0, help_text="Reward rate for this transaction")
    
    # Flags and metadata
    is_disputed = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=False)
    is_international = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_date']),
            models.Index(fields=['statement', 'transaction_type']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.transaction_date} - {self.description[:50]} - ₹{self.transaction_amount} ({self.transaction_type})"
    
    @property
    def is_debit_transaction(self):
        """Check if this is a debit to the account (purchase, fee, interest)"""
        return self.transaction_type in ['PURCHASE', 'FEE', 'INTEREST', 'CASH_ADVANCE']
    
    @property
    def is_credit_transaction(self):
        """Check if this is a credit to the account (payment, refund)"""
        return self.transaction_type in ['PAYMENT', 'CREDIT']

class CreditCardFee(models.Model):
    """Model to store credit card fees and charges"""
    
    FEE_TYPES = [
        ('LATE_PAYMENT', 'Late Payment Fee'),
        ('OVERLIMIT', 'Over Limit Fee'),
        ('ANNUAL', 'Annual Fee'),
        ('CASH_ADVANCE', 'Cash Advance Fee'),
        ('FOREIGN_TRANSACTION', 'Foreign Transaction Fee'),
        ('BALANCE_TRANSFER', 'Balance Transfer Fee'),
        ('RETURNED_PAYMENT', 'Returned Payment Fee'),
        ('SERVICE', 'Service Charge'),
        ('GST', 'GST on Fees'),
        ('OTHER', 'Other Fee'),
    ]
    
    statement = models.ForeignKey(CreditCardStatement, on_delete=models.CASCADE, related_name='fees')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_card_fees')
    
    fee_type = models.CharField(max_length=30, choices=FEE_TYPES)
    fee_description = models.CharField(max_length=255)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    fee_date = models.DateField()
    
    # Additional fee details
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount on which fee is calculated")
    fee_rate = models.FloatField(null=True, blank=True, help_text="Percentage rate if applicable")
    is_reversed = models.BooleanField(default=False, help_text="Whether fee was reversed/waived")
    reversal_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fee_date']
    
    def __str__(self):
        return f"{self.fee_type} - ₹{self.fee_amount} - {self.fee_date}"

class CreditCardInterest(models.Model):
    """Model to store credit card interest charges"""
    
    INTEREST_TYPES = [
        ('PURCHASE', 'Purchase Interest'),
        ('CASH_ADVANCE', 'Cash Advance Interest'),
        ('BALANCE_TRANSFER', 'Balance Transfer Interest'),
        ('PROMOTIONAL', 'Promotional Rate Interest'),
    ]
    
    statement = models.ForeignKey(CreditCardStatement, on_delete=models.CASCADE, related_name='interest_charges')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_card_interest')
    
    interest_type = models.CharField(max_length=20, choices=INTEREST_TYPES)
    interest_description = models.CharField(max_length=255)
    interest_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_date = models.DateField()
    
    # Interest calculation details
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    annual_percentage_rate = models.FloatField(null=True, blank=True, help_text="APR applied")
    daily_rate = models.FloatField(null=True, blank=True)
    number_of_days = models.IntegerField(null=True, blank=True)
    
    # Period information
    billing_period_start = models.DateField(null=True, blank=True)
    billing_period_end = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-interest_date']
    
    def __str__(self):
        return f"{self.interest_type} - ₹{self.interest_amount} - {self.interest_date}"

class CreditCardReward(models.Model):
    """Model to store credit card reward information"""
    
    REWARD_TYPES = [
        ('POINTS', 'Reward Points'),
        ('CASHBACK', 'Cashback'),
        ('MILES', 'Air Miles'),
        ('FUEL_POINTS', 'Fuel Points'),
    ]
    
    statement = models.ForeignKey(CreditCardStatement, on_delete=models.CASCADE, related_name='rewards')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_card_rewards')
    transaction = models.ForeignKey(CreditCardTransaction, on_delete=models.CASCADE, related_name='rewards', null=True, blank=True)
    
    reward_type = models.CharField(max_length=15, choices=REWARD_TYPES)
    reward_description = models.CharField(max_length=255)
    reward_date = models.DateField()
    
    # Reward amounts
    points_earned = models.IntegerField(default=0)
    cashback_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    reward_rate = models.FloatField(default=0.0, help_text="Rate at which reward was earned")
    
    # Expiry and redemption
    expiry_date = models.DateField(null=True, blank=True)
    is_redeemed = models.BooleanField(default=False)
    redemption_date = models.DateField(null=True, blank=True)
    redemption_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-reward_date']
    
    def __str__(self):
        if self.reward_type == 'POINTS':
            return f"{self.points_earned} points - {self.reward_date}"
        else:
            return f"₹{self.cashback_amount} cashback - {self.reward_date}"