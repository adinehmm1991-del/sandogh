from django.contrib import admin
from django.utils.html import format_html
from jalali_date.admin import ModelAdminJalaliMixin
from .models import Transaction, ProfitPeriod, ProfitDistribution, WithdrawalRequest

# 1. تنظیمات تراکنش‌ها
@admin.register(Transaction)
class TransactionAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('user', 'get_amount_display', 'get_type_display', 'date', 'is_verified', 'effective_date')
    list_filter = ('transaction_type', 'is_verified', 'date')
    search_fields = ('user__full_name', 'user__phone_number', 'amount')
    ordering = ('-date',)

    readonly_fields = ('profit_period',)

    # نمایش مبلغ با جداکننده
    def get_amount_display(self, obj):
        return f"{obj.amount:,} تومان"
    get_amount_display.short_description = 'مبلغ'
    get_amount_display.admin_order_field = 'amount' # برای اینکه قابلیت سورت کردن حفظ شود

    def get_type_display(self, obj):
        return obj.get_transaction_type_display()
    get_type_display.short_description = 'نوع تراکنش'


# 2. تنظیمات دوره‌های سود
@admin.register(ProfitPeriod)
class ProfitPeriodAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'get_total_profit_display', 'is_calculated', 'calculate_btn')
    
    def get_total_profit_display(self, obj):
        return f"{obj.total_profit_amount:,} تومان"
    get_total_profit_display.short_description = 'کل سود'

    def calculate_btn(self, obj):
        return format_html(
            '<a class="button" href="/api/accounting/calculate-profit/{}/" target="_blank" style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 5px; text-decoration: none;">محاسبه و تقسیم سود</a>',
            obj.id
        )
    calculate_btn.short_description = "عملیات"
    calculate_btn.allow_tags = True


# 3. تنظیمات لیست توزیع سود
@admin.register(ProfitDistribution)
class ProfitDistributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'period', 'calculated_score', 'get_profit_display')
    list_filter = ('period',)
    search_fields = ('user__full_name', 'user__phone_number')

    def get_profit_display(self, obj):
        return f"{obj.profit_amount:,} تومان"
    get_profit_display.short_description = 'سود تعلق گرفته'


# 4. تنظیمات درخواست‌های برداشت
@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('user', 'get_amount_display', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__full_name', 'user__phone_number')
    readonly_fields = ('created_at',)

    def get_amount_display(self, obj):
        return f"{obj.amount:,} تومان"
    get_amount_display.short_description = 'مبلغ درخواستی'