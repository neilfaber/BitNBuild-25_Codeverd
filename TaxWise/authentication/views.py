from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

def index(request):
    """Home page showing login status"""
    return render(request, 'authentication/index.html')

def login_view(request):
    """Login page with Google OAuth button"""
    if request.user.is_authenticated:
        return redirect('profile')
    return render(request, 'authentication/login.html')

@login_required
def profile(request):
    """User profile page - only accessible after login"""
    return render(request, 'authentication/profile.html')

def logout_view(request):
    """Logout user and redirect to home"""
    logout(request)
    return redirect('auth_index')
