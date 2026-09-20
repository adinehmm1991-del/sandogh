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
# --- فرم اختصاصی برای وارد کردن مبلغ سود با کاما ---
class ProfitPeriodAdminForm(forms.ModelForm):
    total_profit_amount = forms.CharField(
        label="مبلغ کل سود تولید شده در این دوره (تومان)",
        widget=forms.TextInput(attrs={
            'class': 'vTextField', 
            'dir': 'ltr',
            'inputmode': 'numeric',
            'placeholder': 'مثال: 50,000,000',
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
        model = ProfitPeriod
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.total_profit_amount:
            self.initial['total_profit_amount'] = f"{self.instance.total_profit_amount:,}"

    def clean_total_profit_amount(self):
        val = self.cleaned_data.get('total_profit_amount', '')
        persian_digits = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        val = str(val).translate(persian_digits).replace(',', '').strip()
        try:
            return int(val)
        except ValueError:
            return 0

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
    form = ProfitPeriodAdminForm
    list_display = ('name', 'start_date', 'end_date', 'total_profit_display', 'is_calculated')
    actions = ['preview_period_profit_excel', 'distribute_period_profit']
    filter_horizontal = ('included_months',) 

    @admin.display(description='مبلغ کل سود')
    def total_profit_display(self, obj): return f"{obj.total_profit_amount:,} تومان"

    def _get_period_calculation(self, period):
        """ موتور مرکزی محاسبه سود دوره‌ای با تفکیک کامل کوتاه‌مدت و بلندمدت """
        total_profit = period.total_profit_amount
        start_date_g = period.start_date
        end_date_g = period.end_date
        days_in_period = (end_date_g - start_date_g).days + 1

        users = User.objects.exclude(role='FUND_ACCOUNT')
        
        # دسته‌بندی حساب‌ها
        st_types = ['SHORT_TERM']
        st_wit = ['W_SHORT']
        lt_types = ['LONG_TERM', 'MONTHLY', 'PROFIT_SAVING', 'MANUAL_PROFIT', 'SADAQAH', 'WAQF', 'SACRIFICE', 'BOOK', 'KHOMS_IMAM', 'KHOMS_SADAT', 'WAQF_GEN', 'WAQF_BOOK', 'WAQF_MEDIA', 'WAQF_INFRA']
        lt_wit = ['W_LONG', 'W_MONTHLY', 'W_PROFIT', 'W_MAN_PROFIT', 'WITHDRAWAL_OTHER', 'WITHDRAWAL', 'W_CULTURAL']
        loan_types = ['LOAN_SAVING']
        loan_wit = ['W_SAVING']
        qard_fee_types = ['QARD', 'FEE']
        qard_fee_wit = ['W_QARD', 'W_FEE']

        # ۱. استخراج مبالغ علی‌الحساب
        ali_hesab_descriptions = []
        for rate in period.included_months.all():
            j_date = jdatetime.date.fromgregorian(date=rate.month_year)
            month_name = j_date.strftime("%B %Y")
            ali_hesab_descriptions.append(f"سود علی‌الحساب روزشمار {month_name}")

        user_data = []
        total_st_points = 0
        total_lt_points = 0
        total_loan_points = 0
        total_qard_fee_points = 0

        # ۲. محاسبه دقیق امتیازات روزشمار (قدم اول منطق شما)
        for user in users:
            def get_pts(dep_types, wit_types):
                dep_before = Transaction.objects.filter(user=user, transaction_type__in=dep_types, effective_date__lt=start_date_g, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
                wit_before = Transaction.objects.filter(user=user, transaction_type__in=wit_types, effective_date__lt=start_date_g, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
                current_bal = max(0, dep_before - wit_before)
                pts = 0
                trans = Transaction.objects.filter(user=user, transaction_type__in=dep_types+wit_types, effective_date__gte=start_date_g, effective_date__lte=end_date_g, is_verified=True).order_by('effective_date')
                changes = {}
                for t in trans:
                    d = t.effective_date
                    changes[d] = changes.get(d, 0) + (t.amount if t.transaction_type in dep_types else -t.amount)
                for day_offset in range(days_in_period):
                    curr_day = start_date_g + datetime.timedelta(days=day_offset)
                    if curr_day in changes: current_bal = max(0, current_bal + changes[curr_day])
                    # اختصاص امتیاز به ازای هر یک میلیون تومان در هر روز
                    pts += (current_bal // 1000000) * 1000000
                return pts

            st_p = get_pts(st_types, st_wit)
            lt_p = get_pts(lt_types, lt_wit)
            loan_p = get_pts(loan_types, loan_wit)
            qf_p = get_pts(qard_fee_types, qard_fee_wit)
            
            total_st_points += st_p
            total_lt_points += lt_p
            total_loan_points += loan_p
            total_qard_fee_points += qf_p
            
            ali_hesab_paid = 0
            if ali_hesab_descriptions:
                ali_hesab_paid = Transaction.objects.filter(
                    user=user, transaction_type='MANUAL_PROFIT', 
                    description__in=ali_hesab_descriptions, is_verified=True
                ).aggregate(Sum('amount'))['amount__sum'] or 0

            user_data.append({
                'user': user, 'st_p': st_p, 'lt_p': lt_p, 'loan_p': loan_p, 'qf_p': qf_p, 'ali_hesab': ali_hesab_paid
            })

        grand_total_points = total_st_points + total_lt_points + total_loan_points + total_qard_fee_points
        profit_per_point = total_profit / grand_total_points if grand_total_points > 0 else 0

        # ۳. توزیع و اعمال کسر صندوق، علی‌الحساب و تضمین‌ها (قدم دوم، سوم و چهارم)
        results = []
        fund_net_profit_saving = 0 
        
        # ۱۰۰٪ سود وام به پس‌انداز وام صندوق می‌رود
        fund_net_loan_saving = int(total_loan_points * profit_per_point) 
        # ۱۰۰٪ سود سایر حساب‌ها (حق عضویت و...) به سود صندوق می‌رود
        fund_net_profit_saving += int(total_qard_fee_points * profit_per_point) 

        f_share_st = float(period.fund_share_short_term) / 100.0
        f_share_lt = float(period.fund_share_long_term) / 100.0
        g_rate_st = float(period.guarantee_short_term) / 100.0
        g_rate_lt = float(period.guarantee_long_term) / 100.0

        for ud in user_data:
            u = ud['user']
            
            # محاسبه سود ناخالص
            gross_st = ud['st_p'] * profit_per_point
            gross_lt = ud['lt_p'] * profit_per_point
            
            # کسر سهم صندوق (قدم دوم)
            fund_cut_st = gross_st * f_share_st
            fund_cut_lt = gross_lt * f_share_lt
            
            fund_net_profit_saving += (fund_cut_st + fund_cut_lt)
            
            user_net_st = gross_st - fund_cut_st
            user_net_lt = gross_lt - fund_cut_lt
            
            # میانگین سرمایه برای محاسبه تضمین (قدم چهارم)
            avg_cap_st = ud['st_p'] / days_in_period
            avg_cap_lt = ud['lt_p'] / days_in_period
            
            min_req_st = avg_cap_st * g_rate_st
            min_req_lt = avg_cap_lt * g_rate_lt
            
            boost_st = max(0, min_req_st - user_net_st)
            boost_lt = max(0, min_req_lt - user_net_lt)
            
            # جبران از جیب صندوق به حساب کاربر
            fund_net_profit_saving -= (boost_st + boost_lt)
            user_net_st += boost_st
            user_net_lt += boost_lt
            
            total_user_net = int(user_net_st + user_net_lt)
            ali_hesab = ud['ali_hesab']
            
            # کسر علی‌الحساب از سود نهایی (قدم سوم)
            final_payout = total_user_net - ali_hesab
            if final_payout < 0: final_payout = 0 
            
            if total_user_net > 0 or ali_hesab > 0:
                results.append({
                    'user': u,
                    'avg_st': int(avg_cap_st),
                    'gross_st': int(gross_st),
                    'fund_cut_st': int(fund_cut_st),
                    'boost_st': int(boost_st),
                    'net_st': int(user_net_st),
                    
                    'avg_lt': int(avg_cap_lt),
                    'gross_lt': int(gross_lt),
                    'fund_cut_lt': int(fund_cut_lt),
                    'boost_lt': int(boost_lt),
                    'net_lt': int(user_net_lt),
                    
                    'total_net': total_user_net,
                    'ali_hesab': ali_hesab,
                    'final_payout': final_payout
                })

        return results, int(fund_net_profit_saving), fund_net_loan_saving

    @admin.action(description='📊 ۱. دریافت اکسل پیش‌نمایش (با جزئیات تفکیکی کامل)')
    def preview_period_profit_excel(self, request, queryset):
        import csv
        from django.http import HttpResponse

        if queryset.count() != 1:
            self.message_user(request, "لطفاً فقط یک دوره را انتخاب کنید.", messages.ERROR)
            return

        period = queryset.first()
        results, fund_profit, fund_loan = self._get_period_calculation(period)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Detailed_Profit_Preview_{period.name}.csv"'
        response.write('\ufeff'.encode('utf8')) 
        writer = csv.writer(response)
        
        # هدرهای بسیار دقیق و تفکیک شده
        writer.writerow([
            'ردیف', 'نام کاربر', 'کد عضویت', 
            'میانگین سرمایه کوتاه‌مدت', 'سود ناخالص کوتاه‌مدت', 'سهم کسر شده صندوق (کوتاه‌مدت)', 'جبران تضمین (کوتاه‌مدت)', 'سود خالص کوتاه‌مدت',
            'میانگین سرمایه بلندمدت', 'سود ناخالص بلندمدت', 'سهم کسر شده صندوق (بلندمدت)', 'جبران تضمین (بلندمدت)', 'سود خالص بلندمدت',
            'جمع کل سود خالص شخص', 'علی‌الحساب پرداختی در دوره', 'مبلغ قابل واریز (قطعی)'
        ])

        tot_payout = 0
        idx = 1
        for r in results:
            writer.writerow([
                idx, r['user'].full_name, r['user'].membership_code, 
                r['avg_st'], r['gross_st'], r['fund_cut_st'], r['boost_st'], r['net_st'],
                r['avg_lt'], r['gross_lt'], r['fund_cut_lt'], r['boost_lt'], r['net_lt'],
                r['total_net'], r['ali_hesab'], r['final_payout']
            ])
            tot_payout += r['final_payout']
            idx += 1

        writer.writerow(['---'] * 16)
        writer.writerow(['مجموع مبالغ واریزی به کاربران', '', '', '', '', '', '', '', '', '', '', '', '', '', '', tot_payout])
        writer.writerow(['سهم اختصاصی صندوق (سود قطعی + رسوبات غیرمشمول)', '', '', '', '', '', '', '', '', '', '', '', '', '', '', fund_profit])
        writer.writerow(['سهم تزریقی به پس‌انداز وام صندوق', '', '', '', '', '', '', '', '', '', '', '', '', '', '', fund_loan])
        
        return response

    @admin.action(description='🏆 ۲. تایید نهایی و واریز سود قطعی دوره به حساب‌ها')
    def distribute_period_profit(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "لطفاً فقط یک دوره را انتخاب کنید.", messages.ERROR)
            return

        period = queryset.first()
        if period.is_calculated:
            self.message_user(request, "خطا: سود این دوره قبلاً محاسبه و تقسیم شده است!", messages.ERROR)
            return

        results, fund_profit, fund_loan = self._get_period_calculation(period)
        end_date_g = period.end_date
        
        transactions_to_create = []
        total_distributed = 0
        
        for r in results:
            if r['final_payout'] > 0:
                transactions_to_create.append(Transaction(
                    user=r['user'], amount=r['final_payout'], transaction_type='MANUAL_PROFIT',
                    date=timezone.now(), effective_date=end_date_g, is_verified=True,
                    description=f"سود قطعی دوره {period.name} (پس از کسر {r['ali_hesab']:,} تومان علی‌الحساب)", profit_period=period
                ))
                total_distributed += r['final_payout']
                ProfitDistribution.objects.create(period=period, user=r['user'], calculated_score=0, profit_amount=r['final_payout'])

        fund_account = User.objects.filter(role='FUND_ACCOUNT').first()
        if fund_account:
            if fund_profit > 0:
                transactions_to_create.append(Transaction(
                    user=fund_account, amount=fund_profit, transaction_type='PROFIT_SAVING',
                    date=timezone.now(), effective_date=end_date_g, is_verified=True,
                    description=f"سهم قطعی و رسوبات صندوق از دوره {period.name}", profit_period=period
                ))
            if fund_loan > 0:
                transactions_to_create.append(Transaction(
                    user=fund_account, amount=fund_loan, transaction_type='LOAN_SAVING',
                    date=timezone.now(), effective_date=end_date_g, is_verified=True,
                    description=f"رسوب وام از سود دوره {period.name} (افزایش ظرفیت وام‌دهی)", profit_period=period
                ))
                FundProfitAllocation.objects.update_or_create(
                    date=end_date_g,
                    defaults={
                        'total_profit': fund_profit + fund_loan,
                        'loan_saving_share': fund_loan,
                        'description': f"تخصیص از سود دوره {period.name}"
                    }
                )

        if transactions_to_create:
            Transaction.objects.bulk_create(transactions_to_create)

        period.is_calculated = True
        period.save()
        self.message_user(request, f"✅ سود قطعی دوره با موفقیت تقسیم شد! (کاربران: {total_distributed:,} | سود صندوق: {fund_profit:,} | پس‌انداز وام صندوق: {fund_loan:,})", messages.SUCCESS)
        
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
        lt_dep_types = ['LONG_TERM', 'MONTHLY', 'PROFIT_SAVING', 'MANUAL_PROFIT', 'SADAQAH', 'WAQF', 'SACRIFICE', 'BOOK', 'KHOMS_IMAM', 'KHOMS_SADAT', 'WAQF_GEN', 'WAQF_BOOK', 'WAQF_MEDIA', 'WAQF_INFRA']
        lt_wit_types = ['W_LONG', 'W_MONTHLY', 'W_PROFIT', 'W_MAN_PROFIT', 'WITHDRAWAL_OTHER', 'WITHDRAWAL', 'W_CULTURAL']
        
        # --- جراحی: تفکیک دقیق وام از سایر حساب‌های غیرمشمول ---
        loan_dep_types = ['LOAN_SAVING']
        loan_wit_types = ['W_SAVING']
        qf_dep_types = ['QARD', 'FEE']
        qf_wit_types = ['W_QARD', 'W_FEE']

        users = User.objects.all()
        results = []

        for user in users:
            fee_dep = Transaction.objects.filter(user=user, transaction_type='FEE', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            fee_wit = Transaction.objects.filter(user=user, transaction_type='W_FEE', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            has_paid_fee = (fee_dep - fee_wit) > 0
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
            loan_exact, loan_round = get_points(loan_dep_types, loan_wit_types)
            qf_exact, qf_round = get_points(qf_dep_types, qf_wit_types)

            user_st = 0
            user_lt = 0
            fund_resub_other = 0
            fund_resub_loan = 0

            if user.role == 'FUND_ACCOUNT':
                user_st = st_exact * daily_rate_short
                user_lt = (lt_exact + qf_exact) * daily_rate_long
                fund_resub_loan = loan_exact * daily_rate_long
            elif user.role == 'CULTURAL':
                user_st = st_exact * daily_rate_short
                user_lt = (lt_exact + qf_exact + loan_exact) * daily_rate_long
            else:
                if is_eligible:
                    user_st = st_round * daily_rate_short
                    user_lt = lt_round * daily_rate_long
                    fund_resub_other += (st_exact - st_round) * daily_rate_short
                    fund_resub_other += (lt_exact - lt_round) * daily_rate_long
                else:
                    fund_resub_other += st_exact * daily_rate_short
                    fund_resub_other += lt_exact * daily_rate_long
                
                fund_resub_other += qf_exact * daily_rate_long
                fund_resub_loan += loan_exact * daily_rate_long

            user_total = int(user_st) + int(user_lt)
            fund_resub_other_int = int(fund_resub_other)
            fund_resub_loan_int = int(fund_resub_loan)

            if user_total > 0 or fund_resub_other_int > 0 or fund_resub_loan_int > 0:
                results.append({
                    'user': user,
                    'user_st': int(user_st),
                    'user_lt': int(user_lt),
                    'user_total': user_total,
                    'fund_resub_other': fund_resub_other_int,
                    'fund_resub_loan': fund_resub_loan_int
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
        
        writer.writerow(['ردیف', 'نام و نقش', 'کد عضویت', 'سود کوتاه‌مدت شخص', 'سود بلندمدت شخص', 'جمع سود شخص', 'مبلغ رسوب شده برای صندوق (سایر)', 'رسوب پس‌انداز وام صندوق'])

        total_st = 0
        total_lt = 0
        total_user = 0
        total_fund_resub_other = 0
        total_fund_resub_loan = 0
        fund_own_profit = 0

        row_idx = 1
        for r in results:
            u = r['user']
            u_total = r['user_total']
            
            writer.writerow([row_idx, u.full_name, u.membership_code, r['user_st'], r['user_lt'], u_total, r['fund_resub_other'], r['fund_resub_loan']])
            row_idx += 1

            if u.role == 'FUND_ACCOUNT':
                fund_own_profit += u_total
            else:
                total_st += r['user_st']
                total_lt += r['user_lt']
                total_user += u_total
            
            total_fund_resub_other += r['fund_resub_other']
            total_fund_resub_loan += r['fund_resub_loan']

        writer.writerow(['---', '---', '---', '---', '---', '---', '---', '---'])
        writer.writerow(['', 'جمع سودهای پرداختی به اعضا', '', total_st, total_lt, total_user, '', ''])
        writer.writerow(['', 'سود اختصاصی خود حساب صندوق', '', '', '', fund_own_profit, '', ''])
        writer.writerow(['', 'جمع مبالغ رسوب شده از اعضا', '', '', '', '', total_fund_resub_other, total_fund_resub_loan])
        writer.writerow(['', 'مجموع کل سهم صندوق', '', '', '', fund_own_profit + total_fund_resub_other + total_fund_resub_loan, '', ''])
        
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
        total_fund_resub_other = 0
        total_fund_resub_loan = 0
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

            total_fund_resub_other += r['fund_resub_other']
            total_fund_resub_loan += r['fund_resub_loan']

        fund_user = User.objects.filter(role='FUND_ACCOUNT').first()
        if fund_user:
            if total_fund_resub_other > 0:
                transactions_to_create.append(Transaction(
                    user=fund_user, amount=total_fund_resub_other, transaction_type='MANUAL_PROFIT',
                    date=profit_transaction_date, effective_date=end_date_g,
                    is_verified=True, description=f"رسوب منابع خرد و غیرشمول - {desc_text}"
                ))
            if total_fund_resub_loan > 0:
                transactions_to_create.append(Transaction(
                    user=fund_user, amount=total_fund_resub_loan, transaction_type='LOAN_SAVING',
                    date=profit_transaction_date, effective_date=end_date_g,
                    is_verified=True, description=f"سود تولیدی از پس‌انداز وام‌ها - {desc_text}"
                ))
                # --- آپدیت جدول تخصیص‌ها ---
                FundProfitAllocation.objects.update_or_create(
                    date=end_date_g,
                    defaults={
                        'total_profit': fund_own_profit + total_fund_resub_other + total_fund_resub_loan,
                        'loan_saving_share': total_fund_resub_loan,
                        'description': f"تخصیص از {desc_text}"
                    }
                )

        if transactions_to_create:
            Transaction.objects.bulk_create(transactions_to_create)

        self.message_user(request, f"✅ موفق: سود {month_name} تقسیم شد. مبلغ {total_user_profit:,} به اعضا، {fund_own_profit + total_fund_resub_other:,} به صندوق و {total_fund_resub_loan:,} به پس‌انداز وام صندوق واریز شد.", messages.SUCCESS)
        
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