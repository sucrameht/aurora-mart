from django.urls import path
from .views import customLoginView, RegisterView, OnboardingView, ChangePasswordView

urlpatterns = [
    path('login/', customLoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]