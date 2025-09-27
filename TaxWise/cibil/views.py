# cibil/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Avg, Count, Q, Sum, Max, Min
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import datetime, timedelta, date
import json
import csv

from .models import (
    CibilProfile, CreditAccount, PaymentHistory, 
    CibilScoreHistory, CibilRecommendation, WhatIfScenario,
    CreditInquiry, AlertSettings
)
from .forms import (
    CibilProfileForm, CreditAccountForm, PaymentHistoryForm,
    WhatIfScenarioForm, ScoreUpdateForm
)
from .utils import CibilScoreCalculator, RecommendationEngine, ScoreAnalyzer

# ==================== MAIN DASHBOARD ====================

@login_required
def dashboard(request):
    """Main CIBIL dashboard with comprehensive overview"""
    try:
        cibil_profile = CibilProfile.objects.get(user=request.user)
    except CibilProfile.DoesNotExist:
        return redirect('cibil:create_profile')
    
    # Get recent score history (last 12 months)
    twelve_months_ago = date.today() - timedelta(days=365)
    recent_scores = CibilScoreHistory.objects.filter(
        cibil_profile=cibil_profile,
        score_date__gte=twelve_months_ago
    ).order_by('score_date')
    
    # Get active credit accounts
    active_accounts = CreditAccount.objects.filter(
        cibil_profile=cibil_profile,
        account_status='ACTIVE'
    ).select_related()
    
    # Calculate key financial metrics
    total_credit_limit = sum(
        acc.credit_limit or 0 for acc in active_accounts 
        if acc.account_type in ['CREDIT_CARD', 'OVERDRAFT']
    )
    total_outstanding = sum(acc.current_balance for acc in active_accounts)
    overall_utilization = (
        (total_outstanding / total_credit_limit * 100) 
        if total_credit_limit > 0 else 0
    )
    
    # Payment behavior analysis (last 6 months)
    six_months_ago = date.today() - timedelta(days=180)
    recent_payments = PaymentHistory.objects.filter(
        credit_account__cibil_profile=cibil_profile,
        payment_date__gte=six_months_ago
    )
    
    payment_stats = {
        'total_payments': recent_payments.count(),
        'on_time_payments': recent_payments.filter(payment_status='ON_TIME').count(),
        'late_payments': recent_payments.exclude(payment_status='ON_TIME').count(),
        'missed_payments': recent_payments.filter(payment_status='MISSED').count(),
    }
    
    payment_stats['on_time_percentage'] = (
        (payment_stats['on_time_payments'] / payment_stats['total_payments'] * 100)
        if payment_stats['total_payments'] > 0 else 0
    )
    
    # Get high priority recommendations
    high_priority_recommendations = CibilRecommendation.objects.filter(
        cibil_profile=cibil_profile,
        is_completed=False,
        priority='HIGH'
    ).order_by('-potential_score_impact')[:3]
    
    # Recent credit inquiries (last 12 months)
    recent_inquiries = CreditInquiry.objects.filter(
        cibil_profile=cibil_profile,
        inquiry_date__gte=twelve_months_ago,
        inquiry_type='HARD'
    )
    
    # Account distribution
    account_type_distribution = list(
        active_accounts.values('account_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # Score trend analysis
    score_trend = 'stable'
    if recent_scores.count() >= 2:
        latest_score = recent_scores.last().score
        previous_score = recent_scores[recent_scores.count()-2].score
        if latest_score > previous_score + 10:
            score_trend = 'improving'
        elif latest_score < previous_score - 10:
            score_trend = 'declining'
    
    context = {
        'cibil_profile': cibil_profile,
        'recent_scores': recent_scores,
        'active_accounts': active_accounts,
        'total_credit_limit': total_credit_limit,
        'total_outstanding': total_outstanding,
        'overall_utilization': round(overall_utilization, 2),
        'payment_stats': payment_stats,
        'high_priority_recommendations': high_priority_recommendations,
        'recent_inquiries': recent_inquiries,
        'account_type_distribution': account_type_distribution,
        'score_trend': score_trend,
    }
    
    return render(request, 'cibil/dashboard.html', context)

# ==================== PROFILE MANAGEMENT ====================

@login_required
def create_profile(request):
    """Create CIBIL profile for new users"""
    if hasattr(request.user, 'cibil_profile'):
        messages.info(request, 'You already have a CIBIL profile.')
        return redirect('cibil:dashboard')
    
    if request.method == 'POST':
        form = CibilProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            
            # Create default alert settings
            AlertSettings.objects.create(cibil_profile=profile)
            
            messages.success(request, 'CIBIL profile created successfully!')
            return redirect('cibil:dashboard')
    else:
        form = CibilProfileForm()
    
    return render(request, 'cibil/create_profile.html', {'form': form})

@login_required
def update_profile(request):
    """Update existing CIBIL profile"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    if request.method == 'POST':
        form = CibilProfileForm(request.POST, instance=cibil_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('cibil:dashboard')
    else:
        form = CibilProfileForm(instance=cibil_profile)
    
    return render(request, 'cibil/update_profile.html', {
        'form': form,
        'cibil_profile': cibil_profile
    })

@login_required
def update_score(request):
    """Update current CIBIL score"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    if request.method == 'POST':
        form = ScoreUpdateForm(request.POST, instance=cibil_profile)
        if form.is_valid():
            new_score = form.cleaned_data['current_score']
            
            # Update score with history
            cibil_profile.update_score(new_score, {
                'source': 'manual_update',
                'updated_by': request.user.username
            })
            
            messages.success(request, f'CIBIL score updated to {new_score}!')
            return redirect('cibil:dashboard')
    else:
        form = ScoreUpdateForm(instance=cibil_profile)
    
    return render(request, 'cibil/update_score.html', {
        'form': form,
        'cibil_profile': cibil_profile
    })

# ==================== CREDIT ACCOUNTS MANAGEMENT ====================

@login_required
def credit_accounts(request):
    """List all credit accounts with filtering"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    accounts = CreditAccount.objects.filter(cibil_profile=cibil_profile)
    
    # Apply filters
    account_type = request.GET.get('account_type')
    status = request.GET.get('status')
    
    if account_type and account_type != 'all':
        accounts = accounts.filter(account_type=account_type)
    
    if status and status != 'all':
        accounts = accounts.filter(account_status=status)
    
    # Pagination
    paginator = Paginator(accounts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary statistics
    total_accounts = accounts.count()
    active_accounts = accounts.filter(account_status='ACTIVE').count()
    total_credit_limit = sum(acc.credit_limit or 0 for acc in accounts)
    total_balance = sum(acc.current_balance for acc in accounts)
    
    context = {
        'page_obj': page_obj,
        'cibil_profile': cibil_profile,
        'account_types': CreditAccount.ACCOUNT_TYPES,
        'account_statuses': CreditAccount.ACCOUNT_STATUS,
        'selected_type': account_type,
        'selected_status': status,
        'total_accounts': total_accounts,
        'active_accounts': active_accounts,
        'total_credit_limit': total_credit_limit,
        'total_balance': total_balance,
    }
    
    return render(request, 'cibil/credit_accounts.html', context)

@login_required
def add_credit_account(request):
    """Add new credit account"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    if request.method == 'POST':
        form = CreditAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.cibil_profile = cibil_profile
            account.save()
            
            messages.success(request, f'{account.get_account_type_display()} account added successfully!')
            return redirect('cibil:credit_accounts')
    else:
        form = CreditAccountForm()
    
    return render(request, 'cibil/add_credit_account.html', {'form': form})

@login_required
def edit_credit_account(request, account_id):
    """Edit existing credit account"""
    account = get_object_or_404(
        CreditAccount, 
        id=account_id, 
        cibil_profile__user=request.user
    )
    
    if request.method == 'POST':
        form = CreditAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Credit account updated successfully!')
            return redirect('cibil:credit_accounts')
    else:
        form = CreditAccountForm(instance=account)
    
    return render(request, 'cibil/edit_credit_account.html', {
        'form': form,
        'account': account
    })

@login_required
def delete_credit_account(request, account_id):
    """Delete credit account"""
    account = get_object_or_404(
        CreditAccount, 
        id=account_id, 
        cibil_profile__user=request.user
    )
    
    if request.method == 'POST':
        account_name = str(account)
        account.delete()
        messages.success(request, f'{account_name} deleted successfully!')
        return redirect('cibil:credit_accounts')
    
    return render(request, 'cibil/delete_credit_account.html', {'account': account})

@login_required
def account_detail(request, account_id):
    """Detailed view of a credit account"""
    account = get_object_or_404(
        CreditAccount, 
        id=account_id, 
        cibil_profile__user=request.user
    )
    
    # Get recent payment history
    recent_payments = account.payment_history.all()[:20]
    
    # Payment statistics
    total_payments = account.payment_history.count()
    on_time_payments = account.payment_history.filter(payment_status='ON_TIME').count()
    late_payments = account.payment_history.exclude(payment_status='ON_TIME').count()
    
    # Monthly payment trend (last 12 months)
    twelve_months_ago = date.today() - timedelta(days=365)
    monthly_payments = account.payment_history.filter(
        payment_date__gte=twelve_months_ago
    ).extra(
        select={'month': 'EXTRACT(month FROM payment_date)'}
    ).values('month').annotate(
        count=Count('id'),
        on_time_count=Count('id', filter=Q(payment_status='ON_TIME'))
    ).order_by('month')
    
    context = {
        'account': account,
        'recent_payments': recent_payments,
        'total_payments': total_payments,
        'on_time_payments': on_time_payments,
        'late_payments': late_payments,
        'on_time_percentage': (on_time_payments / total_payments * 100) if total_payments > 0 else 0,
        'monthly_payments': monthly_payments,
    }
    
    return render(request, 'cibil/account_detail.html', context)

# ==================== PAYMENT HISTORY ====================

@login_required
def payment_history(request, account_id=None):
    """View payment history for specific account or all accounts"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    if account_id:
        account = get_object_or_404(
            CreditAccount, 
            id=account_id, 
            cibil_profile=cibil_profile
        )
        payments = PaymentHistory.objects.filter(credit_account=account)
        page_title = f'Payment History - {account}'
    else:
        account = None
        payments = PaymentHistory.objects.filter(
            credit_account__cibil_profile=cibil_profile
        )
        page_title = 'All Payment History'
    
    # Apply filters
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status_filter and status_filter != 'all':
        payments = payments.filter(payment_status=status_filter)
    
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    
    # Pagination
    paginator = Paginator(payments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'account': account,
        'page_title': page_title,
        'payment_statuses': PaymentHistory.PAYMENT_STATUS,
        'selected_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'cibil/payment_history.html', context)

@login_required
def add_payment(request, account_id):
    """Add payment record for specific account"""
    account = get_object_or_404(
        CreditAccount, 
        id=account_id, 
        cibil_profile__user=request.user
    )
    
    if request.method == 'POST':
        form = PaymentHistoryForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.credit_account = account
            
            # Set due_date same as payment_date if not provided
            if not payment.due_date:
                payment.due_date = payment.payment_date
            
            payment.save()
            
            # Update account balance and last payment date
            if payment.payment_status == 'ON_TIME':
                account.current_balance = max(0, account.current_balance - payment.paid_amount)
                account.last_payment_date = payment.payment_date
                account.save()
            
            messages.success(request, 'Payment record added successfully!')
            return redirect('cibil:account_detail', account_id=account.id)
    else:
        form = PaymentHistoryForm(initial={
            'payment_date': date.today(),
            'due_date': date.today()
        })
    
    return render(request, 'cibil/add_payment.html', {
        'form': form,
        'account': account
    })

# ==================== RECOMMENDATIONS ====================

@login_required
def recommendations(request):
    """View and manage CIBIL improvement recommendations"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    # Generate fresh recommendations
    recommendation_engine = RecommendationEngine(cibil_profile)
    recommendation_engine.generate_recommendations()
    
    # Get recommendations by priority
    high_priority = CibilRecommendation.objects.filter(
        cibil_profile=cibil_profile,
        is_completed=False,
        priority='HIGH'
    ).order_by('-potential_score_impact')
    
    medium_priority = CibilRecommendation.objects.filter(
        cibil_profile=cibil_profile,
        is_completed=False,
        priority='MEDIUM'
    ).order_by('-potential_score_impact')
    
    low_priority = CibilRecommendation.objects.filter(
        cibil_profile=cibil_profile,
        is_completed=False,
        priority='LOW'
    ).order_by('-potential_score_impact')
    
    completed_recommendations = CibilRecommendation.objects.filter(
        cibil_profile=cibil_profile,
        is_completed=True
    ).order_by('-completed_at')[:10]
    
    # Calculate potential total score improvement
    total_potential_improvement = sum(
        rec.potential_score_impact 
        for rec in CibilRecommendation.objects.filter(
            cibil_profile=cibil_profile,
            is_completed=False
        )
    )
    
    context = {
        'cibil_profile': cibil_profile,
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'low_priority': low_priority,
        'completed_recommendations': completed_recommendations,
        'total_potential_improvement': total_potential_improvement,
    }
    
    return render(request, 'cibil/recommendations.html', context)

@login_required
@require_http_methods(["POST"])
def mark_recommendation_completed(request, recommendation_id):
    """Mark a recommendation as completed via AJAX"""
    recommendation = get_object_or_404(
        CibilRecommendation, 
        id=recommendation_id, 
        cibil_profile__user=request.user
    )
    
    user_notes = request.POST.get('user_notes', '')
    
    recommendation.mark_completed()
    if user_notes:
        recommendation.user_notes = user_notes
        recommendation.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': 'Recommendation marked as completed!'
        })
    
    messages.success(request, 'Recommendation marked as completed!')
    return redirect('cibil:recommendations')

# ==================== WHAT-IF SCENARIOS ====================

@login_required
def what_if_scenarios(request):
    """View what-if scenario analysis"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    scenarios = WhatIfScenario.objects.filter(cibil_profile=cibil_profile).order_by('-created_at')
    
    context = {
        'cibil_profile': cibil_profile,
        'scenarios': scenarios,
        'current_score': cibil_profile.current_score or 650,
    }
    
    return render(request, 'cibil/what_if_scenarios.html', context)

@login_required
@csrf_exempt
def create_scenario(request):
    """Create a new what-if scenario via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'})
    
    try:
        data = json.loads(request.body)
        cibil_profile = get_object_or_404(CibilProfile, user=request.user)
        
        calculator = CibilScoreCalculator(cibil_profile)
        projected_score = calculator.calculate_scenario_score(data.get('scenario_data', {}))
        time_estimate = calculator.estimate_time_to_achieve(projected_score)
        
        scenario = WhatIfScenario.objects.create(
            cibil_profile=cibil_profile,
            scenario_name=data.get('scenario_name', 'Unnamed Scenario'),
            description=data.get('description', ''),
            current_score=cibil_profile.current_score or 650,
            scenario_data=data.get('scenario_data', {}),
            projected_score=projected_score,
            time_to_achieve=time_estimate,
            factor_improvements=calculator.get_factor_breakdown()
        )
        
        return JsonResponse({
            'status': 'success',
            'scenario_id': scenario.id,
            'projected_score': projected_score,
            'score_improvement': scenario.score_improvement,
            'time_to_achieve': time_estimate
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def delete_scenario(request, scenario_id):
    """Delete a what-if scenario"""
    scenario = get_object_or_404(
        WhatIfScenario, 
        id=scenario_id, 
        cibil_profile__user=request.user
    )
    
    if request.method == 'POST':
        scenario.delete()
        messages.success(request, 'Scenario deleted successfully!')
    
    return redirect('cibil:what_if_scenarios')

# ==================== ANALYTICS & REPORTS ====================

@login_required
def analytics(request):
    """Advanced analytics and insights"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    analyzer = ScoreAnalyzer(cibil_profile)
    
    # Get analytics data
    score_analysis = analyzer.analyze_score_trends()
    factor_analysis = analyzer.analyze_factors()
    benchmarks = analyzer.get_benchmarks()
    predictions = analyzer.predict_future_scores()
    
    context = {
        'cibil_profile': cibil_profile,
        'score_analysis': score_analysis,
        'factor_analysis': factor_analysis,
        'benchmarks': benchmarks,
        'predictions': predictions,
    }
    
    return render(request, 'cibil/analytics.html', context)

@login_required
def export_data(request):
    """Export user's CIBIL data to CSV"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cibil_data_{request.user.username}.csv"'
    
    writer = csv.writer(response)
    
    # Write score history
    writer.writerow(['Score History'])
    writer.writerow(['Date', 'Score', 'Change'])
    
    score_history = CibilScoreHistory.objects.filter(
        cibil_profile=cibil_profile
    ).order_by('score_date')
    
    for i, score in enumerate(score_history):
        change = score.score_change if i > 0 else 0
        writer.writerow([score.score_date, score.score, change])
    
    writer.writerow([])  # Empty row
    
    # Write credit accounts
    writer.writerow(['Credit Accounts'])
    writer.writerow(['Bank', 'Account Type', 'Credit Limit', 'Current Balance', 'Utilization', 'Status'])
    
    for account in cibil_profile.credit_accounts.all():
        writer.writerow([
            account.bank_name,
            account.get_account_type_display(),
            account.credit_limit or 0,
            account.current_balance,
            f"{account.credit_utilization:.2f}%",
            account.get_account_status_display()
        ])
    
    return response

# ==================== API ENDPOINTS ====================

@login_required
def score_history_api(request):
    """API endpoint for score history chart data"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    period = request.GET.get('period', '12')  # months
    end_date = date.today()
    start_date = end_date - timedelta(days=int(period) * 30)
    
    scores = CibilScoreHistory.objects.filter(
        cibil_profile=cibil_profile,
        score_date__gte=start_date
    ).order_by('score_date')
    
    data = [
        {
            'date': score.score_date.strftime('%Y-%m-%d'),
            'score': score.score,
            'change': score.score_change
        }
        for score in scores
    ]
    
    return JsonResponse({'scores': data})

@login_required
def utilization_api(request):
    """API endpoint for credit utilization data"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    accounts = CreditAccount.objects.filter(
        cibil_profile=cibil_profile,
        account_status='ACTIVE',
        account_type__in=['CREDIT_CARD', 'OVERDRAFT']
    )
    
    data = [
        {
            'account': str(account),
            'utilization': float(account.credit_utilization),
            'balance': float(account.current_balance),
            'limit': float(account.credit_limit or 0)
        }
        for account in accounts
        if account.credit_limit
    ]
    
    return JsonResponse({'utilization_data': data})

@login_required
def payment_trends_api(request):
    """API endpoint for payment trend analysis"""
    cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    
    # Get payment data for last 12 months grouped by month
    twelve_months_ago = date.today() - timedelta(days=365)
    
    payments = PaymentHistory.objects.filter(
        credit_account__cibil_profile=cibil_profile,
        payment_date__gte=twelve_months_ago
    ).extra(
        select={
            'month': 'EXTRACT(month FROM payment_date)',
            'year': 'EXTRACT(year FROM payment_date)'
        }
    ).values('month', 'year').annotate(
        total_payments=Count('id'),
        on_time_payments=Count('id', filter=Q(payment_status='ON_TIME')),
        late_payments=Count('id', filter=~Q(payment_status='ON_TIME'))
    ).order_by('year', 'month')
    
    data = [
        {
            'period': f"{int(payment['year'])}-{int(payment['month']):02d}",
            'total_payments': payment['total_payments'],
            'on_time_payments': payment['on_time_payments'],
            'late_payments': payment['late_payments'],
            'on_time_percentage': (
                payment['on_time_payments'] / payment['total_payments'] * 100
                if payment['total_payments'] > 0 else 0
            )
        }
        for payment in payments
    ]
    
    return JsonResponse({'payment_trends': data})

# ==================== CIBIL ADVICE ENDPOINT ====================

@login_required
def get_cibil_advice(request):
    """
    Get personalized CIBIL advice based on user's profile and financial data
    Can return JSON for API calls or render template for regular requests
    """
    try:
        cibil_profile = get_object_or_404(CibilProfile, user=request.user)
    except CibilProfile.DoesNotExist:
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'status': 'error',
                'message': 'Please create your CIBIL profile first'
            })
        messages.error(request, 'Please create your CIBIL profile first.')
        return redirect('cibil:create_profile')
    
    # Generate comprehensive advice
    advice_generator = CibilAdviceGenerator(cibil_profile)
    advice_data = advice_generator.generate_comprehensive_advice()
    
    # If it's an API request, return JSON
    if request.headers.get('Content-Type') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({
            'status': 'success',
            'data': advice_data
        })
    
    # Otherwise render template
    context = {
        'cibil_profile': cibil_profile,
        'advice_data': advice_data,
    }
    
    return render(request, 'cibil/advice.html', context)


class CibilAdviceGenerator:
    """
    Helper class to generate personalized CIBIL advice
    """
    
    def __init__(self, cibil_profile):
        self.profile = cibil_profile
        self.credit_accounts = CreditAccount.objects.filter(
            cibil_profile=cibil_profile,
            account_status='ACTIVE'
        )
    
    def generate_comprehensive_advice(self):
        """Generate comprehensive advice based on user's financial profile"""
        advice = {
            'overall_health': self._assess_overall_health(),
            'priority_actions': self._get_priority_actions(),
            'score_improvement_tips': self._get_score_improvement_tips(),
            'factor_analysis': self._analyze_score_factors(),
            'monthly_action_plan': self._create_monthly_action_plan(),
            'long_term_strategy': self._create_long_term_strategy(),
        }
        return advice
    
    def _assess_overall_health(self):
        """Assess overall CIBIL health"""
        score = self.profile.current_score or 650
        
        if score >= 750:
            status = 'excellent'
            message = "Your CIBIL score is excellent! You're in the top tier."
            color = 'green'
        elif score >= 700:
            status = 'good'
            message = "Your CIBIL score is good. You can get most loans approved."
            color = 'blue'
        elif score >= 650:
            status = 'fair'
            message = "Your CIBIL score is fair. There's room for improvement."
            color = 'orange'
        elif score >= 600:
            status = 'poor'
            message = "Your CIBIL score needs attention to access better credit options."
            color = 'red'
        else:
            status = 'critical'
            message = "Your CIBIL score is critical. Immediate action needed."
            color = 'darkred'
        
        return {
            'status': status,
            'message': message,
            'color': color,
            'score': score
        }
    
    def _get_priority_actions(self):
        """Get top 3 priority actions"""
        actions = []
        
        # Check payment history
        recent_late_payments = PaymentHistory.objects.filter(
            credit_account__cibil_profile=self.profile,
            payment_date__gte=date.today() - timedelta(days=90)
        ).exclude(payment_status='ON_TIME')
        
        if recent_late_payments.exists():
            actions.append({
                'priority': 1,
                'title': 'Fix Payment Delays',
                'description': 'You have recent late payments. Set up auto-pay to avoid future delays.',
                'impact': 'High',
                'timeline': 'Immediate'
            })
        
        # Check credit utilization
        high_utilization_accounts = [
            acc for acc in self.credit_accounts 
            if acc.credit_utilization > 30 and acc.account_type == 'CREDIT_CARD'
        ]
        
        if high_utilization_accounts:
            actions.append({
                'priority': 2,
                'title': 'Reduce Credit Utilization',
                'description': f'You have {len(high_utilization_accounts)} accounts with >30% utilization.',
                'impact': 'High',
                'timeline': '1-2 months'
            })
        
        # Check for closed accounts
        old_accounts = CreditAccount.objects.filter(
            cibil_profile=self.profile,
            account_status='CLOSED',
            account_closed_date__gte=date.today() - timedelta(days=180)
        )
        
        if old_accounts.exists():
            actions.append({
                'priority': 3,
                'title': 'Maintain Old Credit Accounts',
                'description': 'Keep old accounts open to maintain credit history length.',
                'impact': 'Medium',
                'timeline': '3-6 months'
            })
        
        return actions[:3]
    
    def _get_score_improvement_tips(self):
        """Get specific score improvement tips"""
        tips = []
        current_score = self.profile.current_score or 650
        
        # Payment history tips
        tips.append({
            'category': 'Payment History (35%)',
            'current_status': self._get_payment_status(),
            'tips': [
                'Set up automatic payments for all credit accounts',
                'Pay at least the minimum amount before due date',
                'If you missed payments, get current and stay current',
                'Consider paying twice a month to reduce utilization'
            ]
        })
        
        # Credit utilization tips
        utilization_data = self._get_utilization_status()
        tips.append({
            'category': 'Credit Utilization (30%)',
            'current_status': utilization_data['status'],
            'tips': [
                'Keep credit card balances below 30% of limit',
                'Pay down balances before statement closing date',
                'Consider requesting credit limit increases',
                'Spread balances across multiple cards if needed'
            ]
        })
        
        # Credit history length tips
        tips.append({
            'category': 'Credit History Length (15%)',
            'current_status': self._get_history_length_status(),
            'tips': [
                'Keep old credit accounts open',
                'Use old cards occasionally to keep them active',
                'Avoid closing your oldest credit account',
                'Be patient - this factor improves with time'
            ]
        })
        
        return tips
    
    def _analyze_score_factors(self):
        """Analyze each factor affecting the score"""
        return {
            'payment_history': {
                'weight': '35%',
                'status': self._get_payment_status(),
                'score_impact': self._calculate_payment_impact()
            },
            'credit_utilization': {
                'weight': '30%',
                'status': self._get_utilization_status()['status'],
                'score_impact': self._calculate_utilization_impact()
            },
            'credit_history_length': {
                'weight': '15%',
                'status': self._get_history_length_status(),
                'score_impact': self._calculate_history_impact()
            },
            'credit_mix': {
                'weight': '10%',
                'status': self._get_credit_mix_status(),
                'score_impact': self._calculate_mix_impact()
            },
            'new_credit': {
                'weight': '10%',
                'status': self._get_new_credit_status(),
                'score_impact': self._calculate_new_credit_impact()
            }
        }
    
    def _create_monthly_action_plan(self):
        """Create a month-by-month action plan"""
        plan = []
        
        for month in range(1, 7):  # 6-month plan
            month_plan = {
                'month': month,
                'focus': self._get_monthly_focus(month),
                'actions': self._get_monthly_actions(month),
                'expected_impact': self._get_expected_monthly_impact(month)
            }
            plan.append(month_plan)
        
        return plan
    
    def _create_long_term_strategy(self):
        """Create long-term improvement strategy"""
        current_score = self.profile.current_score or 650
        target_score = self.profile.target_score or min(850, current_score + 100)
        
        return {
            'current_score': current_score,
            'target_score': target_score,
            'estimated_timeline': self._estimate_timeline(current_score, target_score),
            'milestones': self._create_milestones(current_score, target_score),
            'key_strategies': [
                'Maintain 100% on-time payment history',
                'Keep credit utilization below 10%',
                'Diversify credit portfolio gradually',
                'Monitor credit report monthly',
                'Limit hard credit inquiries'
            ]
        }
    
    # Helper methods for status checks
    def _get_payment_status(self):
        """Get current payment status"""
        recent_payments = PaymentHistory.objects.filter(
            credit_account__cibil_profile=self.profile,
            payment_date__gte=date.today() - timedelta(days=180)
        )
        
        if not recent_payments.exists():
            return 'No recent payment history'
        
        on_time = recent_payments.filter(payment_status='ON_TIME').count()
        total = recent_payments.count()
        percentage = (on_time / total) * 100
        
        if percentage >= 95:
            return f'Excellent ({percentage:.1f}% on-time)'
        elif percentage >= 85:
            return f'Good ({percentage:.1f}% on-time)'
        elif percentage >= 75:
            return f'Fair ({percentage:.1f}% on-time)'
        else:
            return f'Needs Improvement ({percentage:.1f}% on-time)'
    
    def _get_utilization_status(self):
        """Get credit utilization status"""
        credit_cards = self.credit_accounts.filter(account_type='CREDIT_CARD')
        
        if not credit_cards.exists():
            return {'status': 'No credit cards', 'utilization': 0}
        
        total_limit = sum(card.credit_limit or 0 for card in credit_cards)
        total_balance = sum(card.current_balance for card in credit_cards)
        
        if total_limit == 0:
            return {'status': 'No credit limit data', 'utilization': 0}
        
        utilization = (total_balance / total_limit) * 100
        
        if utilization <= 10:
            status = f'Excellent ({utilization:.1f}%)'
        elif utilization <= 30:
            status = f'Good ({utilization:.1f}%)'
        elif utilization <= 50:
            status = f'Fair ({utilization:.1f}%)'
        else:
            status = f'High ({utilization:.1f}%)'
        
        return {'status': status, 'utilization': utilization}
    
    def _get_history_length_status(self):
        """Get credit history length status"""
        oldest_account = self.credit_accounts.aggregate(
            oldest=Min('account_opened_date')
        )['oldest']
        
        if not oldest_account:
            return 'No credit history'
        
        years = (date.today() - oldest_account).days / 365.25
        
        if years >= 10:
            return f'Excellent ({years:.1f} years)'
        elif years >= 5:
            return f'Good ({years:.1f} years)'
        elif years >= 2:
            return f'Fair ({years:.1f} years)'
        else:
            return f'Short ({years:.1f} years)'
    
    def _get_credit_mix_status(self):
        """Get credit mix status"""
        account_types = set(self.credit_accounts.values_list('account_type', flat=True))
        
        if len(account_types) >= 3:
            return 'Excellent mix'
        elif len(account_types) == 2:
            return 'Good mix'
        elif len(account_types) == 1:
            return 'Limited mix'
        else:
            return 'No active accounts'
    
    def _get_new_credit_status(self):
        """Get new credit inquiry status"""
        recent_inquiries = CreditInquiry.objects.filter(
            cibil_profile=self.profile,
            inquiry_type='HARD',
            inquiry_date__gte=date.today() - timedelta(days=365)
        ).count()
        
        if recent_inquiries == 0:
            return 'No recent inquiries'
        elif recent_inquiries <= 2:
            return f'Low impact ({recent_inquiries} inquiries)'
        elif recent_inquiries <= 5:
            return f'Moderate impact ({recent_inquiries} inquiries)'
        else:
            return f'High impact ({recent_inquiries} inquiries)'
    
    # Impact calculation methods (simplified for now)
    def _calculate_payment_impact(self):
        return "High positive impact" if "Excellent" in self._get_payment_status() else "Needs improvement"
    
    def _calculate_utilization_impact(self):
        util_data = self._get_utilization_status()
        return "High positive impact" if util_data['utilization'] <= 30 else "Negative impact"
    
    def _calculate_history_impact(self):
        return "Positive impact" if "years" in self._get_history_length_status() else "Limited impact"
    
    def _calculate_mix_impact(self):
        return "Positive impact" if "Good" in self._get_credit_mix_status() else "Limited impact"
    
    def _calculate_new_credit_impact(self):
        return "Neutral" if "No recent" in self._get_new_credit_status() else "Slight negative impact"
    
    # Monthly planning methods
    def _get_monthly_focus(self, month):
        focuses = [
            "Payment Behavior Optimization",
            "Credit Utilization Reduction", 
            "Account Management",
            "Credit Mix Improvement",
            "Score Monitoring & Analysis",
            "Long-term Strategy Review"
        ]
        return focuses[month - 1]
    
    def _get_monthly_actions(self, month):
        actions = [
            ["Set up auto-pay", "Review all due dates", "Clear any overdue amounts"],
            ["Pay down high balances", "Request credit limit increases", "Time payments strategically"],
            ["Keep old accounts active", "Close unnecessary new accounts", "Optimize account portfolio"],
            ["Consider adding installment loan", "Balance revolving vs installment credit"],
            ["Check credit report", "Dispute any errors", "Track score changes"],
            ["Review and adjust strategy", "Plan for major credit needs", "Set new targets"]
        ]
        return actions[month - 1]
    
    def _get_expected_monthly_impact(self, month):
        impacts = [
            "5-10 points improvement",
            "10-20 points improvement", 
            "5-15 points improvement",
            "5-10 points improvement",
            "Maintain current score",
            "Long-term sustained growth"
        ]
        return impacts[month - 1]
    
    def _estimate_timeline(self, current_score, target_score):
        """Estimate timeline to reach target score"""
        score_gap = target_score - current_score
        if score_gap <= 0:
            return "Target already achieved"
        elif score_gap <= 25:
            return "3-6 months"
        elif score_gap <= 50:
            return "6-12 months"
        elif score_gap <= 100:
            return "12-24 months"
        else:
            return "24+ months"
    
    def _create_milestones(self, current_score, target_score):
        """Create milestone targets"""
        milestones = []
        score_gap = target_score - current_score
        
        if score_gap > 0:
            milestone_increment = max(25, score_gap // 4)
            for i in range(1, 5):
                milestone_score = min(target_score, current_score + (milestone_increment * i))
                milestones.append({
                    'score': milestone_score,
                    'timeline': f"{i * 3}-{i * 6} months",
                    'key_focus': self._get_milestone_focus(i)
                })
        
        return milestones
    
    def _get_milestone_focus(self, milestone_num):
        focuses = [
            "Payment consistency",
            "Utilization optimization", 
            "Account diversification",
            "Score maintenance"
        ]
        return focuses[milestone_num - 1] if milestone_num <= len(focuses) else "Continued improvement"