# cibil/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
import re

from .models import (
    CibilProfile, CreditAccount, PaymentHistory, 
    CibilRecommendation, WhatIfScenario, CreditInquiry,
    AlertSettings
)

# ==================== PROFILE FORMS ====================

class CibilProfileForm(forms.ModelForm):
    """Form for creating and updating CIBIL profile"""
    
    class Meta:
        model = CibilProfile
        fields = [
            'pan_number', 'date_of_birth', 'phone_number', 
            'current_score', 'target_score'
        ]
        widgets = {
            'pan_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ABCDE1234F',
                'style': 'text-transform: uppercase;',
                'maxlength': '10'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': date.today().strftime('%Y-%m-%d')
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91XXXXXXXXXX',
                'pattern': r'\+91[6-9]\d{9}'
            }),
            'current_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 300,
                'max': 900,
                'placeholder': 'Enter your current CIBIL score (optional)'
            }),
            'target_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 300,
                'max': 900,
                'placeholder': 'Target CIBIL score to achieve'
            }),
        }
        labels = {
            'pan_number': 'PAN Number *',
            'date_of_birth': 'Date of Birth *',
            'phone_number': 'Mobile Number *',
            'current_score': 'Current CIBIL Score',
            'target_score': 'Target CIBIL Score',
        }
        help_texts = {
            'pan_number': 'Enter your 10-character PAN number',
            'phone_number': 'Enter Indian mobile number with +91',
            'current_score': 'Leave blank if you don\'t know your current score',
            'target_score': 'Set a realistic target score to achieve',
        }

    def clean_pan_number(self):
        """Validate PAN number format"""
        pan = self.cleaned_data.get('pan_number', '').upper().strip()
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
            raise ValidationError(
                'Please enter a valid PAN number (e.g., ABCDE1234F)'
            )
        return pan

    def clean_phone_number(self):
        """Validate and format phone number"""
        phone = self.cleaned_data.get('phone_number', '').strip()
        
        # Remove all non-digit characters except +
        phone_clean = re.sub(r'[^\d+]', '', phone)
        
        # Handle different input formats
        if phone_clean.startswith('+91'):
            phone_digits = phone_clean[3:]
        elif phone_clean.startswith('91') and len(phone_clean) == 12:
            phone_digits = phone_clean[2:]
        elif len(phone_clean) == 10:
            phone_digits = phone_clean
        else:
            raise ValidationError('Please enter a valid Indian mobile number')
        
        # Validate 10-digit mobile number
        if not (len(phone_digits) == 10 and phone_digits.startswith(('6', '7', '8', '9'))):
            raise ValidationError('Please enter a valid Indian mobile number (10 digits starting with 6/7/8/9)')
        
        return f'+91{phone_digits}'

    def clean_date_of_birth(self):
        """Validate date of birth"""
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 18:
                raise ValidationError('You must be at least 18 years old to have a CIBIL profile')
            if age > 100:
                raise ValidationError('Please enter a valid date of birth')
            if dob > today:
                raise ValidationError('Date of birth cannot be in the future')
        
        return dob

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        current_score = cleaned_data.get('current_score')
        target_score = cleaned_data.get('target_score')
        
        if current_score and target_score:
            if target_score <= current_score:
                raise ValidationError('Target score should be higher than current score')
            if target_score - current_score > 200:
                raise ValidationError('Target score should be realistic (within 200 points of current score)')
        
        return cleaned_data

class ScoreUpdateForm(forms.ModelForm):
    """Form for updating CIBIL score"""
    
    class Meta:
        model = CibilProfile
        fields = ['current_score']
        widgets = {
            'current_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 300,
                'max': 900,
                'placeholder': 'Enter your updated CIBIL score',
                'required': True
            })
        }
        labels = {
            'current_score': 'Updated CIBIL Score *'
        }

    def clean_current_score(self):
        """Validate score range"""
        score = self.cleaned_data.get('current_score')
        if score is not None:
            if score < 300 or score > 900:
                raise ValidationError('CIBIL score must be between 300 and 900')
        return score

# ==================== CREDIT ACCOUNT FORMS ====================

class CreditAccountForm(forms.ModelForm):
    """Form for adding/editing credit accounts"""
    
    class Meta:
        model = CreditAccount
        fields = [
            'account_type', 'bank_name', 'account_number', 
            'credit_limit', 'current_balance', 'original_amount',
            'monthly_installment', 'account_opened_date', 'account_status'
        ]
        widgets = {
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., HDFC Bank, ICICI Bank, SBI'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last 4 digits or masked number (e.g., XXXX1234)'
            }),
            'credit_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Credit limit (for credit cards/overdrafts)'
            }),
            'current_balance': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Current outstanding balance'
            }),
            'original_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Original loan amount (for term loans)'
            }),
            'monthly_installment': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Monthly EMI/installment amount'
            }),
            'account_opened_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': date.today().strftime('%Y-%m-%d')
            }),
            'account_status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'account_type': 'Account Type *',
            'bank_name': 'Bank/Lender Name *',
            'account_number': 'Account Number *',
            'credit_limit': 'Credit Limit (₹)',
            'current_balance': 'Current Outstanding Balance (₹) *',
            'original_amount': 'Original Loan Amount (₹)',
            'monthly_installment': 'Monthly EMI (₹)',
            'account_opened_date': 'Account Opening Date *',
            'account_status': 'Account Status *',
        }
        help_texts = {
            'credit_limit': 'Required for credit cards and overdrafts',
            'original_amount': 'Required for term loans (home, auto, personal loans)',
            'account_number': 'For security, enter only last 4 digits or use XXXX format',
        }

    def clean_account_opened_date(self):
        """Validate account opening date"""
        opened_date = self.cleaned_data.get('account_opened_date')
        if opened_date:
            if opened_date > date.today():
                raise ValidationError('Account opening date cannot be in the future')
            if opened_date < date.today() - timedelta(days=365*50):  # 50 years ago
                raise ValidationError('Account opening date seems too old')
        return opened_date

    def clean_credit_limit(self):
        """Validate credit limit"""
        credit_limit = self.cleaned_data.get('credit_limit')
        if credit_limit and credit_limit > 10000000:  # 1 Crore
            raise ValidationError('Credit limit seems unusually high. Please verify.')
        return credit_limit

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        account_type = cleaned_data.get('account_type')
        credit_limit = cleaned_data.get('credit_limit')
        current_balance = cleaned_data.get('current_balance', 0)
        original_amount = cleaned_data.get('original_amount')
        
        # Credit limit validation for revolving accounts
        if account_type in ['CREDIT_CARD', 'OVERDRAFT']:
            if not credit_limit:
                raise ValidationError('Credit limit is required for credit cards and overdrafts')
            if current_balance > credit_limit:
                raise ValidationError('Current balance cannot exceed credit limit')
        
        # Original amount validation for term loans
        if account_type in ['PERSONAL_LOAN', 'HOME_LOAN', 'AUTO_LOAN', 'EDUCATION_LOAN', 'BUSINESS_LOAN']:
            if not original_amount:
                raise ValidationError('Original loan amount is required for term loans')
            if current_balance > original_amount:
                raise ValidationError('Current balance cannot exceed original loan amount')
        
        return cleaned_data

# ==================== PAYMENT HISTORY FORMS ====================

class PaymentHistoryForm(forms.ModelForm):
    """Form for adding payment history records"""
    
    class Meta:
        model = PaymentHistory
        fields = [
            'payment_date', 'due_date', 'due_amount', 'paid_amount', 
            'payment_status', 'late_fee_charged', 'interest_charged'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': date.today().strftime('%Y-%m-%d')
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'due_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Amount that was due'
            }),
            'paid_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Amount actually paid'
            }),
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
            'late_fee_charged': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Late fee charged (if any)'
            }),
            'interest_charged': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Interest charged (if any)'
            }),
        }
        labels = {
            'payment_date': 'Payment Date *',
            'due_date': 'Due Date *',
            'due_amount': 'Due Amount (₹) *',
            'paid_amount': 'Paid Amount (₹) *',
            'payment_status': 'Payment Status *',
            'late_fee_charged': 'Late Fee Charged (₹)',
            'interest_charged': 'Interest Charged (₹)',
        }

    def clean(self):
        """Cross-field validation for payment data"""
        cleaned_data = super().clean()
        payment_date = cleaned_data.get('payment_date')
        due_date = cleaned_data.get('due_date')
        due_amount = cleaned_data.get('due_amount', 0)
        paid_amount = cleaned_data.get('paid_amount', 0)
        payment_status = cleaned_data.get('payment_status')
        
        # Date validation
        if payment_date and due_date:
            if payment_date < due_date - timedelta(days=30):
                raise ValidationError('Payment date seems too early compared to due date')
        
        # Payment status validation
        if payment_status == 'ON_TIME':
            if payment_date and due_date and payment_date > due_date:
                raise ValidationError('Payment cannot be marked as on-time if paid after due date')
            if paid_amount < due_amount:
                raise ValidationError('For on-time payments, paid amount should be at least equal to due amount')
        
        if payment_status == 'MISSED' and paid_amount > 0:
            raise ValidationError('For missed payments, paid amount should be 0')
        
        if payment_status == 'PARTIAL' and paid_amount >= due_amount:
            raise ValidationError('For partial payments, paid amount should be less than due amount')
        
        return cleaned_data

# ==================== BULK UPLOAD FORMS ====================

class BulkAccountUploadForm(forms.Form):
    """Form for bulk uploading credit account data via CSV"""
    
    csv_file = forms.FileField(
        label='CSV File *',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        }),
        help_text='Upload a CSV file with credit account data'
    )
    
    def clean_csv_file(self):
        """Validate CSV file"""
        csv_file = self.cleaned_data.get('csv_file')
        
        if csv_file:
            if not csv_file.name.endswith('.csv'):
                raise ValidationError('Please upload a CSV file')
            
            if csv_file.size > 5 * 1024 * 1024:  # 5MB limit
                raise ValidationError('File size should be less than 5MB')
        
        return csv_file

class BulkPaymentUploadForm(forms.Form):
    """Form for bulk uploading payment history via CSV"""
    
    csv_file = forms.FileField(
        label='CSV File *',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        }),
        help_text='Upload a CSV file with payment history data'
    )
    
    credit_account = forms.ModelChoiceField(
        queryset=CreditAccount.objects.none(),
        label='Credit Account *',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the credit account for these payments'
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['credit_account'].queryset = CreditAccount.objects.filter(
                cibil_profile__user=user,
                account_status='ACTIVE'
            )

# ==================== WHAT-IF SCENARIO FORMS ====================

class WhatIfScenarioForm(forms.Form):
    """Form for creating what-if scenarios"""
    
    scenario_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Pay off credit card debt'
        }),
        label='Scenario Name *'
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe your scenario in detail'
        }),
        label='Description'
    )
    
    # Credit utilization changes
    target_credit_utilization = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Target credit utilization %',
            'step': '0.1'
        }),
        label='Target Credit Utilization (%)'
    )
    
    # Payment behavior improvements
    target_on_time_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Target on-time payment %',
            'step': '0.1'
        }),
        label='Target On-Time Payment (%)'
    )
    
    # Account changes
    new_accounts_to_add = forms.IntegerField(
        min_value=0,
        max_value=10,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Number of new accounts'
        }),
        label='New Credit Accounts to Add'
    )
    
    accounts_to_close = forms.IntegerField(
        min_value=0,
        max_value=10,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Number of accounts to close'
        }),
        label='Accounts to Close'
    )
    
    # Debt reduction
    debt_reduction_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Amount of debt to pay off',
            'step': '0.01'
        }),
        label='Debt Reduction Amount (₹)'
    )
    
    def clean(self):
        """Validate scenario parameters"""
        cleaned_data = super().clean()
        
        # Check if at least one parameter is specified
        params = [
            'target_credit_utilization', 'target_on_time_percentage',
            'new_accounts_to_add', 'accounts_to_close', 'debt_reduction_amount'
        ]
        
        if not any(cleaned_data.get(param) for param in params):
            raise ValidationError('Please specify at least one scenario parameter')
        
        return cleaned_data

# ==================== RECOMMENDATION FORMS ====================

class RecommendationForm(forms.ModelForm):
    """Form for creating custom recommendations"""
    
    class Meta:
        model = CibilRecommendation
        fields = [
            'recommendation_type', 'title', 'description', 
            'priority', 'potential_score_impact', 'estimated_timeline'
        ]
        widgets = {
            'recommendation_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief title for the recommendation'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed description of the recommendation'
            }),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'potential_score_impact': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100,
                'placeholder': 'Estimated score improvement points'
            }),
            'estimated_timeline': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 3-6 months, 1 year'
            }),
        }

class RecommendationCompletionForm(forms.Form):
    """Form for marking recommendations as completed"""
    
    user_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about how you completed this recommendation'
        }),
        label='Completion Notes'
    )

# ==================== INQUIRY FORMS ====================

class CreditInquiryForm(forms.ModelForm):
    """Form for adding credit inquiries"""
    
    class Meta:
        model = CreditInquiry
        fields = [
            'inquiry_type', 'inquiry_purpose', 'inquiring_entity',
            'inquiry_date', 'inquiry_amount'
        ]
        widgets = {
            'inquiry_type': forms.Select(attrs={'class': 'form-control'}),
            'inquiry_purpose': forms.Select(attrs={'class': 'form-control'}),
            'inquiring_entity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank or lender name'
            }),
            'inquiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': date.today().strftime('%Y-%m-%d')
            }),
            'inquiry_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01,
                'placeholder': 'Amount applied for (optional)'
            }),
        }
        labels = {
            'inquiry_type': 'Inquiry Type *',
            'inquiry_purpose': 'Purpose *',
            'inquiring_entity': 'Bank/Lender *',
            'inquiry_date': 'Inquiry Date *',
            'inquiry_amount': 'Applied Amount (₹)',
        }

# ==================== SETTINGS FORMS ====================

class AlertSettingsForm(forms.ModelForm):
    """Form for managing alert preferences"""
    
    class Meta:
        model = AlertSettings
        fields = [
            'email_score_updates', 'email_payment_reminders', 
            'email_recommendations', 'email_monthly_summary',
            'sms_score_updates', 'sms_payment_reminders',
            'app_score_updates', 'app_payment_reminders', 'app_recommendations'
        ]
        widgets = {
            'email_score_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_payment_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_recommendations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_monthly_summary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_score_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_payment_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_score_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_payment_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_recommendations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'email_score_updates': 'Email me when my CIBIL score changes',
            'email_payment_reminders': 'Email payment due reminders',
            'email_recommendations': 'Email new recommendations',
            'email_monthly_summary': 'Email monthly credit summary',
            'sms_score_updates': 'SMS me when my CIBIL score changes',
            'sms_payment_reminders': 'SMS payment due reminders',
            'app_score_updates': 'Push notifications for score changes',
            'app_payment_reminders': 'Push notifications for payment reminders',
            'app_recommendations': 'Push notifications for new recommendations',
        }

# ==================== SEARCH AND FILTER FORMS ====================

class AccountFilterForm(forms.Form):
    """Form for filtering credit accounts"""
    
    account_type = forms.ChoiceField(
        choices=[('all', 'All Types')] + list(CreditAccount.ACCOUNT_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('all', 'All Status')] + list(CreditAccount.ACCOUNT_STATUS),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    bank_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by bank name'
        })
    )

class PaymentFilterForm(forms.Form):
    """Form for filtering payment history"""
    
    payment_status = forms.ChoiceField(
        choices=[('all', 'All Status')] + list(PaymentHistory.PAYMENT_STATUS),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError('Start date must be before end date')
        
        return cleaned_data

# ==================== USER REGISTRATION FORM ====================

class CustomUserCreationForm(UserCreationForm):
    """Extended user creation form with additional fields"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add password validation messages
        self.fields['password1'].help_text = 'Your password must contain at least 8 characters.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    
    def clean_email(self):
        """Validate unique email"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email
    
    def save(self, commit=True):
        """Save user with additional fields"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
        
        return user

# In your views.py when using forms:
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def create_profile(request):
    # Your view logic here
    pass