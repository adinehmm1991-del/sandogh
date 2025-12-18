from django.contrib import admin
from django.contrib import messages
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
import jdatetime

from .models import (
    Transaction, 
    ProfitPeriod, 
    ProfitDistribution, 
    WithdrawalRequest, 
    LoanRequest, 
    PointLog, 
    PointTransferRequest
)
from users.models import User

# --- تنظیمات خروجی اکسل تراکنش‌ها (حل مشکل مغایرت) ---
class TransactionResource(resources.ModelResource):
    # نمایش نام کاربر به جای ID در فایل اکسل
    user = fields.Field(
        column_name='نام کاربر',
        attribute='user',
        widget=ForeignKeyWidget(User, 'full_name')
    )
    # ستون اختصاصی تاریخ شمسی برای اکسل
    shamsi_date = fields.Field(column_name='تاریخ شمسی')
    # ستون اختصاصی نوع تراکنش فارسی
    farsi_type = fields.Field(column_name='نوع تراکنش')

    class Meta:
        model = Transaction
        fields = ('id', 'user', 'amount', 'farsi_type', 'is_verified', 'description', 'shamsi_date', 'bank_tracking_code')
        export_order = ('id', 'user', 'amount', 'farsi_type', 'is_verified', 'shamsi_date', 'description')

    def dehydrate_shamsi_date(self, transaction):
        if transaction.date:
            return jdatetime.datetime.fromgregorian(datetime=transaction.date).strftime('%Y/%m/%d')
        return "-"

    def dehydrate_farsi_type(self, transaction):
        return transaction.get_transaction_type_display()


# 1. مدیریت تراکنش‌ها (ترکیب قابلیت اکسل + ظاهر زیبا)
@admin.register(Transaction)
class TransactionAdmin(ImportExportModelAdmin):
    resource_class = TransactionResource
    list_display = ('user', 'amount_display', 'type_farsi', 'date_jalali', 'is_verified_icon')
    list_filter = ('is_verified', 'transaction_type', 'date', 'profit_period')
    search_fields = ('user__full_name', 'user__phone_number', 'amount', 'description', 'bank_tracking_code')
    ordering = ('-date',)

    @admin.display(description='مبلغ (تومان)')
    def amount_display(self, obj):
        return f"{obj.amount:,}"

    @admin.display(description='نوع تراکنش')
    def type_farsi(self, obj):
        return obj.get_transaction_type_display()

    @admin.display(description='تاریخ')
    def date_jalali(self, obj):
        if obj.date:
            return jdatetime.datetime.fromgregorian(datetime=obj.date).strftime("%Y/%m/%d | %H:%M")
        return "-"

    @admin.display(description='وضعیت')
    def is_verified_icon(self, obj):
        return "✅ تایید شده" if obj.is_verified else "❌ تایید نشده"


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


# 4. درخواست‌های برداشت (حفظ قابلیت ویرایش سریع)
@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'source_type', 'status', 'created_at_jalali')
    list_filter = ('status', 'source_type')
    list_editable = ('status',)  # حفظ شد: امکان تغییر وضعیت مستقیم
    search_fields = ('user__full_name',)

    @admin.display(description='مبلغ')
    def amount_display(self, obj):
        return f"{obj.amount:,}"
    
    @admin.display(description='تاریخ درخواست')
    def created_at_jalali(self, obj):
        return jdatetime.datetime.fromgregorian(datetime=obj.created_at).strftime("%Y/%m/%d")


# 5. درخواست‌های وام (حفظ قابلیت ویرایش امتیاز)
@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'status', 'points_cost', 'created_at_jalali')
    list_filter = ('status',)
    list_editable = ('status', 'points_cost') # حفظ شد: مدیر می‌تواند امتیاز کسر شده را همینجا وارد کند

    @admin.display(description='مبلغ وام')
    def amount_display(self, obj):
        return f"{obj.amount:,}"

    @admin.display(description='تاریخ')
    def created_at_jalali(self, obj):
        return jdatetime.datetime.fromgregorian(datetime=obj.created_at).strftime("%Y/%m/%d")


# 6. سوابق امتیاز
@admin.register(PointLog)
class PointLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'log_type', 'related_user', 'created_at_jalali')
    list_filter = ('log_type',)
    search_fields = ('user__full_name',)

    @admin.display(description='تاریخ')
    def created_at_jalali(self, obj):
        return jdatetime.datetime.fromgregorian(datetime=obj.created_at).strftime("%Y/%m/%d")


# 7. درخواست انتقال امتیاز (حفظ قابلیت تایید گروهی)
@admin.register(PointTransferRequest)
class PointTransferRequestAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'amount', 'status', 'created_at_jalali')
    list_filter = ('status',)
    actions = ['approve_requests', 'reject_requests'] # حفظ شد

    @admin.display(description='تاریخ')
    def created_at_jalali(self, obj):
        return jdatetime.datetime.fromgregorian(datetime=obj.created_at).strftime("%Y/%m/%d")

    @admin.action(description='✅ تایید درخواست‌های انتخاب شده')
    def approve_requests(self, request, queryset):
        for req in queryset:
            if req.status == 'PENDING':
                req.status = 'APPROVED'
                req.save() # بسیار مهم: این save باعث اجرای لاگ و پیامک می‌شود
        self.message_user(request, "موارد انتخاب شده تایید و اعمال شدند.", messages.SUCCESS)

    @admin.action(description='❌ رد درخواست‌های انتخاب شده')
    def reject_requests(self, request, queryset):
        # برای رد کردن، نیازی به لاگ امتیاز نیست، پس update کافیست
        # اما اگر بخواهید پیامک رد شدن برود، باید حلقه for بگذارید
        queryset.update(status='REJECTED')
        self.message_user(request, "موارد انتخاب شده رد شدند.", messages.WARNING)