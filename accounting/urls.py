from django.urls import path
from .views import (
    TransactionListCreateView, 
    CalculateProfitView, 
    UserDashboardView, 
    GeneralReportView,
    WithdrawalRequestListCreateView,
    AdminLoanSavingsReportView,
    LoanRequestListCreateView,
    LoanDashboardReportView,
    PointTransferView,
    PointLogListView,
    AdminLoanManagementView,
    AdminLoanDetailView,
    InvestmentDashboardView,
    ExternalInvestmentListCreateView,
    ExternalInvestmentDetailView,
    InvestmentTransactionCreateView,
    SettleInvestmentProfitsView,
    AdminLoanInstallmentsView  # <--- ۱. این کلاس اضافه شد
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

    path('reports/loan-dashboard/', LoanDashboardReportView.as_view(), name='loan-dashboard-report'),
    path('manager/loans/', AdminLoanManagementView.as_view(), name='admin-loan-list'),
    path('manager/loans/<int:pk>/', AdminLoanDetailView.as_view(), name='admin-loan-detail'),
    
    # ---> ۲. جراحی اصلی: این آدرس برای اقساط اضافه شد تا ارور 404 برطرف شود <---
    path('manager/loans/<int:loan_id>/installments/', AdminLoanInstallmentsView.as_view(), name='admin-loan-installments'),
    
    path('manager/loan-savings/', AdminLoanSavingsReportView.as_view(), name='admin-loan-savings'),
    path('manager/investment-dashboard/', InvestmentDashboardView.as_view(), name='investment-dashboard'),
    path('manager/investments/', ExternalInvestmentListCreateView.as_view(), name='investment-list-create'),
    path('manager/investments/<int:pk>/', ExternalInvestmentDetailView.as_view(), name='investment-detail'),
    path('manager/investment-transactions/', InvestmentTransactionCreateView.as_view(), name='investment-transaction-create'),
    path('manager/investment-profits/settle/', SettleInvestmentProfitsView.as_view(), name='investment-profits-settle'),
]