from django.urls import path
from .views import (
    RegisterView, 
    LoginView, 
    ProfileUpdateView, 
    ForgotPasswordView, 
    ChangePasswordView,
    FamilyMemberView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'), # <--- ویرگول اینجا مهم است
    path('family/', FamilyMemberView.as_view(), name='family-members'),
]