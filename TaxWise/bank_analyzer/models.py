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