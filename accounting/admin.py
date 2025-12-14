from django.contrib import admin
from .models import Transaction, ProfitPeriod, ProfitDistribution, WithdrawalRequest, LoanRequest, PointLog, PointTransferRequest
from django.contrib import messages

# 1. مدیریت تراکنش‌ها
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'transaction_type', 'date_jalali', 'is_verified')
    list_filter = ('transaction_type', 'is_verified', 'date')
    search_fields = ('user__full_name', 'user__phone_number', 'amount')
    ordering = ('-date',)

    @admin.display(description='مبلغ (تومان)')
    def amount_display(self, obj):
        return f"{obj.amount:,}"

    @admin.display(description='تاریخ')
    def date_jalali(self, obj):
        return obj.date.strftime("%Y/%m/%d | %H:%M")

# 2. مدیریت دوره‌های سود
@admin.register(ProfitPeriod)
class ProfitPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'total_profit_display', 'is_calculated')
    
    @admin.display(description='سود کل')
    def total_profit_display(self, obj):
        return f"{obj.total_profit_amount:,}"

# 3. مدیریت توزیع سود
@admin.register(ProfitDistribution)
class ProfitDistributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'period', 'calculated_score', 'profit_amount_display')
    list_filter = ('period',)
    
    @admin.display(description='سود واریزی')
    def profit_amount_display(self, obj):
        return f"{obj.profit_amount:,}"

# 4. درخواست‌های برداشت (با قابلیت تایید سریع)
@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'source_type', 'status', 'created_at_jalali')
    list_filter = ('status', 'source_type')
    list_editable = ('status',)  # امکان تغییر وضعیت مستقیم از لیست
    search_fields = ('user__full_name',)

    @admin.display(description='مبلغ')
    def amount_display(self, obj):
        return f"{obj.amount:,}"
    
    @admin.display(description='تاریخ درخواست')
    def created_at_jalali(self, obj):
        return obj.created_at.strftime("%Y/%m/%d")

# 5. درخواست‌های وام (جدید)
@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'status', 'points_cost', 'created_at')
    list_filter = ('status',)
    list_editable = ('status', 'points_cost') # مدیر می‌تواند امتیاز کسر شده را همینجا وارد کند

    @admin.display(description='مبلغ وام')
    def amount_display(self, obj):
        return f"{obj.amount:,}"

# 6. سوابق امتیاز (Log)
@admin.register(PointLog)
class PointLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'log_type', 'related_user', 'created_at')
    list_filter = ('log_type',)
    search_fields = ('user__full_name',)

# 7. درخواست انتقال امتیاز (جدید)
@admin.register(PointTransferRequest)
class PointTransferRequestAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    actions = ['approve_requests', 'reject_requests']

    @admin.action(description='✅ تایید درخواست‌های انتخاب شده')
    def approve_requests(self, request, queryset):
        for req in queryset:
            if req.status == 'PENDING':
                req.status = 'APPROVED'
                req.save() # متد save مدل صدا زده می‌شود و انتقال انجام می‌شود
        self.message_user(request, "موارد انتخاب شده تایید و اعمال شدند.", messages.SUCCESS)

    @admin.action(description='❌ رد درخواست‌های انتخاب شده')
    def reject_requests(self, request, queryset):
        queryset.update(status='REJECTED')
        self.message_user(request, "موارد انتخاب شده رد شدند.", messages.WARNING)