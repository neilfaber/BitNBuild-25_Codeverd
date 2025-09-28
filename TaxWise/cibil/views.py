from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Avg, Count, Q, Max, Min
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
import google.generativeai as genai

from .models import CIBILScore, ScoreFactorImpact, CreditHealthTrend, ScoreSimulation
from bank_analyzer.models import CreditCardStatement, CreditCardTransaction, CreditCardFee, CreditCardInterest

# Configure Gemini API
genai.configure(api_key="AIzaSyBJIV6SFqxNLCHagY2l8QLJ1DJ_QDdR3MA")

class CIBILScoreCalculator:
    """
    Comprehensive CIBIL Score Calculator based on real credit card data
    """
    
    def __init__(self, user):
        self.user = user
        self.score_factors = []
        
    def calculate_comprehensive_score(self):
        """
        Calculate CIBIL score using weighted components:
        - Payment History: 35%
        - Credit Utilization: 30% 
        - Credit History Length: 15%
        - Credit Mix: 10%
        - New Credit: 10%
        """
        
        # Get all credit card data for the user
        statements = CreditCardStatement.objects.filter(user=self.user)
        transactions = CreditCardTransaction.objects.filter(user=self.user)
        fees = CreditCardFee.objects.filter(user=self.user)
        
        if not statements.exists():
            return None  # Return None for consistency with view logic
        
        # Calculate individual components
        payment_score, payment_metrics = self._calculate_payment_history_score(statements, transactions, fees)
        utilization_score, utilization_metrics = self._calculate_credit_utilization_score(statements)
        history_score, history_metrics = self._calculate_credit_history_length_score(statements)
        mix_score, mix_metrics = self._calculate_credit_mix_score(statements)
        new_credit_score, new_credit_metrics = self._calculate_new_credit_score(statements)
        
        # Calculate weighted final score (300-900 range)
        base_score = 300
        score_range = 600  # 900 - 300
        
        weighted_score = (
            (payment_score * 0.35) +
            (utilization_score * 0.30) +
            (history_score * 0.15) +
            (mix_score * 0.10) +
            (new_credit_score * 0.10)
        )
        
        final_score = int(base_score + (weighted_score * score_range))
        final_score = max(300, min(900, final_score))  # Clamp to valid range
        
        # Determine score range
        if final_score >= 750:
            score_range_category = 'EXCELLENT'
        elif final_score >= 650:
            score_range_category = 'GOOD'
        elif final_score >= 550:
            score_range_category = 'FAIR'
        else:
            score_range_category = 'POOR'
        
        # Combine all metrics
        all_metrics = {
            **payment_metrics,
            **utilization_metrics, 
            **history_metrics,
            **mix_metrics,
            **new_credit_metrics
        }
        
        return {
            'final_score': final_score,
            'score_range': score_range_category,
            'component_scores': {
                'payment_history': payment_score,
                'credit_utilization': utilization_score,
                'credit_history_length': history_score,
                'credit_mix': mix_score,
                'new_credit': new_credit_score
            },
            'metrics': all_metrics,
            'score_factors': self.score_factors
        }
    
    def _calculate_payment_history_score(self, statements, transactions, fees):
        """Calculate payment history score (35% weight)"""
        
        metrics = {
            'total_payments_due': 0,
            'on_time_payments': 0,
            'late_payments': 0,
            'missed_payments': 0,
            'payment_history_percentage': 0,
            'late_payment_fees': 0
        }
        
        # Count late payment fees as indicators of missed/late payments
        late_payment_fees = fees.filter(fee_type='LATE_PAYMENT').count()
        
        # Estimate payment behavior from statements
        total_statements = statements.count()
        if total_statements == 0:
            return 0.0, metrics
        
        # Analyze payment patterns
        overdue_indicators = 0
        total_fee_amount = fees.filter(fee_type='LATE_PAYMENT').aggregate(
            total=Sum('fee_amount')
        )['total'] or 0
        
        # Calculate metrics
        metrics['late_payments'] = late_payment_fees
        metrics['late_payment_fees'] = float(total_fee_amount)
        metrics['total_payments_due'] = total_statements
        metrics['on_time_payments'] = max(0, total_statements - late_payment_fees)
        
        if total_statements > 0:
            metrics['payment_history_percentage'] = (metrics['on_time_payments'] / total_statements) * 100
        
        # Score calculation (0.0 to 1.0)
        if late_payment_fees == 0:
            payment_score = 1.0  # Perfect payment history
            self.score_factors.append({
                'type': 'PAYMENT_HISTORY',
                'description': 'Perfect payment history with no late payment fees',
                'impact': 'VERY_POSITIVE',
                'points': 100
            })
        elif late_payment_fees <= 2:
            payment_score = 0.8  # Good with minor issues
            self.score_factors.append({
                'type': 'LATE_PAYMENT',
                'description': f'{late_payment_fees} late payment fees detected',
                'impact': 'NEGATIVE',
                'points': -40
            })
        else:
            payment_score = 0.4  # Poor payment history
            self.score_factors.append({
                'type': 'LATE_PAYMENT',
                'description': f'Multiple late payments ({late_payment_fees}) indicating poor payment habits',
                'impact': 'VERY_NEGATIVE',
                'points': -80
            })
        
        return payment_score, metrics
    
    def _calculate_credit_utilization_score(self, statements):
        """Calculate credit utilization score (30% weight)"""
        
        metrics = {
            'average_utilization': 0,
            'max_utilization': 0,
            'min_utilization': 0,
            'total_credit_limit': 0,
            'average_outstanding_balance': 0,
            'high_utilization_months': 0
        }
        
        if not statements.exists():
            return 0.0, metrics
        
        # Calculate utilization metrics
        utilizations = []
        total_limits = []
        total_balances = []
        high_util_count = 0
        
        for statement in statements:
            if statement.total_credit_limit > 0:
                utilization = (float(statement.current_balance) / float(statement.total_credit_limit)) * 100
                utilizations.append(utilization)
                total_limits.append(float(statement.total_credit_limit))
                total_balances.append(float(statement.current_balance))
                
                if utilization > 70:  # High utilization threshold
                    high_util_count += 1
        
        if utilizations:
            avg_utilization = sum(utilizations) / len(utilizations)
            metrics['average_utilization'] = avg_utilization
            metrics['max_utilization'] = max(utilizations)
            metrics['min_utilization'] = min(utilizations)
            metrics['total_credit_limit'] = sum(total_limits) / len(total_limits)
            metrics['average_outstanding_balance'] = sum(total_balances) / len(total_balances)
            metrics['high_utilization_months'] = high_util_count
            
            # Score calculation based on utilization
            if avg_utilization <= 10:
                utilization_score = 1.0  # Excellent
                self.score_factors.append({
                    'type': 'CREDIT_UTILIZATION',
                    'description': f'Excellent credit utilization at {avg_utilization:.1f}%',
                    'impact': 'VERY_POSITIVE',
                    'points': 90
                })
            elif avg_utilization <= 30:
                utilization_score = 0.8  # Good
                self.score_factors.append({
                    'type': 'CREDIT_UTILIZATION', 
                    'description': f'Good credit utilization at {avg_utilization:.1f}%',
                    'impact': 'POSITIVE',
                    'points': 40
                })
            elif avg_utilization <= 50:
                utilization_score = 0.6  # Fair
                self.score_factors.append({
                    'type': 'HIGH_UTILIZATION',
                    'description': f'Moderate credit utilization at {avg_utilization:.1f}%',
                    'impact': 'SLIGHTLY_NEGATIVE',
                    'points': -10
                })
            elif avg_utilization <= 70:
                utilization_score = 0.4  # Poor
                self.score_factors.append({
                    'type': 'HIGH_UTILIZATION',
                    'description': f'High credit utilization at {avg_utilization:.1f}%',
                    'impact': 'NEGATIVE',
                    'points': -30
                })
            else:
                utilization_score = 0.2  # Very Poor
                self.score_factors.append({
                    'type': 'HIGH_UTILIZATION',
                    'description': f'Very high credit utilization at {avg_utilization:.1f}%',
                    'impact': 'VERY_NEGATIVE',
                    'points': -60
                })
        else:
            utilization_score = 0.5  # Neutral if no data
        
        return utilization_score, metrics
    
    def _calculate_credit_history_length_score(self, statements):
        """Calculate credit history length score (15% weight)"""
        
        metrics = {
            'credit_history_months': 0,
            'oldest_account_date': None,
            'newest_account_date': None
        }
        
        if not statements.exists():
            return 0.0, metrics
        
        # Find oldest and newest accounts
        oldest_date = statements.aggregate(oldest=Min('billing_period_start'))['oldest']
        newest_date = statements.aggregate(newest=Max('statement_date'))['newest']
        
        if oldest_date and newest_date:
            history_months = ((newest_date - oldest_date).days // 30)
            metrics['credit_history_months'] = history_months
            metrics['oldest_account_date'] = oldest_date
            metrics['newest_account_date'] = newest_date
            
            # Score based on history length
            if history_months >= 60:  # 5+ years
                history_score = 1.0
                self.score_factors.append({
                    'type': 'CREDIT_LENGTH',
                    'description': f'Excellent credit history length: {history_months} months',
                    'impact': 'POSITIVE',
                    'points': 50
                })
            elif history_months >= 36:  # 3-5 years
                history_score = 0.8
                self.score_factors.append({
                    'type': 'CREDIT_LENGTH',
                    'description': f'Good credit history length: {history_months} months', 
                    'impact': 'SLIGHTLY_POSITIVE',
                    'points': 20
                })
            elif history_months >= 12:  # 1-3 years
                history_score = 0.6
                self.score_factors.append({
                    'type': 'CREDIT_LENGTH',
                    'description': f'Fair credit history length: {history_months} months',
                    'impact': 'NEUTRAL',
                    'points': 0
                })
            else:  # Less than 1 year
                history_score = 0.3
                self.score_factors.append({
                    'type': 'CREDIT_LENGTH',
                    'description': f'Short credit history: {history_months} months',
                    'impact': 'SLIGHTLY_NEGATIVE',
                    'points': -15
                })
        else:
            history_score = 0.3
        
        return history_score, metrics
    
    def _calculate_credit_mix_score(self, statements):
        """Calculate credit mix score (10% weight)"""
        
        metrics = {
            'credit_card_accounts': 0,
            'different_banks': 0,
            'card_types': []
        }
        
        # Analyze credit card diversity
        unique_banks = set()
        card_types = set()
        
        for statement in statements:
            if statement.bank_name:
                unique_banks.add(statement.bank_name)
            if statement.card_type:
                card_types.add(statement.card_type)
        
        metrics['credit_card_accounts'] = statements.count()
        metrics['different_banks'] = len(unique_banks)
        metrics['card_types'] = list(card_types)
        
        # Score based on diversity
        mix_score = 0.7  # Base score for having credit cards
        
        if len(unique_banks) > 1:
            mix_score = 0.8
            self.score_factors.append({
                'type': 'CREDIT_MIX',
                'description': f'Good credit mix with {len(unique_banks)} different banks',
                'impact': 'SLIGHTLY_POSITIVE',
                'points': 15
            })
        
        return mix_score, metrics
    
    def _calculate_new_credit_score(self, statements):
        """Calculate new credit inquiries score (10% weight)"""
        
        metrics = {
            'recent_accounts': 0,
            'account_opening_frequency': 0
        }
        
        # Check for recently opened accounts (last 6 months)
        six_months_ago = timezone.now().date() - timedelta(days=180)
        recent_accounts = statements.filter(
            statement_date__gte=six_months_ago
        ).count()
        
        metrics['recent_accounts'] = recent_accounts
        
        # Score based on new credit activity
        if recent_accounts == 0:
            new_credit_score = 1.0
            self.score_factors.append({
                'type': 'NEW_CREDIT',
                'description': 'No recent credit applications or new accounts',
                'impact': 'POSITIVE',
                'points': 20
            })
        elif recent_accounts <= 2:
            new_credit_score = 0.8
            self.score_factors.append({
                'type': 'NEW_CREDIT',
                'description': f'{recent_accounts} recent credit accounts opened',
                'impact': 'NEUTRAL',
                'points': 0
            })
        else:
            new_credit_score = 0.6
            self.score_factors.append({
                'type': 'NEW_CREDIT',
                'description': f'Multiple recent credit accounts ({recent_accounts}) may indicate credit hunger',
                'impact': 'SLIGHTLY_NEGATIVE',
                'points': -10
            })
        
        return new_credit_score, metrics

def generate_ai_insights(score_data, user):
    """Generate AI-powered insights using Gemini"""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        prompt = f"""
        As a financial advisor specializing in credit scores, analyze this CIBIL score data and provide insights:
        
        User's CIBIL Score: {score_data['final_score']} ({score_data['score_range']})
        
        Component Scores:
        - Payment History: {score_data['component_scores']['payment_history']:.1%}
        - Credit Utilization: {score_data['component_scores']['credit_utilization']:.1%}
        - Credit History Length: {score_data['component_scores']['credit_history_length']:.1%}
        - Credit Mix: {score_data['component_scores']['credit_mix']:.1%}
        - New Credit: {score_data['component_scores']['new_credit']:.1%}
        
        Key Metrics:
        - Average Credit Utilization: {score_data['metrics'].get('average_utilization', 0):.1f}%
        - Payment History: {score_data['metrics'].get('payment_history_percentage', 0):.1f}%
        - Credit History: {score_data['metrics'].get('credit_history_months', 0)} months
        - Late Payments: {score_data['metrics'].get('late_payments', 0)}
        
        Provide:
        1. 3-5 specific improvement suggestions with expected score impact
        2. 3-5 positive factors that are helping the score
        3. 3-5 risk factors that are hurting the score
        4. Timeline for potential improvements
        
        Format as JSON with keys: improvement_suggestions, positive_factors, risk_factors, timeline_analysis
        Each suggestion should have: description, impact_points, timeframe, difficulty
        """
        
        response = model.generate_content(prompt)
        result = response.text
        
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            # Fallback manual analysis if AI fails
            return generate_fallback_insights(score_data)
            
    except Exception as e:
        print(f"Error generating AI insights: {e}")
        return generate_fallback_insights(score_data)

def generate_fallback_insights(score_data):
    """Generate insights if AI fails"""
    insights = {
        'improvement_suggestions': [],
        'positive_factors': [],
        'risk_factors': [],
        'timeline_analysis': "Improvements typically take 3-6 months to reflect in your CIBIL score."
    }
    
    # Generate suggestions based on score factors
    utilization = score_data['metrics'].get('average_utilization', 0)
    if utilization > 30:
        insights['improvement_suggestions'].append({
            'description': f'Reduce credit utilization from {utilization:.1f}% to below 30%',
            'impact_points': 50,
            'timeframe': '2-3 months',
            'difficulty': 'Moderate'
        })
    
    late_payments = score_data['metrics'].get('late_payments', 0)
    if late_payments > 0:
        insights['risk_factors'].append({
            'description': f'{late_payments} late payment(s) detected',
            'impact_points': -40,
            'recommendation': 'Set up auto-pay to avoid future late payments'
        })
    
    if score_data['final_score'] >= 750:
        insights['positive_factors'].append({
            'description': 'Excellent credit score range',
            'benefit': 'Eligible for best interest rates and premium credit products'
        })
    
    return insights


def generate_improvement_insights_from_gemini(score_data, improvement_plan, user):
    """
    Generate personalized improvement insights using Gemini AI
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Prepare detailed prompt for improvement insights
        prompt = f"""
        As a CIBIL credit score expert, analyze this user's credit profile and provide personalized improvement recommendations.

        CURRENT CREDIT PROFILE:
        - Current CIBIL Score: {score_data['score']}/900
        - Credit Utilization: {score_data['utilization']:.1f}%
        - Payment History: {score_data['payment_history']:.1f}% on-time payments
        - Credit History Length: {score_data['credit_age']} months
        - Late Payments (last 12 months): {score_data['late_payments']}
        - Total Credit Limit: ₹{score_data['credit_limit']:,.0f}

        IDENTIFIED IMPROVEMENT AREAS:
        {chr(10).join([f"- {plan['category']}: Current {plan['current']} → Target {plan['target']} (Potential +{plan['potential_boost']} points)" for plan in improvement_plan])}

        Please provide:
        1. PRIORITY ACTIONS: Top 3 most impactful actions to take immediately
        2. STRATEGIC RECOMMENDATIONS: Long-term strategies for sustained improvement
        3. TIMELINE INSIGHTS: Realistic expectations for score improvement
        4. RISK WARNINGS: What to avoid that could harm the score
        5. PERSONALIZED TIPS: Specific advice based on current credit profile
        6. MOTIVATION MESSAGE: Encouraging message about improvement potential

        Format as JSON with these keys: priority_actions, strategic_recommendations, timeline_insights, risk_warnings, personalized_tips, motivation_message

        Each array item should have: description, impact_level (HIGH/MEDIUM/LOW), timeframe, specific_steps (array)
        """

        response = model.generate_content(prompt)
        ai_text = response.text.strip()
        
        # Clean JSON response
        if ai_text.startswith('```json'):
            ai_text = ai_text[7:]
        if ai_text.endswith('```'):
            ai_text = ai_text[:-3]
        
        ai_insights = json.loads(ai_text)
        
        # Validate and structure the response
        structured_insights = {
            'priority_actions': ai_insights.get('priority_actions', []),
            'strategic_recommendations': ai_insights.get('strategic_recommendations', []),
            'timeline_insights': ai_insights.get('timeline_insights', []),
            'risk_warnings': ai_insights.get('risk_warnings', []),
            'personalized_tips': ai_insights.get('personalized_tips', []),
            'motivation_message': ai_insights.get('motivation_message', 'You have great potential to improve your CIBIL score!'),
            'ai_generated': True,
            'generation_date': timezone.now().isoformat()
        }
        
        return structured_insights
        
    except Exception as e:
        print(f"Error generating improvement insights from Gemini: {e}")
        return generate_fallback_improvement_insights(score_data, improvement_plan)


def generate_fallback_improvement_insights(score_data, improvement_plan):
    """
    Generate fallback improvement insights when Gemini AI is not available
    """
    score = score_data['score']
    utilization = score_data['utilization']
    payment_history = score_data['payment_history']
    
    # Priority actions based on score profile
    priority_actions = []
    
    if utilization > 30:
        priority_actions.append({
            'description': 'Reduce credit utilization below 30%',
            'impact_level': 'HIGH',
            'timeframe': '1-2 months',
            'specific_steps': [
                'Pay down existing balances',
                'Make multiple payments per month',
                'Request credit limit increases'
            ]
        })
    
    if score_data['late_payments'] > 0:
        priority_actions.append({
            'description': 'Eliminate all late payments going forward',
            'impact_level': 'HIGH',
            'timeframe': 'Immediate',
            'specific_steps': [
                'Set up automatic payments',
                'Create calendar reminders',
                'Pay at least minimum amounts on time'
            ]
        })
    
    if len(priority_actions) == 0:
        priority_actions.append({
            'description': 'Maintain excellent payment discipline',
            'impact_level': 'MEDIUM',
            'timeframe': 'Ongoing',
            'specific_steps': [
                'Continue making on-time payments',
                'Keep utilization low',
                'Monitor credit report regularly'
            ]
        })
    
    # Strategic recommendations
    strategic_recommendations = [
        {
            'description': 'Build a diversified credit portfolio',
            'impact_level': 'MEDIUM',
            'timeframe': '6-12 months',
            'specific_steps': [
                'Consider different types of credit accounts',
                'Maintain a mix of credit cards and loans',
                'Keep old accounts active'
            ]
        },
        {
            'description': 'Monitor and optimize credit regularly',
            'impact_level': 'MEDIUM',
            'timeframe': 'Ongoing',
            'specific_steps': [
                'Check credit report monthly',
                'Dispute any errors immediately',
                'Track score improvements'
            ]
        }
    ]
    
    # Timeline insights
    timeline_insights = [
        {
            'description': 'Quick wins possible in 1-3 months',
            'impact_level': 'HIGH',
            'timeframe': '1-3 months',
            'specific_steps': [
                'Payment history improvements show quickly',
                'Utilization changes reflect in 1-2 billing cycles',
                'Score improvements of 20-50 points possible'
            ]
        }
    ]
    
    # Risk warnings
    risk_warnings = [
        {
            'description': 'Avoid closing old credit accounts',
            'impact_level': 'HIGH',
            'timeframe': 'Always',
            'specific_steps': [
                'Keep oldest accounts open',
                'Use old cards occasionally',
                'Only close accounts with annual fees if necessary'
            ]
        }
    ]
    
    # Personalized tips based on score range
    if score >= 750:
        motivation = "Your score is already excellent! Focus on maintaining these good habits."
        tips_focus = "maintenance"
    elif score >= 650:
        motivation = "You're in good territory! Small improvements can push you to excellent."
        tips_focus = "optimization"
    else:
        motivation = "Great potential for improvement! Focus on the basics first."
        tips_focus = "foundation"
    
    personalized_tips = [
        {
            'description': f'Score-specific advice for {tips_focus}',
            'impact_level': 'MEDIUM',
            'timeframe': 'Ongoing',
            'specific_steps': [
                f'Your {score} score has room for improvement',
                'Focus on payment history and utilization first',
                'Consider your score improvement potential'
            ]
        }
    ]
    
    return {
        'priority_actions': priority_actions,
        'strategic_recommendations': strategic_recommendations,
        'timeline_insights': timeline_insights,
        'risk_warnings': risk_warnings,
        'personalized_tips': personalized_tips,
        'motivation_message': motivation,
        'ai_generated': False,
        'generation_date': timezone.now().isoformat()
    }


def handle_import_existing_data(request):
    """Handle importing CIBIL data from existing credit card statements"""
    try:
        # Calculate score from uploaded credit card data
        calculator = CIBILScoreCalculator(request.user)
        score_result = calculator.calculate_comprehensive_score()
        
        if score_result is None:
            messages.error(request, "No credit card data found to import. Please upload statements first or use manual entry.")
            context = {
                'show_choice_screen': True,
                'has_data': False,
                'has_credit_data': False,
                'error_message': "No credit card data available for import."
            }
            return render(request, 'cibil/dashboard.html', context)
        
        # Validate score result
        if not isinstance(score_result, dict) or 'final_score' not in score_result:
            messages.error(request, "Error processing credit card data. Please try manual entry.")
            context = {
                'show_choice_screen': True,
                'has_data': False,
                'has_credit_data': True,
                'error_message': "Error calculating CIBIL score from uploaded data."
            }
            return render(request, 'cibil/dashboard.html', context)
        
        # Save score to database
        statements = CreditCardStatement.objects.filter(user=request.user)
        period_start = statements.aggregate(start=Min('billing_period_start'))['start']
        period_end = statements.aggregate(end=Max('statement_date'))['end']
        
        # Delete existing score to create fresh one
        CIBILScore.objects.filter(user=request.user).delete()
        
        score_record = CIBILScore.objects.create(
            user=request.user,
            calculated_score=score_result['final_score'],
            score_range=score_result['score_range'],
            payment_history_score=score_result['component_scores']['payment_history'],
            credit_utilization_score=score_result['component_scores']['credit_utilization'],
            credit_history_length_score=score_result['component_scores']['credit_history_length'],
            credit_mix_score=score_result['component_scores']['credit_mix'],
            new_credit_score=score_result['component_scores']['new_credit'],
            payment_history_percentage=score_result['metrics'].get('payment_history_percentage', 0),
            average_credit_utilization=score_result['metrics'].get('average_utilization', 0),
            credit_history_months=score_result['metrics'].get('credit_history_months', 0),
            total_credit_limit=Decimal(str(score_result['metrics'].get('total_credit_limit', 0))),
            total_outstanding_balance=Decimal(str(score_result['metrics'].get('average_outstanding_balance', 0))),
            late_payments_count=score_result['metrics'].get('late_payments', 0),
            data_source_period_start=period_start,
            data_source_period_end=period_end
        )
        
        # Generate AI insights
        ai_insights = generate_ai_insights(score_result, request.user)
        score_record.improvement_suggestions = ai_insights.get('improvement_suggestions', [])
        score_record.positive_factors = ai_insights.get('positive_factors', [])
        score_record.risk_factors = ai_insights.get('risk_factors', [])
        score_record.save()
        
        # Save individual factor impacts
        ScoreFactorImpact.objects.filter(cibil_score=score_record).delete()
        for factor in score_result['score_factors']:
            impact_level = 'NEUTRAL'
            points = factor.get('points', 0)
            
            if points >= 50:
                impact_level = 'VERY_POSITIVE'
            elif points >= 20:
                impact_level = 'POSITIVE' 
            elif points >= 5:
                impact_level = 'SLIGHTLY_POSITIVE'
            elif points <= -50:
                impact_level = 'VERY_NEGATIVE'
            elif points <= -20:
                impact_level = 'NEGATIVE'
            elif points <= -5:
                impact_level = 'SLIGHTLY_NEGATIVE'
            
            ScoreFactorImpact.objects.create(
                cibil_score=score_record,
                factor_type=factor['type'],
                factor_description=factor['description'],
                impact_level=impact_level,
                impact_points=points
            )
        
        messages.success(request, f"Successfully calculated CIBIL score from your credit card data! Your score is {score_record.calculated_score}")
        return render_dashboard_with_existing_score(request, score_record)
        
    except Exception as e:
        messages.error(request, f"Error importing data: {str(e)}. Please try manual entry.")
        context = {
            'show_choice_screen': True,
            'has_data': False,
            'has_credit_data': CreditCardStatement.objects.filter(user=request.user).exists(),
            'error_message': f"Error importing credit card data: {str(e)}"
        }
        return render(request, 'cibil/dashboard.html', context)


def show_manual_entry_form(request):
    """Show the manual data entry form"""
    
    # Check if user has uploaded credit card data available for alternative import option
    has_credit_data = CreditCardStatement.objects.filter(user=request.user).exists()
    
    context = {
        'show_manual_entry': True,
        'has_data': False,
        'has_credit_data': has_credit_data,
        'credit_statements_count': CreditCardStatement.objects.filter(user=request.user).count() if has_credit_data else 0,
    }
    return render(request, 'cibil/dashboard.html', context)


def handle_manual_data_entry(request):
    """Handle manual CIBIL data entry from form submission"""
    try:
        # Extract form data (removed current_score input)
        credit_limit = Decimal(str(request.POST.get('credit_limit', 0)))
        outstanding_balance = Decimal(str(request.POST.get('outstanding_balance', 0)))
        credit_history_months = int(request.POST.get('credit_history_months', 0))
        late_payments = int(request.POST.get('late_payments', 0))
        missed_payments = int(request.POST.get('missed_payments', 0))
        
        # Calculate utilization
        utilization = float((outstanding_balance / credit_limit * 100)) if credit_limit > 0 else 0
        
        # Calculate CIBIL score based on factors (simplified algorithm)
        base_score = 300
        
        # Payment history factor (35% weight) - starts at 850 and reduces for late/missed payments
        payment_score = 850 - (late_payments * 25) - (missed_payments * 50)
        payment_component = max(0, min(100, (payment_score - 300) / 6))
        
        # Credit utilization factor (30% weight) - optimal is <30%
        if utilization <= 10:
            utilization_component = 100
        elif utilization <= 30:
            utilization_component = 90 - ((utilization - 10) * 2)
        elif utilization <= 50:
            utilization_component = 50 - ((utilization - 30) * 1.5)
        else:
            utilization_component = max(0, 20 - ((utilization - 50) * 0.5))
        
        # Credit history length factor (15% weight)
        if credit_history_months >= 60:
            history_component = 100
        elif credit_history_months >= 24:
            history_component = 60 + ((credit_history_months - 24) / 36) * 40
        else:
            history_component = max(20, (credit_history_months / 24) * 60)
        
        # Credit mix and new credit (simplified - 10% each)
        mix_component = 60  # Assume average credit mix
        new_credit_component = 70  # Assume no recent inquiries
        
        # Calculate weighted score
        weighted_score = (
            (payment_component * 0.35) +
            (utilization_component * 0.30) +
            (history_component * 0.15) +
            (mix_component * 0.10) +
            (new_credit_component * 0.10)
        )
        
        # Final score calculation
        calculated_score = int(base_score + (weighted_score * 6))
        calculated_score = max(300, min(900, calculated_score))
        
        # Determine score range
        if calculated_score >= 750:
            score_range = 'EXCELLENT'
        elif calculated_score >= 650:
            score_range = 'GOOD' 
        elif calculated_score >= 550:
            score_range = 'FAIR'
        else:
            score_range = 'POOR'
        
        # Create or update score record
        score_record, created = CIBILScore.objects.get_or_create(
            user=request.user,
            defaults={
                'calculated_score': calculated_score,
                'score_range': score_range,
                'payment_history_score': payment_component / 100,
                'credit_utilization_score': utilization_component / 100,
                'credit_history_length_score': history_component / 100,
                'credit_mix_score': mix_component / 100,
                'new_credit_score': new_credit_component / 100,
                'payment_history_percentage': max(0, 100 - (late_payments * 10) - (missed_payments * 20)),
                'average_credit_utilization': utilization,
                'credit_history_months': credit_history_months,
                'total_credit_limit': credit_limit,
                'total_outstanding_balance': outstanding_balance,
                'late_payments_count': late_payments,
                'missed_payments_count': missed_payments,
            }
        )
        
        if not created:
            # Update existing record
            score_record.calculated_score = calculated_score
            score_record.score_range = score_range
            score_record.average_credit_utilization = utilization
            score_record.credit_history_months = credit_history_months
            score_record.total_credit_limit = credit_limit
            score_record.total_outstanding_balance = outstanding_balance
            score_record.late_payments_count = late_payments
            score_record.missed_payments_count = missed_payments
            score_record.payment_history_percentage = max(0, 100 - (late_payments * 10) - (missed_payments * 20))
            score_record.save()
        
        messages.success(request, f"CIBIL score calculated successfully! Your score is {calculated_score} ({score_range})")
        return render_dashboard_with_existing_score(request, score_record)
        
    except (ValueError, TypeError) as e:
        messages.error(request, f"Invalid data entered: {str(e)}")
        context = {
            'show_manual_entry': True,
            'has_data': False,
            'error_message': f"Please check your input: {str(e)}"
        }
        return render(request, 'cibil/dashboard.html', context)

def render_dashboard_with_existing_score(request, score_record):
    """Render dashboard with existing score record"""
    
    # Generate basic AI insights for manual data
    ai_insights = {
        'improvement_suggestions': score_record.improvement_suggestions or [],
        'positive_factors': score_record.positive_factors or [],
        'risk_factors': score_record.risk_factors or []
    }
    
    # Add basic suggestions based on manual data if none exist
    if not ai_insights['improvement_suggestions']:
        if score_record.average_credit_utilization > 30:
            ai_insights['risk_factors'].append("High credit utilization (>30%) negatively impacts score")
            ai_insights['improvement_suggestions'].append("Reduce credit utilization below 30% for better score")
        
        if score_record.late_payments_count > 0:
            ai_insights['risk_factors'].append(f"{score_record.late_payments_count} late payments detected")
            ai_insights['improvement_suggestions'].append("Focus on making all payments on time")
        
        if score_record.calculated_score >= 750:
            ai_insights['positive_factors'].append("Excellent credit score - maintain current habits")
        elif score_record.calculated_score >= 650:
            ai_insights['positive_factors'].append("Good credit score with room for improvement")

    # Check if user has credit data available for re-import
    has_credit_data = CreditCardStatement.objects.filter(user=request.user).exists()
    
    context = {
        'score_record': score_record,
        'has_data': True,
        'ai_insights': ai_insights,
        'is_manual_entry': True,
        'credit_statements': CreditCardStatement.objects.filter(user=request.user).order_by('-statement_date')[:5],
        'factor_impacts': ScoreFactorImpact.objects.filter(cibil_score=score_record).order_by('-impact_points'),
        'has_credit_data': has_credit_data,
        'show_recalculate_options': True,  # Show options to recalculate
    }
    
    return render(request, 'cibil/dashboard.html', context)

@login_required
def cibil_dashboard(request):
    """Main CIBIL dashboard showing current score and analysis"""
    
    # Handle manual data input
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'manual_entry':
            # Check if this is a request to show manual entry form or process form data
            if 'credit_limit' in request.POST:
                # This is form submission with data - process it
                return handle_manual_data_entry(request)
            else:
                # This is a request to show manual entry form - show the form
                return show_manual_entry_form(request)
        elif action == 'import_data':
            return handle_import_existing_data(request)
    
    # Check if user has existing CIBIL score
    existing_score = CIBILScore.objects.filter(user=request.user).first()
    
    # Check if user has uploaded credit card data available
    has_credit_data = CreditCardStatement.objects.filter(user=request.user).exists()
    
    # If user already has a calculated score, show it
    if existing_score:
        return render_dashboard_with_existing_score(request, existing_score)
    
    # Show choice screen: manual entry OR import from existing data
    context = {
        'show_choice_screen': True,
        'has_data': False,
        'has_credit_data': has_credit_data,
        'credit_statements_count': CreditCardStatement.objects.filter(user=request.user).count() if has_credit_data else 0,
        'sample_score_ranges': [
            {'range': 'EXCELLENT', 'min': 750, 'max': 900, 'color': 'success'},
            {'range': 'GOOD', 'min': 650, 'max': 749, 'color': 'info'},
            {'range': 'FAIR', 'min': 550, 'max': 649, 'color': 'warning'},
            {'range': 'POOR', 'min': 300, 'max': 549, 'color': 'danger'},
        ]
    }
    return render(request, 'cibil/dashboard.html', context)


@login_required
def score_history(request):
    """View showing CIBIL score history and trends"""
    
    score_history = CIBILScore.objects.filter(user=request.user).order_by('-calculation_date')
    credit_trends = CreditHealthTrend.objects.filter(user=request.user).order_by('-year', '-month')
    
    # Calculate score changes for easier template rendering
    score_list = list(score_history)
    for i, score in enumerate(score_list):
        if i < len(score_list) - 1:  # Not the last (oldest) record
            previous_score = score_list[i + 1]
            score.change_from_previous = score.calculated_score - previous_score.calculated_score
        else:
            score.change_from_previous = None
    
    context = {
        'score_history': score_list,
        'credit_trends': credit_trends
    }
    
    return render(request, 'cibil/score_history.html', context)

@login_required
def what_if_analysis(request):
    """What-if scenario analysis for score improvement"""
    
    if request.method == 'POST':
        # Process what-if scenario
        current_score = CIBILScore.objects.filter(user=request.user).first()
        if not current_score:
            messages.error(request, "Please calculate your current CIBIL score first.")
            return redirect('cibil:dashboard')
        
        # Get scenario parameters
        reduce_utilization = request.POST.get('reduce_utilization', 0)
        eliminate_late_payments = request.POST.get('eliminate_late_payments') == 'on'
        increase_credit_limit = request.POST.get('increase_credit_limit', 0)
        
        # Calculate projected score
        projected_score = current_score.calculated_score
        changes = []
        
        if float(reduce_utilization) > 0:
            # Utilization reduction impact
            current_util = current_score.average_credit_utilization
            new_util = max(0, current_util - float(reduce_utilization))
            
            if new_util <= 10:
                util_boost = 60
            elif new_util <= 30:
                util_boost = 40
            else:
                util_boost = 20
                
            projected_score += util_boost
            changes.append(f"Reduce utilization by {reduce_utilization}%: +{util_boost} points")
        
        if eliminate_late_payments:
            payment_boost = min(50, current_score.late_payments_count * 20)
            projected_score += payment_boost
            changes.append(f"Eliminate late payments: +{payment_boost} points")
        
        if float(increase_credit_limit) > 0:
            limit_boost = min(30, int(float(increase_credit_limit) / 1000) * 2)
            projected_score += limit_boost
            changes.append(f"Increase credit limit: +{limit_boost} points")
        
        projected_score = min(900, projected_score)  # Cap at 900
        
        # Save simulation
        simulation = ScoreSimulation.objects.create(
            user=request.user,
            simulation_name=f"Improvement Scenario - {timezone.now().strftime('%Y-%m-%d')}",
            base_score=current_score.calculated_score,
            proposed_changes={
                'reduce_utilization': reduce_utilization,
                'eliminate_late_payments': eliminate_late_payments,
                'increase_credit_limit': increase_credit_limit,
                'changes': changes
            },
            projected_score=projected_score,
            score_improvement=projected_score - current_score.calculated_score,
            timeframe_months=6,
            implementation_difficulty='MODERATE'
        )
        
        return JsonResponse({
            'success': True,
            'current_score': current_score.calculated_score,
            'projected_score': projected_score,
            'improvement': projected_score - current_score.calculated_score,
            'changes': changes
        })
    
    # GET request - show what-if form
    current_score = CIBILScore.objects.filter(user=request.user).first()
    simulations = ScoreSimulation.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    context = {
        'current_score': current_score,
        'simulations': simulations
    }
    
    return render(request, 'cibil/what_if_analysis.html', context)


@login_required
def score_analysis(request):
    """Detailed CIBIL score analysis view"""
    try:
        # Get user's latest score record
        score_record = CIBILScore.objects.filter(user=request.user).first()
        
        if not score_record:
            messages.error(request, "Please calculate your CIBIL score first.")
            return redirect('cibil:dashboard')
        
        # Get credit statements for detailed analysis
        from bank_analyzer.models import CreditStatement
        credit_statements = CreditStatement.objects.filter(user=request.user).order_by('-statement_date')[:6]
        
        # Calculate month-over-month trends
        score_history = CIBILScore.objects.filter(user=request.user).order_by('calculation_date')
        trends = []
        
        for i, score in enumerate(score_history):
            if i > 0:
                prev_score = score_history[i-1]
                change = score.calculated_score - prev_score.calculated_score
                trends.append({
                    'date': score.calculation_date,
                    'score': score.calculated_score,
                    'change': change,
                    'change_percentage': (change / prev_score.calculated_score) * 100 if prev_score.calculated_score > 0 else 0
                })
        
        # Calculate factor impacts
        factor_impacts = ScoreFactorImpact.objects.filter(
            cibil_score=score_record
        ).order_by('-impact_points')
        
        # Generate detailed insights
        ai_insights = generate_ai_insights({
            'score': score_record.calculated_score,
            'utilization': score_record.average_credit_utilization,
            'payment_history': score_record.payment_history_percentage,
            'credit_age': score_record.credit_history_months,
            'late_payments': score_record.late_payments_count,
            'credit_limit': score_record.total_credit_limit
        }, request.user)
        
        context = {
            'score_record': score_record,
            'credit_statements': credit_statements,
            'trends': trends,
            'factor_impacts': factor_impacts,
            'ai_insights': ai_insights,
            'detailed_analysis': True
        }
        
        return render(request, 'cibil/score_analysis.html', context)
        
    except Exception as e:
        messages.error(request, "Error loading score analysis. Please try again.")
        return redirect('cibil:dashboard')


@login_required  
def improve_score(request):
    """CIBIL score improvement recommendations and action plan"""
    try:
        # Get user's latest score record
        score_record = CIBILScore.objects.filter(user=request.user).first()
        
        if not score_record:
            messages.error(request, "Please calculate your CIBIL score first.")
            return redirect('cibil:dashboard')
        
        # Get basic AI insights for improvement suggestions (existing function)
        ai_insights = generate_ai_insights({
            'score': score_record.calculated_score,
            'utilization': score_record.average_credit_utilization,
            'payment_history': score_record.payment_history_percentage,
            'credit_age': score_record.credit_history_months,
            'late_payments': score_record.late_payments_count,
            'credit_limit': score_record.total_credit_limit
        }, request.user)
        
        # Calculate potential improvements
        improvement_plan = []
        
        # Credit utilization improvement
        if score_record.average_credit_utilization > 30:
            target_utilization = 10  # Optimal utilization
            potential_boost = min(80, (score_record.average_credit_utilization - target_utilization) * 2)
            improvement_plan.append({
                'category': 'Credit Utilization',
                'current': f'{score_record.average_credit_utilization:.1f}%',
                'target': f'{target_utilization}%',
                'potential_boost': potential_boost,
                'timeframe': '1-2 months',
                'difficulty': 'Easy',
                'actions': [
                    'Pay down existing balances',
                    'Request credit limit increases',
                    'Spread balances across multiple cards'
                ]
            })
        
        # Payment history improvement
        if score_record.late_payments_count > 0:
            potential_boost = min(60, score_record.late_payments_count * 15)
            improvement_plan.append({
                'category': 'Payment History',
                'current': f'{score_record.payment_history_percentage:.1f}% on-time',
                'target': '100% on-time',
                'potential_boost': potential_boost,
                'timeframe': '3-6 months',
                'difficulty': 'Easy',
                'actions': [
                    'Set up automatic payments',
                    'Create payment reminders',
                    'Pay at least minimum amounts on time'
                ]
            })
        
        # Credit history length improvement
        if score_record.credit_history_months < 60:
            potential_boost = 20
            improvement_plan.append({
                'category': 'Credit History Length',
                'current': f'{score_record.credit_history_months} months',
                'target': '60+ months',
                'potential_boost': potential_boost,
                'timeframe': '12+ months',
                'difficulty': 'Passive',
                'actions': [
                    'Keep old accounts open',
                    'Use old cards occasionally',
                    'Avoid closing accounts unnecessarily'
                ]
            })
        
        # Credit mix improvement
        from bank_analyzer.models import CreditStatement
        credit_types = CreditStatement.objects.filter(user=request.user).values('bank_name').distinct().count()
        if credit_types < 3:
            potential_boost = 25
            improvement_plan.append({
                'category': 'Credit Mix',
                'current': f'{credit_types} credit types',
                'target': '3+ credit types',
                'potential_boost': potential_boost,
                'timeframe': '6-12 months',
                'difficulty': 'Moderate',
                'actions': [
                    'Consider different types of credit',
                    'Add installment loans if needed',
                    'Maintain variety in credit products'
                ]
            })
        
        # Calculate total potential improvement
        total_potential = sum(plan['potential_boost'] for plan in improvement_plan)
        projected_score = min(900, score_record.calculated_score + total_potential)
        
        # Get detailed improvement insights from Gemini AI
        gemini_insights = generate_improvement_insights_from_gemini({
            'score': score_record.calculated_score,
            'utilization': score_record.average_credit_utilization,
            'payment_history': score_record.payment_history_percentage,
            'credit_age': score_record.credit_history_months,
            'late_payments': score_record.late_payments_count,
            'credit_limit': float(score_record.total_credit_limit)
        }, improvement_plan, request.user)
        
        # Get recent simulations
        simulations = ScoreSimulation.objects.filter(user=request.user).order_by('-created_at')[:5]
        
        context = {
            'score_record': score_record,
            'improvement_plan': improvement_plan,
            'total_potential': total_potential,
            'projected_score': projected_score,
            'ai_insights': ai_insights,
            'gemini_insights': gemini_insights,
            'simulations': simulations
        }
        
        return render(request, 'cibil/improve_score.html', context)
        
    except Exception as e:
        messages.error(request, "Error loading improvement recommendations. Please try again.")
        return redirect('cibil:dashboard')


@login_required
def quick_import_cibil(request):
    """Quick import CIBIL score from uploaded data - can be called via AJAX or direct"""
    
    if request.method == 'POST':
        try:
            # Check if user has uploaded data
            has_credit_data = CreditCardStatement.objects.filter(user=request.user).exists()
            if not has_credit_data:
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'No credit card data found. Please upload statements first.'
                    }, status=400)
                else:
                    messages.error(request, "No credit card data found. Please upload statements first.")
                    return redirect('cibil:dashboard')
            
            # Delete any existing score to create fresh one
            CIBILScore.objects.filter(user=request.user).delete()
            
            # Calculate score from uploaded data using existing function
            return handle_import_existing_data(request)
            
        except Exception as e:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Error importing data: {str(e)}'
                }, status=500)
            else:
                messages.error(request, f"Error importing data: {str(e)}")
                return redirect('cibil:dashboard')
    
    # GET request - redirect to dashboard
    return redirect('cibil:dashboard')
