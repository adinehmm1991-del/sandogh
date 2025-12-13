from django.urls import path
from .views import (
    TransactionListCreateView, 
    CalculateProfitView, 
    UserDashboardView, 
    GeneralReportView,
    WithdrawalRequestListCreateView  # <--- این ایمپورت باید باشد
)

urlpatterns = [
    path('transactions/', TransactionListCreateView.as_view(), name='transaction-list-create'),
    path('calculate-profit/<int:period_id>/', CalculateProfitView.as_view(), name='calculate-profit'),
    path('dashboard/', UserDashboardView.as_view(), name='user-dashboard'),
    path('general-report/', GeneralReportView.as_view(), name='general-report'),
    
    # --- این خط قبلاً جا افتاده بود ---
    path('withdrawals/', WithdrawalRequestListCreateView.as_view(), name='withdrawal-list-create'),
]