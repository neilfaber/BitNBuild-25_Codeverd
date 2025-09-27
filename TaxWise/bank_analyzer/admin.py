# analyzer/admin.py
from django.contrib import admin
from .models import UploadedDocument, UploadedPDF, BankTransaction, TransactionSummary

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
