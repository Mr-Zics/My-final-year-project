"""
URL configuration for accounts app.
"""

from django.urls import path
from .views import LoginView, LogoutView, StudentRegisterView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', StudentRegisterView.as_view(), name='register'),
]
