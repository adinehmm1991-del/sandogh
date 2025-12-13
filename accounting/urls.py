from django.urls import path
from .views import (
    TransactionListCreateView, 
    CalculateProfitView, 
    UserDashboardView, 
    GeneralReportView,
    WithdrawalRequestListCreateView,
    # --- کلاس‌های جدید اضافه شدند ---
    LoanRequestListCreateView,
    PointTransferView,
    PointLogListView
)

urlpatterns = [
    # تراکنش‌ها
    path('transactions/', TransactionListCreateView.as_view(), name='transaction-list-create'),
    
    # محاسبه سود
    path('calculate-profit/<int:period_id>/', CalculateProfitView.as_view(), name='calculate-profit'),
    
    # داشبورد و گزارش مدیر
    path('dashboard/', UserDashboardView.as_view(), name='user-dashboard'),
    path('general-report/', GeneralReportView.as_view(), name='general-report'),
    
    # درخواست برداشت
    path('withdrawals/', WithdrawalRequestListCreateView.as_view(), name='withdrawal-list-create'),

    # --- آدرس‌های جدید ---
    
    # 1. درخواست وام
    path('loans/', LoanRequestListCreateView.as_view(), name='loan-list-create'),
    
    # 2. انتقال امتیاز
    path('points/transfer/', PointTransferView.as_view(), name='point-transfer'),
    
    # 3. سوابق امتیاز (تاریخچه)
    path('points/logs/', PointLogListView.as_view(), name='point-logs'),
]