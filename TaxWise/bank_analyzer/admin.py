# analyzer/admin.py
from django.contrib import admin
from .models import (
    UploadedDocument, UploadedPDF, BankTransaction, TransactionSummary,
    CreditCardStatement, CreditCardTransaction, CreditCardFee, 
    CreditCardInterest, CreditCardReward
)

@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'uploaded_at')
    readonly_fields = ('raw_response', 'analysis_json')

@admin.register(UploadedPDF)
class UploadedPDFAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'file', 'uploaded_at')
    list_filter = ('uploaded_at', 'user')
    readonly_fields = ('analysis_result',)
    search_fields = ('file', 'user__username', 'user__email')

@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'user', 'description', 'amount', 'transaction_type', 'category', 'ai_confidence')
    list_filter = ('transaction_type', 'category', 'user', 'transaction_date', 'is_recurring', 'is_verified')
    search_fields = ('description', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('user', 'uploaded_pdf', 'transaction_date', 'description', 'amount', 'transaction_type')
        }),
        ('Categorization', {
            'fields': ('category', 'ai_confidence')
        }),
        ('Flags', {
            'fields': ('is_recurring', 'is_verified')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(TransactionSummary)
class TransactionSummaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'month', 'year', 'total_credits', 'total_debits', 'net_amount', 'total_transactions')
    list_filter = ('year', 'month', 'user')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'category_breakdown')
    
    fieldsets = (
        ('Period', {
            'fields': ('user', 'uploaded_pdf', 'month', 'year')
        }),
        ('Summary Statistics', {
            'fields': ('total_credits', 'total_debits', 'net_amount', 'credit_count', 'debit_count', 'total_transactions')
        }),
        ('Category Breakdown', {
            'fields': ('category_breakdown',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

# Credit Card Models Admin
@admin.register(CreditCardStatement)
class CreditCardStatementAdmin(admin.ModelAdmin):
    list_display = ('user', 'bank_name', 'card_number_last_four', 'statement_date', 'current_balance', 'total_amount_due')
    list_filter = ('bank_name', 'card_type', 'statement_date', 'user')
    search_fields = ('user__username', 'user__email', 'cardholder_name', 'bank_name')
    readonly_fields = ('raw_analysis_result', 'created_at', 'updated_at', 'credit_utilization')
    date_hierarchy = 'statement_date'
    
    fieldsets = (
        ('Card Information', {
            'fields': ('user', 'uploaded_pdf', 'card_number_last_four', 'cardholder_name', 'bank_name', 'card_type')
        }),
        ('Statement Period', {
            'fields': ('statement_date', 'billing_period_start', 'billing_period_end', 'payment_due_date')
        }),
        ('Account Summary', {
            'fields': ('previous_balance', 'current_balance', 'statement_balance', 'minimum_amount_due', 'total_amount_due')
        }),
        ('Credit Limit', {
            'fields': ('total_credit_limit', 'available_credit', 'credit_utilization_percentage')
        }),
        ('Summary Statistics', {
            'fields': ('total_purchases', 'total_payments', 'total_fees', 'total_interest', 'total_credits')
        }),
        ('Rewards', {
            'fields': ('reward_points_earned', 'reward_points_redeemed', 'cashback_earned')
        }),
        ('Processing Info', {
            'fields': ('processing_status', 'ai_confidence_score', 'raw_analysis_result'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(CreditCardTransaction)
class CreditCardTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'user', 'merchant_name', 'transaction_amount', 'transaction_type', 'category')
    list_filter = ('transaction_type', 'category', 'user', 'transaction_date', 'is_international', 'is_recurring')
    search_fields = ('description', 'merchant_name', 'user__username', 'reference_number')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('statement', 'user', 'transaction_date', 'posting_date')
        }),
        ('Transaction Details', {
            'fields': ('description', 'merchant_name', 'merchant_category', 'transaction_amount', 'billing_amount', 'transaction_type')
        }),
        ('Categorization', {
            'fields': ('category', 'ai_predicted_category', 'ai_confidence_score')
        }),
        ('Additional Info', {
            'fields': ('reference_number', 'currency', 'foreign_currency_amount', 'exchange_rate')
        }),
        ('Rewards', {
            'fields': ('reward_points_earned', 'cashback_earned', 'reward_rate')
        }),
        ('Flags', {
            'fields': ('is_disputed', 'is_recurring', 'is_international', 'is_verified')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(CreditCardFee)
class CreditCardFeeAdmin(admin.ModelAdmin):
    list_display = ('fee_date', 'user', 'fee_type', 'fee_description', 'fee_amount', 'is_reversed')
    list_filter = ('fee_type', 'user', 'fee_date', 'is_reversed')
    search_fields = ('fee_description', 'user__username')
    date_hierarchy = 'fee_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('statement', 'user', 'fee_date', 'fee_type', 'fee_description', 'fee_amount')
        }),
        ('Fee Calculation', {
            'fields': ('base_amount', 'fee_rate')
        }),
        ('Reversal Info', {
            'fields': ('is_reversed', 'reversal_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(CreditCardInterest)
class CreditCardInterestAdmin(admin.ModelAdmin):
    list_display = ('interest_date', 'user', 'interest_type', 'interest_amount', 'annual_percentage_rate')
    list_filter = ('interest_type', 'user', 'interest_date')
    search_fields = ('interest_description', 'user__username')
    date_hierarchy = 'interest_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('statement', 'user', 'interest_date', 'interest_type', 'interest_description', 'interest_amount')
        }),
        ('Interest Calculation', {
            'fields': ('principal_amount', 'annual_percentage_rate', 'daily_rate', 'number_of_days')
        }),
        ('Period Information', {
            'fields': ('billing_period_start', 'billing_period_end')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(CreditCardReward)
class CreditCardRewardAdmin(admin.ModelAdmin):
    list_display = ('reward_date', 'user', 'reward_type', 'points_earned', 'cashback_amount', 'is_redeemed')
    list_filter = ('reward_type', 'user', 'reward_date', 'is_redeemed')
    search_fields = ('reward_description', 'user__username')
    date_hierarchy = 'reward_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('statement', 'user', 'transaction', 'reward_date', 'reward_type', 'reward_description')
        }),
        ('Reward Amount', {
            'fields': ('points_earned', 'cashback_amount', 'reward_rate')
        }),
        ('Expiry and Redemption', {
            'fields': ('expiry_date', 'is_redeemed', 'redemption_date', 'redemption_value')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
