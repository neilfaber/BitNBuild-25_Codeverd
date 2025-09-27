from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='auth_index'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
]
