from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Sum
from django.http import HttpResponse
from jalali_date.admin import ModelAdminJalaliMixin, TabularInlineJalaliMixin
from .models import User
from .forms import UserCreationForm
import openpyxl
import datetime 

# --- 1. نمایش لیست تراکنش‌ها در پایین پروفایل ---
class TransactionInline(TabularInlineJalaliMixin, admin.TabularInline):
    from accounting.models import Transaction
    model = Transaction
    fields = ('amount', 'transaction_type', 'date', 'is_verified', 'description')
    readonly_fields = ('date',)
    extra = 0
    ordering = ('-date',)
    verbose_name = "تراکنش"
    verbose_name_plural = "📄 لیست تراکنش‌های مالی"
    
    def has_add_permission(self, request, obj): return False

# --- تابع خروجی اکسل ---
@admin.action(description='📥 دانلود خروجی اکسل کامل')
def export_users_to_excel(modeladmin, request, queryset):
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename=Full_Export_{datetime.datetime.now().strftime("%Y-%m-%d")}.xlsx'
    workbook = openpyxl.Workbook()
    
    ws_users = workbook.active
    ws_users.title = 'لیست اعضا'
    ws_users.sheet_view.rightToLeft = True
    ws_users.append(['کد عضویت', 'نام', 'موبایل', 'کد ملی', 'نقش', 'تعهد ماهیانه', 'وضعیت'])

    for user in queryset:
        from accounting.models import Transaction
        has_paid = Transaction.objects.filter(user=user, transaction_type='FEE', is_verified=True).exists()
        status = "فعال" if has_paid else "غیرفعال"
        ws_users.append([
            user.membership_code, user.full_name, user.phone_number, user.national_code,
            user.get_role_display(), user.monthly_commitment, status
        ])

    ws_trans = workbook.create_sheet(title='ریز تراکنش‌ها')
    ws_trans.sheet_view.rightToLeft = True
    ws_trans.append(['نام عضو', 'نوع', 'مبلغ', 'تاریخ', 'وضعیت'])
    
    from accounting.models import Transaction
    transactions = Transaction.objects.filter(user__in=queryset).order_by('-date')
    for t in transactions:
        t_date = t.date.strftime('%Y/%m/%d') if t.date else '-'
        ws_trans.append([t.user.full_name, t.get_transaction_type_display(), t.amount, t_date, t.is_verified])

    workbook.save(response)
    return response


# --- تنظیمات اصلی پنل کاربر ---
@admin.register(User)
class UserAdmin(ModelAdminJalaliMixin, BaseUserAdmin):
    add_form = UserCreationForm
    actions = [export_users_to_excel]
    inlines = [TransactionInline]

    # لیست ستون‌های جدول کاربران (موبایل اول است)
    list_display = ('phone_number', 'full_name', 'membership_code', 'get_parent_info', 'role', 'is_active_status', 'get_total_balance')
    
    list_filter = ('role', 'is_active', 'gender')
    
    # جستجو بر اساس موبایل و نام
    search_fields = ('phone_number', 'full_name', 'membership_code', 'national_code')
    
    # مرتب‌سازی بر اساس موبایل
    ordering = ('phone_number',)
    
    readonly_fields = (
        'membership_code', 'last_login', 'date_joined','parent',
        'get_total_balance', 'get_profit_saving', 'get_loan_saving', 
        'get_donations', 'get_referrals_count', 'get_fee_status',
        'get_loan_points_savings', 'get_loan_points_donation', 'get_loan_points_referral',
        'get_loan_wait_status'
    )

    # فرم افزودن کاربر جدید (توسط مدیر)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'password', 'confirm_password'),
        }),
    )

    # فرم ویرایش کاربر
    fieldsets = (
        ('📊 خلاصه وضعیت مالی و عملکرد', {
            'fields': (
                ('get_total_balance', 'get_fee_status'),
                ('get_profit_saving', 'get_loan_saving'),
                ('get_donations', 'get_referrals_count'),
                ('get_loan_points_savings', 'get_loan_points_donation', 'get_loan_points_referral'),
                ('get_loan_wait_status',) 
            ),
            'classes': ('collapse', 'open'),
        }),
        (None, {'fields': ('phone_number', 'password')}), # موبایل به عنوان نام کاربری
        ('اطلاعات شخصی', {'fields': ('full_name', 'national_code', 'gender', 'birth_date', 'social_id')}),
        ('اطلاعات حساب', {'fields': ('role', 'membership_code', 'referral_code')}),
        ('اطلاعات مالی و بانکی', {'fields': ('card_number', 'shaba_number', 'monthly_commitment')}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('تاریخچه‌ها', {'fields': ('last_login', 'date_joined')}),
    )

    # --- توابع محاسباتی ---

    def get_sum(self, user, types):
        from accounting.models import Transaction
        return Transaction.objects.filter(user=user, transaction_type__in=types, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0

    def get_total_balance(self, obj):
        deposit_types = ['MONTHLY', 'PROFIT_SAVING', 'LOAN_SAVING', 'QARD', 'FEE']
        deposits = self.get_sum(obj, deposit_types)
        withdrawals = self.get_sum(obj, ['WITHDRAWAL'])
        
        extra = 0
        if obj.role == 'FUND_ACCOUNT':
             from accounting.models import Transaction
             extra = Transaction.objects.filter(transaction_type='DONATION', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0

        balance = (deposits + extra) - withdrawals
        return f"{balance:,} تومان"
    get_total_balance.short_description = "موجودی کل قابل برداشت"

    def get_profit_saving(self, obj):
        return f"{self.get_sum(obj, ['PROFIT_SAVING']):,} تومان"
    get_profit_saving.short_description = "پس‌انداز سود"

    def get_loan_saving(self, obj):
        return f"{self.get_sum(obj, ['LOAN_SAVING']):,} تومان"
    get_loan_saving.short_description = "پس‌انداز وام (اصل پول)"

    def get_donations(self, obj):
        return f"{self.get_sum(obj, ['DONATION']):,} تومان"
    get_donations.short_description = "کمک‌های بلاعوض"

    def get_referrals_count(self, obj):
        count = User.objects.filter(referral_code=obj.membership_code).count()
        return f"{count} نفر"
    get_referrals_count.short_description = "تعداد معرفی"

    def get_fee_status(self, obj):
        from accounting.models import Transaction
        has_paid = Transaction.objects.filter(user=obj, transaction_type='FEE', is_verified=True).exists()
        return "✅ پرداخت شده" if has_paid else "❌ پرداخت نشده"
    get_fee_status.short_description = "حق عضویت"

    def get_loan_points_savings(self, obj):
        from accounting.models import Transaction
        today = datetime.date.today()
        transactions = Transaction.objects.filter(user=obj, transaction_type='LOAN_SAVING', is_verified=True)
        total_points = 0
        for t in transactions:
            days = (today - t.effective_date).days
            if days > 0:
                # فرمول: مبلغ * 0.006 * روز (طبق درخواست جدید شما 6000 تومان شد)
                # اگر هنوز 7000 است، عدد 6000 را به 7000 تغییر دهید
                score = (t.amount / 1000000) * 6000 * days 
                total_points += int(score)
        return f"{total_points:,} تومان"
    get_loan_points_savings.short_description = "امتیاز وام (سپرده)"

    def get_loan_points_donation(self, obj):
        amount = self.get_sum(obj, ['DONATION'])
        points = int(amount * 0.20)
        return f"{points:,} تومان"
    get_loan_points_donation.short_description = "امتیاز وام (بلاعوض)"

    def get_loan_points_referral(self, obj):
        from accounting.models import Transaction
        referrals = User.objects.filter(referral_code=obj.membership_code).values_list('id', flat=True)
        active_count = Transaction.objects.filter(
            user_id__in=referrals, transaction_type='FEE', is_verified=True
        ).values('user').distinct().count()
        
        points = (active_count // 5) * 1000000
        return f"{points:,} تومان ({active_count} فعال)"
    get_loan_points_referral.short_description = "امتیاز وام (معرف)"

    def get_loan_wait_status(self, obj):
        from accounting.models import Transaction
        first_loan_trans = Transaction.objects.filter(
            user=obj, transaction_type='LOAN_SAVING', is_verified=True
        ).order_by('effective_date').first()

        if not first_loan_trans:
            return "--- (بدون پس‌انداز وام)"
            
        today = datetime.date.today()
        days_passed = (today - first_loan_trans.effective_date).days
        
        # تغییر بازه زمانی به ۳ ماه (۹۰ روز) طبق درخواست جدید
        WAIT_DAYS = 90 
        
        if days_passed >= WAIT_DAYS:
            return f"✅ دوره تکمیل شد ({days_passed} روز گذشته)"
        else:
            remaining = WAIT_DAYS - days_passed
            return f"⏳ در انتظار ({days_passed} روز گذشته - {remaining} روز مانده)"
    get_loan_wait_status.short_description = "وضعیت دوره انتظار"

    def is_active_status(self, obj):
        return self.get_fee_status(obj)
    is_active_status.short_description = "وضعیت"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            form.base_fields['confirm_password'] = form.base_fields.get('password')
        return form
    def get_parent_info(self, obj):
        if obj.parent:
            return f"زیرمجموعه: {obj.parent.full_name} ({obj.parent.membership_code})"
        return "-" # سرپرست ندارد (مستقل)
    get_parent_info.short_description = "وضعیت سرپرستی"
    get_parent_info.admin_order_field = 'parent' # قابلیت سورت