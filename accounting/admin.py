from django.contrib import admin
from django.contrib import messages
from django import forms
from django.utils import timezone
from jalali_date.admin import ModelAdminJalaliMixin
import datetime
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
import jdatetime
from django.db.models import Sum
from .models import ProfitRate
from .models import (
    Transaction, 
    ProfitPeriod, 
    ProfitDistribution, 
    WithdrawalRequest, 
    LoanRequest,
    FundProfitAllocation, 
    PointLog, 
    PointTransferRequest
)
from users.models import User

# --- فرم اختصاصی برای وارد کردن مبالغ با کاما (بهینه‌شده و ضد ارور) ---
class TransactionAdminForm(forms.ModelForm):
    amount = forms.CharField(
        label="مبلغ (تومان)",
        widget=forms.TextInput(attrs={
            'class': 'vTextField', 
            'dir': 'ltr',
            'inputmode': 'numeric',
            'placeholder': 'مثال: 10,000,000',
            'oninput': """
                let value = this.value.replace(/\\D/g, '');
                if (value) {
                    let cursor = this.selectionStart;
                    let oldLen = this.value.length;
                    this.value = Number(value).toLocaleString('en-US');
                    let newLen = this.value.length;
                    this.setSelectionRange(cursor + (newLen - oldLen), cursor + (newLen - oldLen));
                } else {
                    this.value = '';
                }
            """
        })
    )

    class Meta:
        model = Transaction
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.amount:
            self.initial['amount'] = f"{self.instance.amount:,}"

    def clean_amount(self):
        val = self.cleaned_data.get('amount', '')
        # تبدیل اعداد فارسی به انگلیسی و حذف کاماها (جلوگیری از ارور ثبت دستی)
        persian_digits = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        val = str(val).translate(persian_digits).replace(',', '').strip()
        try:
            return int(val)
        except ValueError:
            raise forms.ValidationError("مبلغ وارد شده نامعتبر است. لطفاً فقط از اعداد استفاده کنید.")

# --- تنظیمات خروجی اکسل ---
class TransactionResource(resources.ModelResource):
    user = fields.Field(column_name='نام کاربر', attribute='user', widget=ForeignKeyWidget(User, 'full_name'))
    shamsi_date = fields.Field(column_name='تاریخ شمسی')
    farsi_type = fields.Field(column_name='نوع تراکنش')

    class Meta:
        model = Transaction
        fields = ('id', 'user', 'amount', 'farsi_type', 'is_verified', 'description', 'shamsi_date', 'bank_tracking_code')
        export_order = ('id', 'user', 'amount', 'farsi_type', 'is_verified', 'shamsi_date', 'description')

    def dehydrate_shamsi_date(self, transaction):
        if transaction.date:
            local_date = timezone.localtime(transaction.date)
            return jdatetime.datetime.fromgregorian(datetime=local_date).strftime('%Y/%m/%d | %H:%M')
        return "-"
    
    def dehydrate_farsi_type(self, transaction):
        return transaction.get_transaction_type_display()

@admin.register(Transaction)
class TransactionAdmin(ModelAdminJalaliMixin, ImportExportModelAdmin):
    resource_class = TransactionResource
    form = TransactionAdminForm
    list_display = ('user', 'amount_display', 'type_farsi', 'date_jalali', 'is_verified_icon')
    list_filter = ('is_verified', 'transaction_type', 'date') 
    search_fields = ('user__full_name', 'user__phone_number', 'amount', 'description', 'bank_tracking_code')
    autocomplete_fields = ['user']
    ordering = ('-date',)
    exclude = ('profit_period', 'gateway_name') 
    readonly_fields = ('effective_date',)       

    @admin.display(description='مبلغ (تومان)')
    def amount_display(self, obj): return f"{obj.amount:,}"
    @admin.display(description='نوع تراکنش')
    def type_farsi(self, obj): return obj.get_transaction_type_display()
    @admin.display(description='تاریخ')
    def date_jalali(self, obj):
        if obj.date:
            local_date = timezone.localtime(obj.date)
            return jdatetime.datetime.fromgregorian(datetime=local_date).strftime("%Y/%m/%d | %H:%M")
        return "-"
    @admin.display(description='وضعیت')
    def is_verified_icon(self, obj): return "✅ تایید شده" if obj.is_verified else "❌ تایید نشده"

@admin.register(ProfitPeriod)
class ProfitPeriodAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'total_profit_display', 'is_calculated')
    actions = ['export_paid_profits_report', 'distribute_yearly_profit']
    
    @admin.display(description='مبلغ کل سود سالیانه (ثبت شده)')
    def total_profit_display(self, obj): return f"{obj.total_profit_amount:,} تومان"

    @admin.action(description='📊 ۱. گزارش جمع سودهای علی‌الحساب پرداختی در این دوره (اکسل)')
    def export_paid_profits_report(self, request, queryset):
        import csv
        from django.http import HttpResponse

        if queryset.count() != 1:
            self.message_user(request, "لطفاً فقط یک دوره را انتخاب کنید.", messages.ERROR)
            return
        period = queryset.first()
        profits = Transaction.objects.filter(
            transaction_type='MANUAL_PROFIT', effective_date__gte=period.start_date,
            effective_date__lte=period.end_date, is_verified=True
        ).exclude(description__contains='سالیانه') 

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Paid_Profits_Report_{period.name}.csv"'
        response.write('\ufeff'.encode('utf8')) 
        writer = csv.writer(response)
        writer.writerow(['شرح / ماه', 'مبلغ پرداختی (تومان)'])

        monthly_totals = {}
        grand_total = 0
        for p in profits:
            desc = p.description or "سودهای متفرقه"
            if desc not in monthly_totals: monthly_totals[desc] = 0
            monthly_totals[desc] += p.amount
            grand_total += p.amount

        for desc, amount in monthly_totals.items():
            writer.writerow([desc, amount])

        writer.writerow(['----------------', '------'])
        writer.writerow(['جمع کل سودهای پرداخت شده', grand_total])
        return response

    @admin.action(description='🏆 ۲. تقسیم سود قطعی سالیانه (با دقت روزشمار در طول دوره)')
    def distribute_yearly_profit(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "لطفاً فقط یک دوره را انتخاب کنید.", messages.ERROR)
            return

        period = queryset.first()
        if period.is_calculated:
            self.message_user(request, "خطا: سود این دوره قبلاً محاسبه و تقسیم شده است!", messages.ERROR)
            return

        total_profit = period.total_profit_amount
        if total_profit <= 0:
            self.message_user(request, "خطا: مبلغ سود باقیمانده برای این دوره صفر است.", messages.ERROR)
            return

        users_share = int(total_profit * 0.80)
        fund_share = int(total_profit * 0.20)

        start_date_g = period.start_date
        end_date_g = period.end_date
        days_in_period = (end_date_g - start_date_g).days + 1

        users = User.objects.exclude(role='FUND_ACCOUNT')
        fund_account = User.objects.filter(role='FUND_ACCOUNT').first()

        st_dep_types = ['SHORT_TERM']
        st_wit_types = ['W_SHORT']
        lt_dep_types = ['LONG_TERM', 'MONTHLY', 'PROFIT_SAVING', 'MANUAL_PROFIT', 'SADAQAH', 'WAQF', 'SACRIFICE', 'BOOK', 'KHOMS_IMAM', 'KHOMS_SADAT']
        lt_wit_types = ['W_LONG', 'W_MONTHLY', 'W_PROFIT', 'W_MAN_PROFIT', 'WITHDRAWAL_OTHER', 'WITHDRAWAL', 'W_CULTURAL']
        non_dep_types = ['LOAN_SAVING', 'QARD', 'FEE']
        non_wit_types = ['W_SAVING', 'W_QARD', 'W_FEE']

        user_eligible_points = {}
        total_eligible_points = 0
        total_non_eligible_points = 0

        for user in users:
            def get_daily_points(dep_types, wit_types):
                dep_before = Transaction.objects.filter(user=user, transaction_type__in=dep_types, effective_date__lt=start_date_g, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
                wit_before = Transaction.objects.filter(user=user, transaction_type__in=wit_types, effective_date__lt=start_date_g, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
                current_bal = max(0, dep_before - wit_before)
                total_pts = 0
                trans_this_period = Transaction.objects.filter(user=user, transaction_type__in=dep_types + wit_types, effective_date__gte=start_date_g, effective_date__lte=end_date_g, is_verified=True).order_by('effective_date')
                daily_changes = {}
                for t in trans_this_period:
                    d = t.effective_date
                    daily_changes[d] = daily_changes.get(d, 0) + (t.amount if t.transaction_type in dep_types else -t.amount)
                for day_offset in range(days_in_period):
                    current_day_g = start_date_g + datetime.timedelta(days=day_offset)
                    if current_day_g in daily_changes:
                        current_bal = max(0, current_bal + daily_changes[current_day_g])
                    total_pts += (current_bal // 1000000) * 1000000
                return total_pts

            st_points = get_daily_points(st_dep_types, st_wit_types)
            lt_points = get_daily_points(lt_dep_types, lt_wit_types)
            non_points = get_daily_points(non_dep_types, non_wit_types)

            eligible_pts = st_points + lt_points
            if eligible_pts > 0:
                user_eligible_points[user.id] = eligible_pts
                total_eligible_points += eligible_pts
            total_non_eligible_points += non_points

        grand_total_points = total_eligible_points + total_non_eligible_points
        distributed_to_users = 0

        if grand_total_points > 0:
            for uid, pts in user_eligible_points.items():
                user_obj = User.objects.get(id=uid)
                share = int((pts / grand_total_points) * users_share)
                if share > 0:
                    ProfitDistribution.objects.create(period=period, user=user_obj, calculated_score=pts, profit_amount=share)
                    Transaction.objects.create(
                        user=user_obj, amount=share, transaction_type='MANUAL_PROFIT',
                        date=timezone.now(), effective_date=end_date_g, is_verified=True,
                        description=f"سود قطعی سالیانه (دوره {period.name})", profit_period=period
                    )
                    distributed_to_users += share

        final_fund_share = (users_share - distributed_to_users) + fund_share

        if fund_account and final_fund_share > 0:
            ProfitDistribution.objects.create(period=period, user=fund_account, calculated_score=total_non_eligible_points, profit_amount=final_fund_share)
            Transaction.objects.create(
                user=fund_account, amount=final_fund_share, transaction_type='MANUAL_PROFIT',
                date=timezone.now(), effective_date=end_date_g, is_verified=True,
                description=f"سهم ۲۰٪ + رسوب غیرمشمول‌ها از سود سالیانه (دوره {period.name})", profit_period=period
            )
            
            # --- محاسبه هوشمند سهم وام در سود سالیانه ---
            def get_balance(dep_types, wit_types):
                dep = Transaction.objects.filter(effective_date__lte=end_date_g, transaction_type__in=dep_types, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
                wit = Transaction.objects.filter(effective_date__lte=end_date_g, transaction_type__in=wit_types, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
                return max(0, dep - wit)

            loan_cap = get_balance(['LOAN_SAVING'], ['W_SAVING'])
            qard_cap = get_balance(['QARD'], ['W_QARD'])
            fee_cap = get_balance(['FEE'], ['W_FEE'])
            total_cap = loan_cap + qard_cap + fee_cap
            
            loan_share = int((loan_cap / total_cap) * final_fund_share) if total_cap > 0 else 0
            qard_share = int((qard_cap / total_cap) * final_fund_share) if total_cap > 0 else 0

            FundProfitAllocation.objects.update_or_create(
                date=end_date_g,
                defaults={
                    'total_profit': final_fund_share,
                    'loan_saving_share': loan_share,
                    'qard_share': qard_share,
                    'short_term_share': 0, 'long_term_share': 0,
                    'description': f"تخصیص از سود سالیانه دوره {period.name}"
                }
            )

        period.is_calculated = True
        period.save()
        self.message_user(request, f"✅ سود سالیانه محاسبه شد! (مبلغ {distributed_to_users:,} به کاربران و {final_fund_share:,} حق صندوق واریز شد)", messages.SUCCESS)

@admin.register(ProfitDistribution)
class ProfitDistributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'period', 'calculated_score', 'profit_amount_display')
    list_filter = ('period',)
    autocomplete_fields = ('user',)
    @admin.display(description='سود واریزی')
    def profit_amount_display(self, obj): return f"{obj.profit_amount:,}"

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'source_type', 'status', 'created_at_jalali')
    list_filter = ('status', 'source_type')
    list_editable = ('status',)
    search_fields = ('user__full_name', 'user__phone_number')
    autocomplete_fields = ('user',)
    @admin.display(description='مبلغ')
    def amount_display(self, obj): return f"{obj.amount:,}"
    @admin.display(description='تاریخ درخواست')
    def created_at_jalali(self, obj):
        local_date = timezone.localtime(obj.created_at)
        return jdatetime.datetime.fromgregorian(datetime=local_date).strftime("%Y/%m/%d | %H:%M")

@admin.register(PointLog)
class PointLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'log_type', 'related_user', 'created_at_jalali')
    list_filter = ('log_type',)
    search_fields = ('user__full_name',)
    autocomplete_fields = ('user', 'related_user')
    @admin.display(description='تاریخ')
    def created_at_jalali(self, obj):
        local_date = timezone.localtime(obj.created_at)
        return jdatetime.datetime.fromgregorian(datetime=local_date).strftime("%Y/%m/%d | %H:%M")

@admin.register(PointTransferRequest)
class PointTransferRequestAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'amount', 'status', 'created_at_jalali')
    list_filter = ('status',)
    actions = ['approve_requests', 'reject_requests']
    autocomplete_fields = ('sender', 'receiver')
    @admin.display(description='تاریخ')
    def created_at_jalali(self, obj):
        local_date = timezone.localtime(obj.created_at)
        return jdatetime.datetime.fromgregorian(datetime=local_date).strftime("%Y/%m/%d | %H:%M")

    @admin.action(description='✅ تایید درخواست‌های انتخاب شده')
    def approve_requests(self, request, queryset):
        for req in queryset:
            if req.status == 'PENDING':
                req.status = 'APPROVED'
                req.save()
        self.message_user(request, "تایید شد.", messages.SUCCESS)

    @admin.action(description='❌ رد درخواست‌های انتخاب شده')
    def reject_requests(self, request, queryset):
        queryset.update(status='REJECTED')
        self.message_user(request, "رد شد.", messages.WARNING)


# =========================================================
# موتور مرکزی و یکپارچه‌ی محاسبه سود ماهیانه (علی‌الحساب)
# =========================================================
@admin.register(ProfitRate)
class ProfitRateAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('month_year_jalali', 'short_term_percent', 'long_term_percent', 'created_by')
    exclude = ('created_by',)
    actions = ['distribute_monthly_profit', 'preview_monthly_profit_excel']

    @admin.display(description='مربوط به ماه')
    def month_year_jalali(self, obj):
        local_date = timezone.localtime(obj.month_year) if isinstance(obj.month_year, datetime.datetime) else obj.month_year
        return jdatetime.date.fromgregorian(date=local_date).strftime("%B %Y")

    def save_model(self, request, obj, form, change):
        if not obj.pk: obj.created_by = request.user
        if obj.month_year:
            j_date = jdatetime.date.fromgregorian(date=obj.month_year)
            first_day_j = jdatetime.date(j_date.year, j_date.month, 1)
            obj.month_year = first_day_j.togregorian()
        super().save_model(request, obj, form, change)

    def _get_unified_calculation(self, rate_obj):
        """ موتور مرکزی محاسبات که هم برای اکسل و هم برای ثبت واقعی استفاده می‌شود """
        rate_short = float(rate_obj.short_term_percent) / 100.0
        rate_long = float(rate_obj.long_term_percent) / 100.0

        j_date = jdatetime.date.fromgregorian(date=rate_obj.month_year)
        year, month = j_date.year, j_date.month
        days_in_month = 31 if month <= 6 else (30 if month <= 11 else (29 if not j_date.isleap() else 30))

        start_date_g = jdatetime.date(year, month, 1).togregorian()
        end_date_g = jdatetime.date(year, month, days_in_month).togregorian()
        
        daily_rate_short = rate_short / days_in_month
        daily_rate_long = rate_long / days_in_month

        st_dep_types = ['SHORT_TERM']
        st_wit_types = ['W_SHORT']
        # وقف‌های جا افتاده در کد قبلی اضافه شدند
        lt_dep_types = ['LONG_TERM', 'MONTHLY', 'PROFIT_SAVING', 'MANUAL_PROFIT', 'SADAQAH', 'WAQF', 'SACRIFICE', 'BOOK', 'KHOMS_IMAM', 'KHOMS_SADAT', 'WAQF_GEN', 'WAQF_BOOK', 'WAQF_MEDIA', 'WAQF_INFRA']
        lt_wit_types = ['W_LONG', 'W_MONTHLY', 'W_PROFIT', 'W_MAN_PROFIT', 'WITHDRAWAL_OTHER', 'WITHDRAWAL', 'W_CULTURAL']
        non_dep_types = ['LOAN_SAVING', 'QARD', 'FEE']
        non_wit_types = ['W_SAVING', 'W_QARD', 'W_FEE']

        users = User.objects.all()
        results = []

        for user in users:
            has_paid_fee = Transaction.objects.filter(user=user, transaction_type='FEE', is_verified=True).exists()
            is_eligible = has_paid_fee or user.role in ['CULTURAL', 'FUND_ACCOUNT']

            def get_points(dep_types, wit_types):
                dep_before = Transaction.objects.filter(user=user, transaction_type__in=dep_types, effective_date__lt=start_date_g, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
                wit_before = Transaction.objects.filter(user=user, transaction_type__in=wit_types, effective_date__lt=start_date_g, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
                
                current_bal = max(0, dep_before - wit_before)
                exact_pts = 0
                rounded_pts = 0
                
                trans = Transaction.objects.filter(user=user, transaction_type__in=dep_types+wit_types, effective_date__gte=start_date_g, effective_date__lte=end_date_g, is_verified=True).order_by('effective_date')
                daily_changes = {}
                for t in trans:
                    d = t.effective_date
                    daily_changes[d] = daily_changes.get(d, 0) + (t.amount if t.transaction_type in dep_types else -t.amount)
                    
                for day_offset in range(days_in_month):
                    curr_day = start_date_g + datetime.timedelta(days=day_offset)
                    if curr_day in daily_changes:
                        current_bal = max(0, current_bal + daily_changes[curr_day])
                        
                    exact_pts += current_bal
                    rounded_pts += (current_bal // 1000000) * 1000000
                    
                return exact_pts, rounded_pts

            st_exact, st_round = get_points(st_dep_types, st_wit_types)
            lt_exact, lt_round = get_points(lt_dep_types, lt_wit_types)
            non_exact, non_round = get_points(non_dep_types, non_wit_types)

            user_st = 0
            user_lt = 0
            fund_resub = 0

            if user.role == 'FUND_ACCOUNT':
                # سود دقیق حساب صندوق (از محل سرمایه‌های درگیر خودش) به جیب خودش می‌رود و رسوب محاسبه نمی‌شود
                user_st = st_exact * daily_rate_short
                user_lt = (lt_exact + non_exact) * daily_rate_long
            elif user.role == 'CULTURAL':
                # حساب‌های فرهنگی سود دقیقشان را می‌گیرند
                user_st = st_exact * daily_rate_short
                user_lt = (lt_exact + non_exact) * daily_rate_long
            else:
                if is_eligible:
                    # شخص عادی واجد شرایط: مضرب میلیون برای خودش، مابقی برای صندوق
                    user_st = st_round * daily_rate_short
                    user_lt = lt_round * daily_rate_long
                    fund_resub += (st_exact - st_round) * daily_rate_short
                    fund_resub += (lt_exact - lt_round) * daily_rate_long
                else:
                    # شخص فاقد شرایط: کل سودش برای صندوق رسوب می‌شود
                    fund_resub += st_exact * daily_rate_short
                    fund_resub += lt_exact * daily_rate_long
                
                # برای اشخاص عادی، سود حساب‌های غیرشمول (وام، حق عضویت) تماماً رسوبِ صندوق است
                fund_resub += non_exact * daily_rate_long

            user_total = int(user_st) + int(user_lt)
            fund_resub_int = int(fund_resub)

            if user_total > 0 or fund_resub_int > 0:
                results.append({
                    'user': user,
                    'user_st': int(user_st),
                    'user_lt': int(user_lt),
                    'user_total': user_total,
                    'fund_resub': fund_resub_int
                })

        return results, end_date_g

    @admin.action(description='📊 ۲. دریافت فایل اکسل پیش‌نمایش محاسبات سود (بدون واریز)')
    def preview_monthly_profit_excel(self, request, queryset):
        import csv
        from django.http import HttpResponse

        if queryset.count() != 1:
            self.message_user(request, "لطفاً فقط یک نرخ ماهانه را انتخاب کنید.", messages.ERROR)
            return

        rate_obj = queryset.first()
        j_date = jdatetime.date.fromgregorian(date=rate_obj.month_year)
        month_name = j_date.strftime("%B_%Y")

        results, _ = self._get_unified_calculation(rate_obj)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Profit_Preview_{month_name}.csv"'
        response.write('\ufeff'.encode('utf8')) 
        writer = csv.writer(response)
        
        writer.writerow(['ردیف', 'نام و نقش', 'کد عضویت', 'سود کوتاه‌مدت شخص', 'سود بلندمدت شخص', 'جمع سود شخص', 'مبلغ رسوب شده برای صندوق (تومان)'])

        total_st = 0
        total_lt = 0
        total_user = 0
        total_fund_resub = 0
        fund_own_profit = 0

        row_idx = 1
        for r in results:
            u = r['user']
            u_total = r['user_total']
            
            writer.writerow([row_idx, u.full_name, u.membership_code, r['user_st'], r['user_lt'], u_total, r['fund_resub']])
            row_idx += 1

            if u.role == 'FUND_ACCOUNT':
                fund_own_profit += u_total
            else:
                total_st += r['user_st']
                total_lt += r['user_lt']
                total_user += u_total
            
            total_fund_resub += r['fund_resub']

        writer.writerow(['---', '---', '---', '---', '---', '---', '---'])
        writer.writerow(['', 'جمع سودهای پرداختی به اعضا', '', total_st, total_lt, total_user, ''])
        writer.writerow(['', 'سود اختصاصی خود حساب صندوق', '', '', '', fund_own_profit, ''])
        writer.writerow(['', 'جمع مبالغ رسوب شده از اعضا', '', '', '', '', total_fund_resub])
        writer.writerow(['', 'مجموع کل سهم صندوق (خودش + رسوبات)', '', '', '', fund_own_profit + total_fund_resub, ''])
        
        return response

    @admin.action(description='💰 ۱. محاسبه و واریز سود ماهیانه (با مکانیزم رسوب‌گیری منابع صندوق)')
    def distribute_monthly_profit(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "لطفاً فقط یک نرخ ماهانه را انتخاب کنید.", messages.ERROR)
            return

        rate_obj = queryset.first()
        j_date = jdatetime.date.fromgregorian(date=rate_obj.month_year)
        month_name = j_date.strftime("%B %Y")
        desc_text = f"سود علی‌الحساب روزشمار {month_name}"

        if Transaction.objects.filter(transaction_type='MANUAL_PROFIT', description=desc_text).exists():
            self.message_user(request, f"خطا: سود ماه {month_name} قبلاً محاسبه و واریز شده است!", messages.ERROR)
            return

        results, end_date_g = self._get_unified_calculation(rate_obj)
        profit_transaction_date = timezone.make_aware(datetime.datetime.combine(end_date_g, datetime.time(23, 59)))

        transactions_to_create = []
        total_user_profit = 0
        total_fund_resub = 0
        fund_own_profit = 0

        for r in results:
            u = r['user']
            u_total = r['user_total']
            
            if u_total > 0:
                transactions_to_create.append(Transaction(
                    user=u, amount=u_total, transaction_type='MANUAL_PROFIT',
                    date=profit_transaction_date, effective_date=end_date_g,
                    is_verified=True, description=desc_text
                ))
                if u.role == 'FUND_ACCOUNT':
                    fund_own_profit += u_total
                else:
                    total_user_profit += u_total

            total_fund_resub += r['fund_resub']

        if total_fund_resub > 0:
            fund_user = User.objects.filter(role='FUND_ACCOUNT').first()
            if fund_user:
                transactions_to_create.append(Transaction(
                    user=fund_user, amount=total_fund_resub, transaction_type='MANUAL_PROFIT',
                    date=profit_transaction_date, effective_date=end_date_g,
                    is_verified=True, description=f"رسوب منابع خرد و غیرشمول - {desc_text}"
                ))

        if transactions_to_create:
            Transaction.objects.bulk_create(transactions_to_create)

        self.message_user(request, f"✅ موفق: سود {month_name} با موفقیت تقسیم شد. مبلغ {total_user_profit:,} به اعضا، {fund_own_profit:,} به حساب خود صندوق و {total_fund_resub:,} رسوب منابع به حساب صندوق واریز شد.", messages.SUCCESS)

@admin.register(FundProfitAllocation)
class FundProfitAllocationAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_profit', 'loan_saving_share', 'qard_share']
    list_filter = ['date']
    search_fields = ['description']

@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'granted_date', 'duration_months', 'is_manual']
    list_filter = ['status', 'is_manual', 'granted_date']
    search_fields = ['user__phone_number', 'user__full_name']


# =========================================================
# --- فاز ۵: پنل ادمین سرمایه‌گذاری‌های خارج از صندوق ---
# =========================================================
from .models import ExternalInvestment, InvestmentTransaction

class InvestmentTransactionInline(admin.TabularInline):
    model = InvestmentTransaction
    extra = 1

@admin.register(ExternalInvestment)
class ExternalInvestmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'investment_type', 'start_date', 'status']
    list_filter = ['status', 'investment_type']
    search_fields = ['title', 'description']
    inlines = [InvestmentTransactionInline]

@admin.register(InvestmentTransaction)
class InvestmentTransactionAdmin(admin.ModelAdmin):
    list_display = ['investment', 'amount_display', 'transaction_type', 'date']
    list_filter = ['transaction_type', 'date', 'investment']
    search_fields = ['investment__title', 'description']

    @admin.display(description='مبلغ (تومان)')
    def amount_display(self, obj):
        return f"{obj.amount:,}"
    
from .models import LoanInstallment

@admin.register(LoanInstallment)
class LoanInstallmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user_name', 'installment_number', 'amount', 'due_date', 'is_paid', 'paid_date']
    list_filter = ['is_paid', 'due_date']
    search_fields = ['loan__user__full_name', 'loan__user__phone_number', 'loan__user__membership_code']
    list_editable = ['is_paid', 'due_date']

    def get_user_name(self, obj):
        return obj.loan.user.full_name
    get_user_name.short_description = 'وام‌گیرنده'