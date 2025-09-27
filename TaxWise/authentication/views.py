from django.shortcuts import render, redirect
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse

def landing_page(request):
    """Main landing page - accessible to everyone"""
    if request.user.is_authenticated:
        return redirect('tax_optimization:home')
    return render(request, 'authentication/landing.html')

def index(request):
    """Home page showing login status"""
    return render(request, 'authentication/index.html')

def login_view(request):
    """Login page with Google OAuth button and email/password form"""
    if request.user.is_authenticated:
        return redirect('tax_optimization:home')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            # Try to authenticate with email as username
            user = authenticate(request, username=email, password=password)
            if not user:
                # Try to find user by email and authenticate with username
                try:
                    user_obj = User.objects.get(email=email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
            
            if user:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                # Redirect to tax optimization after successful login
                next_url = request.GET.get('next', 'tax_optimization:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password. Please try again or use Google OAuth.')
    
    return render(request, 'authentication/login.html')

@login_required
def profile(request):
    """User profile page - only accessible after login"""
    return render(request, 'authentication/profile.html')

def logout_view(request):
    """Logout user and redirect to landing page"""
    logout(request)
    return redirect('landing')

def signup_success(request):
    """Success page after Google OAuth signup"""
    if not request.user.is_authenticated:
        return redirect('landing')
    messages.success(request, f'Welcome to TaxWise, {request.user.first_name or request.user.username}! You can now access the AI tax optimization engine.')
    return redirect('tax_optimization:home')
