from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('', views.index, name='auth_index'),
    path('landing/', views.landing_page, name='landing'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('signup-success/', views.signup_success, name='signup_success'),
]
