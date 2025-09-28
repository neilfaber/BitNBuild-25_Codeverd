from django.contrib import admin
from .models import CIBILScore, ScoreFactorImpact, CreditHealthTrend, ScoreSimulation

@admin.register(CIBILScore)
class CIBILScoreAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'calculated_score', 'score_range', 'calculation_date',
        'payment_history_percentage', 'average_credit_utilization', 'late_payments_count'
    ]
    list_filter = ['score_range', 'calculation_date']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['calculation_date']
    ordering = ['-calculation_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'calculated_score', 'score_range', 'calculation_date')
        }),
        ('Component Scores', {
            'fields': (
                'payment_history_score', 'credit_utilization_score',
                'credit_history_length_score', 'credit_mix_score', 'new_credit_score'
            )
        }),
        ('Detailed Metrics', {
            'fields': (
                'payment_history_percentage', 'average_credit_utilization',
                'credit_history_months', 'total_credit_limit',
                'total_outstanding_balance', 'late_payments_count'
            )
        }),
        ('AI Insights', {
            'fields': ('improvement_suggestions', 'positive_factors', 'risk_factors'),
            'classes': ('collapse',)
        }),
        ('Data Source', {
            'fields': ('data_source_period_start', 'data_source_period_end'),
            'classes': ('collapse',)
        })
    )

@admin.register(ScoreFactorImpact)
class ScoreFactorImpactAdmin(admin.ModelAdmin):
    list_display = ['cibil_score', 'factor_type', 'impact_level', 'impact_points']
    list_filter = ['factor_type', 'impact_level']
    search_fields = ['cibil_score__user__username', 'factor_description']
    ordering = ['-impact_points']

@admin.register(CreditHealthTrend)
class CreditHealthTrendAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'year', 'month', 'average_utilization', 
        'on_time_payments', 'late_payments', 'estimated_score_change'
    ]
    list_filter = ['year', 'month']
    search_fields = ['user__username']
    ordering = ['-year', '-month']

@admin.register(ScoreSimulation)
class ScoreSimulationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'simulation_name', 'base_score', 'projected_score',
        'score_improvement', 'timeframe_months', 'created_at'
    ]
    list_filter = ['implementation_difficulty', 'created_at']
    search_fields = ['user__username', 'simulation_name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
