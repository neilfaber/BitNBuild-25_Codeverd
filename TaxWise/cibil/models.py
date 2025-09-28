from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import datetime, timedelta
import json

class CIBILScore(models.Model):
    """Model to store calculated CIBIL scores and analysis"""
    
    SCORE_RANGES = [
        ('EXCELLENT', 'Excellent (750-900)'),
        ('GOOD', 'Good (650-749)'),
        ('FAIR', 'Fair (550-649)'),
        ('POOR', 'Poor (300-549)'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cibil_scores')
    
    # Calculated Score
    calculated_score = models.IntegerField(help_text="Calculated CIBIL score (300-900)")
    score_range = models.CharField(max_length=20, choices=SCORE_RANGES)
    
    # Score Components (weightages as per CIBIL methodology)
    payment_history_score = models.FloatField(help_text="Payment history component (35% weight)")
    credit_utilization_score = models.FloatField(help_text="Credit utilization component (30% weight)")
    credit_history_length_score = models.FloatField(help_text="Credit history length component (15% weight)")
    credit_mix_score = models.FloatField(help_text="Credit mix component (10% weight)")
    new_credit_score = models.FloatField(help_text="New credit inquiries component (10% weight)")
    
    # Detailed Metrics
    payment_history_percentage = models.FloatField(default=0.0, help_text="% of on-time payments")
    average_credit_utilization = models.FloatField(default=0.0, help_text="Average credit utilization %")
    credit_history_months = models.IntegerField(default=0, help_text="Length of credit history in months")
    total_credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_outstanding_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Negative Factors
    late_payments_count = models.IntegerField(default=0)
    missed_payments_count = models.IntegerField(default=0)
    overlimit_instances = models.IntegerField(default=0)
    high_utilization_months = models.IntegerField(default=0)
    
    # Analysis Results
    improvement_suggestions = models.JSONField(default=list, help_text="AI-generated improvement suggestions")
    risk_factors = models.JSONField(default=list, help_text="Identified risk factors")
    positive_factors = models.JSONField(default=list, help_text="Positive factors helping score")
    
    # Metadata
    calculation_date = models.DateTimeField(auto_now_add=True)
    data_source_period_start = models.DateField(null=True, blank=True)
    data_source_period_end = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-calculation_date']
        
    def __str__(self):
        return f"{self.user.username} - {self.calculated_score} ({self.score_range})"
    
    @property
    def score_category(self):
        if self.calculated_score >= 750:
            return "EXCELLENT"
        elif self.calculated_score >= 650:
            return "GOOD"
        elif self.calculated_score >= 550:
            return "FAIR"
        else:
            return "POOR"
    
    @property
    def improvement_potential(self):
        """Calculate potential score improvement"""
        if self.calculated_score >= 750:
            return 900 - self.calculated_score
        elif self.calculated_score >= 650:
            return 750 - self.calculated_score
        else:
            return 650 - self.calculated_score

class ScoreFactorImpact(models.Model):
    """Model to track individual factor impacts on CIBIL score"""
    
    FACTOR_TYPES = [
        ('PAYMENT_HISTORY', 'Payment History'),
        ('CREDIT_UTILIZATION', 'Credit Utilization'), 
        ('CREDIT_LENGTH', 'Credit History Length'),
        ('CREDIT_MIX', 'Credit Mix'),
        ('NEW_CREDIT', 'New Credit'),
        ('LATE_PAYMENT', 'Late Payment'),
        ('MISSED_PAYMENT', 'Missed Payment'),
        ('HIGH_UTILIZATION', 'High Utilization'),
        ('OVERLIMIT', 'Over Limit'),
        ('CREDIT_LIMIT_INCREASE', 'Credit Limit Increase'),
    ]
    
    IMPACT_LEVELS = [
        ('VERY_POSITIVE', 'Very Positive (+50 to +100)'),
        ('POSITIVE', 'Positive (+20 to +49)'),
        ('SLIGHTLY_POSITIVE', 'Slightly Positive (+5 to +19)'),
        ('NEUTRAL', 'Neutral (0)'),
        ('SLIGHTLY_NEGATIVE', 'Slightly Negative (-5 to -19)'),
        ('NEGATIVE', 'Negative (-20 to -49)'),
        ('VERY_NEGATIVE', 'Very Negative (-50 to -100)'),
    ]
    
    cibil_score = models.ForeignKey(CIBILScore, on_delete=models.CASCADE, related_name='factor_impacts')
    factor_type = models.CharField(max_length=30, choices=FACTOR_TYPES)
    factor_description = models.TextField()
    impact_level = models.CharField(max_length=20, choices=IMPACT_LEVELS)
    impact_points = models.IntegerField(help_text="Point impact on score (-100 to +100)")
    current_value = models.FloatField(null=True, blank=True, help_text="Current value of the factor")
    recommended_value = models.FloatField(null=True, blank=True, help_text="Recommended value for improvement")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-impact_points']
        
    def __str__(self):
        return f"{self.factor_type}: {self.impact_points} points"

class CreditHealthTrend(models.Model):
    """Model to track credit health trends over time"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_trends')
    
    # Monthly metrics
    month = models.IntegerField()
    year = models.IntegerField()
    
    # Key metrics for the month
    average_utilization = models.FloatField(default=0.0)
    total_spending = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    outstanding_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Payment behavior
    on_time_payments = models.IntegerField(default=0)
    late_payments = models.IntegerField(default=0)
    missed_payments = models.IntegerField(default=0)
    
    # Fees and charges
    total_fees_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_interest_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Estimated score impact
    estimated_score_change = models.IntegerField(default=0, help_text="Estimated score change for this month")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'month', 'year']
        ordering = ['-year', '-month']
        
    def __str__(self):
        return f"{self.user.username} - {self.month}/{self.year}"

class ScoreSimulation(models.Model):
    """Model to store what-if scenarios for score improvement"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='score_simulations')
    
    # Simulation parameters
    simulation_name = models.CharField(max_length=255)
    base_score = models.IntegerField(help_text="Starting score for simulation")
    
    # Proposed changes
    proposed_changes = models.JSONField(help_text="JSON of proposed changes")
    
    # Simulation results
    projected_score = models.IntegerField(help_text="Projected score after changes")
    score_improvement = models.IntegerField(help_text="Expected score improvement")
    timeframe_months = models.IntegerField(help_text="Expected timeframe for improvement")
    
    # Implementation difficulty
    implementation_difficulty = models.CharField(max_length=20, choices=[
        ('EASY', 'Easy (0-3 months)'),
        ('MODERATE', 'Moderate (3-6 months)'),
        ('DIFFICULT', 'Difficult (6-12 months)'),
        ('VERY_DIFFICULT', 'Very Difficult (12+ months)'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-score_improvement', '-created_at']
        
    def __str__(self):
        return f"{self.simulation_name}: +{self.score_improvement} points"
