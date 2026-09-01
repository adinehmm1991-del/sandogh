from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
import datetime
import jdatetime
def add_jalali_months(base_date, months_to_add):
    import jdatetime
    j_date = jdatetime.date.fromgregorian(date=base_date)
    y = j_date.year + (j_date.month + months_to_add - 1) // 12
    m = (j_date.month + months_to_add - 1) % 12 + 1
    d = j_date.day
    if m > 6 and d == 31: d = 30
    if m == 12 and d >= 29:
        d = 30 if jdatetime.date(y, 1, 1).isleap() else 29
    return jdatetime.date(y, m, d).togregorian()

# --- تابع مسیریاب هوشمند پیامک ---
def get_admin_phones(role='general'):
    try:
        from users.models import NotificationSettings
        settings_obj = NotificationSettings.objects.first()
        if not settings_obj:
            return []
        
        phones_str = ""
        if role == 'financial':
            phones_str = settings_obj.financial_phones
        elif role == 'loan':
            phones_str = settings_obj.loan_phones
        else:
            phones_str = settings_obj.general_phones
            
        if not phones_str:
            return []
            
        # جدا کردن شماره‌ها با ویرگول و حذف فاصله‌های اضافه
        return [p.strip() for p in phones_str.split(',') if p.strip()]
    except:
        return []


# 1. ثبت سوابق دستی امتیاز
class PointLog(models.Model):
    class Types(models.TextChoices):
        TRANSFER_SENT = 'SENT', 'انتقال به دیگران (کسر)'
        TRANSFER_RECEIVED = 'RECEIVED', 'دریافت از دیگران (افزایش)'
        LOAN_USED = 'USED', 'استفاده برای وام (کسر)'
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    points = models.BigIntegerField(verbose_name="مقدار امتیاز")
    log_type = models.CharField(max_length=10, choices=Types.choices, verbose_name="نوع عملیات")
    description = models.TextField(verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True)
    related_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='point_related', verbose_name="کاربر مرتبط")

    class Meta:
        verbose_name = "سجل امتیاز"
        verbose_name_plural = "سوابق امتیازات"

    def __str__(self):
        return f"{self.user} - {self.points} ({self.get_log_type_display()})"


# 2. جدول تراکنش‌ها
class Transaction(models.Model):
    class Types(models.TextChoices):
        SHORT_TERM = 'SHORT_TERM', 'پس‌انداز کوتاه‌مدت (روزشمار)'
        LONG_TERM = 'LONG_TERM', 'پس‌انداز بلندمدت (۳ ماهه)'
        MONTHLY_DEPOSIT = 'MONTHLY', 'واریز ماهیانه (منسوخ)'
        PROFIT_SAVING = 'PROFIT_SAVING', 'پس‌انداز سود (منسوخ)'
        LOAN_SAVING = 'LOAN_SAVING', 'پس‌انداز وام'
        QARD_HASAN = 'QARD', 'قرض‌الحسنه'
        MEMBERSHIP_FEE = 'FEE', 'حق عضویت'
        MANUAL_PROFIT = 'MANUAL_PROFIT', 'واریز سود (سیستمی/دستی)'
        
        SADAQAH = 'SADAQAH', 'صدقه'
        SACRIFICE = 'SACRIFICE', 'قربانی'
        BOOK = 'BOOK', 'کتاب'
        KHOMS_IMAM = 'KHOMS_IMAM', 'سهم امام'
        KHOMS_SADAT = 'KHOMS_SADAT', 'سهم سادات'
        WAQF = 'WAQF', 'وقف (عمومی قدیم)'
        WAQF_GEN = 'WAQF_GEN', 'وقف عام'
        WAQF_BOOK = 'WAQF_BOOK', 'وقف خاص (کتاب)'
        WAQF_MEDIA = 'WAQF_MEDIA', 'وقف خاص (محتوا)'
        WAQF_INFRA = 'WAQF_INFRA', 'وقف خاص (زیرساخت)'
        
        WITHDRAWAL_SHORT = 'W_SHORT', 'برداشت از کوتاه‌مدت'
        WITHDRAWAL_LONG = 'W_LONG', 'برداشت از بلندمدت'
        WITHDRAWAL_SAVING = 'W_SAVING', 'برداشت از پس‌انداز وام'
        WITHDRAWAL_PROFIT = 'W_PROFIT', 'برداشت از پس‌انداز سود (منسوخ)'
        WITHDRAWAL_MONTHLY = 'W_MONTHLY', 'برداشت از ماهیانه (منسوخ)'
        WITHDRAWAL_QARD = 'W_QARD', 'برداشت از قرض‌الحسنه'
        WITHDRAWAL_OTHER = 'WITHDRAWAL', 'برداشت (سایر)'
        WITHDRAWAL_FEE = 'W_FEE', 'برداشت حق عضویت'
        WITHDRAWAL_MANUAL_PROFIT = 'W_MAN_PROFIT', 'برداشت از سودهای دریافتی'
        WITHDRAWAL_CULTURAL = 'W_CULTURAL', 'برداشت از حساب‌های فرهنگی'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    amount = models.BigIntegerField(verbose_name="مبلغ (تومان)")
    transaction_type = models.CharField(max_length=20, choices=Types.choices, verbose_name="نوع تراکنش")
    
    date = models.DateTimeField(verbose_name="تاریخ دقیق")
    effective_date = models.DateField(verbose_name="تاریخ مؤثر", null=True, blank=True)
    
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    is_verified = models.BooleanField(default=False, verbose_name="تایید شده")
    receipt_image = models.ImageField(upload_to='receipts/', null=True, blank=True, verbose_name="تصویر فیش")
    bank_tracking_code = models.CharField(max_length=100, null=True, blank=True, verbose_name="کد رهگیری")
    gateway_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="نام درگاه")
    profit_period = models.ForeignKey('ProfitPeriod', on_delete=models.CASCADE, null=True, blank=True, verbose_name="دوره سود")

    approval_date = models.DateField(null=True, blank=True, verbose_name="تاریخ تأیید", help_text="تاریخی که مدیر تایید کرد")

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms
        
        ALL_WITHDRAWAL_TYPES = [
            self.Types.WITHDRAWAL_SAVING, self.Types.WITHDRAWAL_PROFIT, self.Types.WITHDRAWAL_MONTHLY,
            self.Types.WITHDRAWAL_QARD, self.Types.WITHDRAWAL_OTHER, 'WITHDRAWAL', 
            self.Types.WITHDRAWAL_SHORT, self.Types.WITHDRAWAL_LONG, self.Types.WITHDRAWAL_MANUAL_PROFIT,
            self.Types.WITHDRAWAL_CULTURAL
        ]

        if not self.effective_date:
            base_date = self.date if self.date else datetime.datetime.now()
            self.effective_date = base_date.date()

        is_new = self.pk is None
        old_verified = False
        if not is_new: old_verified = Transaction.objects.get(pk=self.pk).is_verified

        super().save(*args, **kwargs)

        try:
            target_phone = self.user.parent.phone_number if self.user.parent else self.user.phone_number
            target_name = self.user.full_name
            raw_type = str(self.get_transaction_type_display())
            clean_type = raw_type.split('(')[0].strip()

            is_deposit = self.transaction_type not in ALL_WITHDRAWAL_TYPES

            # ارسال به لیست مدیران مالی
            if is_new and not self.is_verified and is_deposit:
                phones = get_admin_phones('financial')
                for phone in phones:
                    send_pattern_sms(phone, 'admin_alert', {'token1': clean_type, 'token2': target_name, 'token3': f"{self.amount:,}"})

            if not old_verified and self.is_verified and is_deposit:
                 send_pattern_sms(target_phone, 'verify_deposit', {'token1': target_name, 'token2': clean_type, 'token3': f"{self.amount:,}"})
        except: pass

    class Meta:
        verbose_name = "تراکنش"
        verbose_name_plural = "تراکنش‌ها"
    def __str__(self): return f"{self.user} - {self.amount}"


# 3. درخواست برداشت
class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار'
        APPROVED = 'APPROVED', 'تایید شده (واریز شد)'
        REJECTED = 'REJECTED', 'رد شده'

    class Source(models.TextChoices):
        LOAN_SAVING = 'LOAN', 'پس‌انداز وام'
        SHORT_TERM = 'SHORT_TERM', 'کوتاه‌مدت (بدون قفل)'
        LONG_TERM = 'LONG_TERM', 'بلندمدت (قفل ۳ ماهه)'
        PROFIT = 'PROFIT', 'سودهای دریافتی (آزاد)'
        QARD = 'QARD', 'قرض‌الحسنه'
        CULTURAL = 'CULTURAL', 'حساب‌های فرهنگی'
        FEE = 'FEE', 'حق عضویت'  # <--- فقط این خط اضافه شود

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    amount = models.BigIntegerField(verbose_name="مبلغ (تومان)")
    description = models.TextField(null=True, blank=True, verbose_name="شماره کارت/شبا")
    source_type = models.CharField(max_length=10, choices=Source.choices, default=Source.LOAN_SAVING, verbose_name="محل کسر وجه")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="وضعیت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ درخواست")
    admin_note = models.TextField(null=True, blank=True, verbose_name="پاسخ مدیر")

    class Meta:
        verbose_name = "درخواست برداشت"
        verbose_name_plural = "درخواست‌های برداشت"

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms
        
        is_new = self.pk is None
        old_status = None
        if not is_new: old_status = WithdrawalRequest.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)
        
        target_phone = self.user.parent.phone_number if self.user.parent else self.user.phone_number
        target_name = self.user.full_name

        try:
            # ارسال به لیست مدیران مالی
            if is_new:
                phones = get_admin_phones('financial')
                for phone in phones:
                    send_pattern_sms(phone, 'admin_alert', {'token1': "درخواست برداشت", 'token2': target_name, 'token3': f"{self.amount:,}"})

            if old_status != self.Status.APPROVED and self.status == self.Status.APPROVED:
                t_type = Transaction.Types.WITHDRAWAL_OTHER
                if self.source_type == self.Source.SHORT_TERM: t_type = Transaction.Types.WITHDRAWAL_SHORT
                elif self.source_type == self.Source.LONG_TERM: t_type = Transaction.Types.WITHDRAWAL_LONG
                elif self.source_type == self.Source.LOAN_SAVING: t_type = Transaction.Types.WITHDRAWAL_SAVING
                elif self.source_type == self.Source.PROFIT: t_type = Transaction.Types.WITHDRAWAL_MANUAL_PROFIT
                elif self.source_type == self.Source.QARD: t_type = Transaction.Types.WITHDRAWAL_QARD
                elif self.source_type == self.Source.CULTURAL: t_type = Transaction.Types.WITHDRAWAL_CULTURAL
                elif self.source_type == self.Source.FEE: t_type = Transaction.Types.WITHDRAWAL_FEE # <--- فقط این خط اضافه شود

                Transaction.objects.create(
                    user=self.user, amount=self.amount, transaction_type=t_type,
                    date=timezone.now(), is_verified=True,
                    description=f"برداشت بابت درخواست {self.id} (از محل {self.get_source_type_display()}) - {self.admin_note or ''}"
                )
                send_pattern_sms(target_phone, 'verify_withdraw', {'token1': target_name, 'token2': f"{self.amount:,}"})
        except: pass

# 4. درخواست وام
class LoanRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار'
        APPROVED = 'APPROVED', 'تایید شده (معرفی به بانک)'
        REJECTED = 'REJECTED', 'رد شده'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    amount = models.BigIntegerField(verbose_name="مبلغ وام (تومان)")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="وضعیت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ درخواست")
    points_cost = models.BigIntegerField(default=0, verbose_name="امتیاز کسر شده")
    
    # --- فیلدهای جدید فاز ۴ ---
    duration_months = models.IntegerField(default=12, verbose_name="مدت بازپرداخت (ماه)")
    granted_date = models.DateField(null=True, blank=True, verbose_name="تاریخ معرفی به بانک")
    is_manual = models.BooleanField(default=False, verbose_name="وام دستی (تصمیم هیئت مدیره)")

    class Meta:
        verbose_name = "پرونده وام"
        verbose_name_plural = "پرونده‌های وام"

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms
        is_new = self.pk is None
        old_status = None
        if not is_new: old_status = LoanRequest.objects.get(pk=self.pk).status
        super().save(*args, **kwargs)
        if self.status == self.Status.APPROVED and self.granted_date and self.duration_months > 0:
            from .models import LoanInstallment
            if not LoanInstallment.objects.filter(loan=self).exists():
                installment_amount = self.amount // self.duration_months
                for i in range(1, self.duration_months + 1):
                    due = add_jalali_months(self.granted_date, i)
                    LoanInstallment.objects.create(
                        loan=self, installment_number=i, due_date=due, amount=installment_amount
                    )
        target_name = self.user.full_name or self.user.phone_number
        try:
            # ارسال به لیست مسئولین وام
            if is_new:
                phones = get_admin_phones('loan')
                for phone in phones:
                    send_pattern_sms(phone, 'loan_request_admin', {'token1': target_name, 'token2': f"{self.amount:,}"})
                    
            if not is_new and old_status != self.status and self.status in [self.Status.APPROVED, self.Status.REJECTED]:
                target_phone = self.user.parent.phone_number if self.user.parent else self.user.phone_number
                send_pattern_sms(target_phone, 'loan_result_user', {'token1': target_name})
                if self.status == self.Status.APPROVED and self.points_cost > 0:
                    exists = PointLog.objects.filter(user=self.user, log_type=PointLog.Types.LOAN_USED, description__contains=f"وام {self.id}").exists()
                    if not exists:
                        PointLog.objects.create(user=self.user, points=-self.points_cost, log_type=PointLog.Types.LOAN_USED, description=f"استفاده برای وام {self.amount:,} تومانی (شناسه {self.id})")
        except: pass

# --- مدل‌های سود ---
class ProfitPeriod(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دوره (مثلاً سال ۱۴۰۴)")
    start_date = models.DateField(verbose_name="تاریخ شروع دوره")
    end_date = models.DateField(verbose_name="تاریخ پایان دوره")
    total_profit_amount = models.BigIntegerField(default=0, verbose_name="مبلغ کل سود (تومان)")
    is_calculated = models.BooleanField(default=False, verbose_name="آیا سود این دوره محاسبه و تقسیم شده است؟")
    
    class Meta:
        verbose_name = "دوره سود سالیانه"
        verbose_name_plural = "دوره‌های سود سالیانه"
    def __str__(self): return self.name

class ProfitDistribution(models.Model):
    period = models.ForeignKey(ProfitPeriod, on_delete=models.CASCADE, verbose_name="دوره سود")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    calculated_score = models.DecimalField(max_digits=20, decimal_places=4, verbose_name="امتیاز/سرمایه محاسبه‌شده")
    profit_amount = models.BigIntegerField(verbose_name="مبلغ واریز شده (تومان)")

    class Meta:
        verbose_name = "سود تقسیم شده (گزارش فردی)"
        verbose_name_plural = "گزارش سودهای تقسیم شده"

class PointTransferRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار تایید'
        APPROVED = 'APPROVED', 'تایید شده (انجام شد)'
        REJECTED = 'REJECTED', 'رد شده'

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_point_requests', verbose_name="فرستنده")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_point_requests', verbose_name="گیرنده")
    amount = models.IntegerField(verbose_name="میزان امتیاز")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="وضعیت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ درخواست")
    admin_note = models.TextField(null=True, blank=True, verbose_name="یادداشت مدیر")

    class Meta:
        verbose_name = "درخواست انتقال امتیاز"
        verbose_name_plural = "درخواست‌های انتقال امتیاز"

    def __str__(self): return f"{self.sender} -> {self.receiver} ({self.amount})"

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms
        is_new = self.pk is None
        old_status = None
        if not is_new: old_status = PointTransferRequest.objects.get(pk=self.pk).status
        super().save(*args, **kwargs)
        try:
            # ارسال به مدیر کل
           if is_new and self.status == self.Status.PENDING:
                    
            if old_status != self.Status.APPROVED and self.status == self.Status.APPROVED:
                PointLog.objects.create(user=self.sender, points=-self.amount, log_type=PointLog.Types.TRANSFER_SENT, related_user=self.receiver, description=f"انتقال تایید شده به {self.receiver.full_name}")
                PointLog.objects.create(user=self.receiver, points=self.amount, log_type=PointLog.Types.TRANSFER_RECEIVED, related_user=self.sender, description=f"دریافت تایید شده از {self.sender.full_name}")
                target_phone = self.receiver.parent.phone_number if self.receiver.parent else self.receiver.phone_number
                send_pattern_sms(target_phone, 'transfer_received_user', {'token1': self.receiver.full_name, 'token2': f"{self.amount:,}"})
        except: pass

class ProfitRate(models.Model):
    month_year = models.DateField(verbose_name="ماه و سال", unique=True)
    short_term_percent = models.DecimalField(max_digits=5, decimal_places=2, default=2.00, verbose_name="درصد سود کوتاه‌مدت")
    long_term_percent = models.DecimalField(max_digits=5, decimal_places=2, default=3.00, verbose_name="درصد سود بلندمدت")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="ثبت‌کننده")

    class Meta:
        verbose_name = "نرخ سود علی‌الحساب"
        verbose_name_plural = "نرخ‌های سود علی‌الحساب"
        ordering = ['-month_year']

# --- مدیریت سودهای کلاری/سرمایه‌گذاری صندوق (فاز ۴) ---
class FundProfitAllocation(models.Model):
    date = models.DateField(verbose_name="تاریخ واریز سود به صندوق")
    total_profit = models.BigIntegerField(verbose_name="کل سود دریافتی (تومان)", help_text="مثلاً سود سپرده‌گذاری در بانک")
    
    loan_saving_share = models.BigIntegerField(default=0, verbose_name="سهم پس‌انداز وام (تومان)", help_text="این مبلغ به ظرفیت وام‌دهی اضافه می‌شود")
    qard_share = models.BigIntegerField(default=0, verbose_name="سهم قرض‌الحسنه (تومان)")
    short_term_share = models.BigIntegerField(default=0, verbose_name="سهم کوتاه‌مدت (تومان)")
    long_term_share = models.BigIntegerField(default=0, verbose_name="سهم بلندمدت (تومان)")
    
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات و منبع سود")

    class Meta:
        verbose_name = "تخصیص سود سرمایه‌گذاری صندوق"
        verbose_name_plural = "تخصیص‌های سود سرمایه‌گذاری"
        ordering = ['-date']
        
    def __str__(self):
        return f"سود {self.date} - مبلغ کل: {self.total_profit:,} تومان"


# =========================================================
# --- فاز ۵: مدیریت سرمایه‌گذاری‌های خارج از صندوق ---
# =========================================================

class ExternalInvestment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'فعال (در جریان)'
        CLOSED = 'CLOSED', 'بسته شده (پایان یافته)'

    class InvestmentType(models.TextChoices):
        SHORT_TERM = 'SHORT_TERM', 'کوتاه‌مدت'
        LONG_TERM = 'LONG_TERM', 'بلندمدت'
        RISK_FREE = 'RISK_FREE', 'بدون ریسک (سپرده بانکی/اوراق)'
        RISKY = 'RISKY', 'ریسک‌پذیر (بورس/طلا/املاک)'

    title = models.CharField(max_length=200, verbose_name="عنوان سرمایه‌گذاری", help_text="مثلاً: سپرده بانکی رسالت، خرید طلا، صندوق درآمد ثابت")
    investment_type = models.CharField(max_length=20, choices=InvestmentType.choices, default=InvestmentType.RISK_FREE, verbose_name="نوع سرمایه‌گذاری")
    start_date = models.DateField(verbose_name="تاریخ شروع")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name="وضعیت")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات تکمیلی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت در سیستم")

    class Meta:
        verbose_name = "پرونده سرمایه‌گذاری"
        verbose_name_plural = "پرونده‌های سرمایه‌گذاری"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class InvestmentTransaction(models.Model):
    class Types(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'تزریق سرمایه (خروج پول از صندوق به سرمایه‌گذاری)'
        WITHDRAWAL = 'WITHDRAWAL', 'آزادسازی سرمایه (بازگشت اصل پول به صندوق)'
        PROFIT = 'PROFIT', 'سود محقق شده (درآمد حاصل از سرمایه‌گذاری)'

    investment = models.ForeignKey(ExternalInvestment, on_delete=models.CASCADE, related_name='transactions', verbose_name="پرونده سرمایه‌گذاری")
    amount = models.BigIntegerField(verbose_name="مبلغ (تومان)")
    transaction_type = models.CharField(max_length=20, choices=Types.choices, verbose_name="نوع تراکنش")
    date = models.DateField(verbose_name="تاریخ تراکنش")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    is_settled = models.BooleanField(default=False, verbose_name="تسویه شده (صفر شده)")

    class Meta:
        verbose_name = "گردش مالی سرمایه‌گذاری"
        verbose_name_plural = "گردش‌های مالی سرمایه‌گذاری"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.investment.title} - {self.get_transaction_type_display()} - {self.amount:,} تومان"

# --- فاز جدید: جدول اقساط وام ---
class LoanInstallment(models.Model):
    loan = models.ForeignKey(LoanRequest, on_delete=models.CASCADE, related_name='installments', verbose_name="وام مرتبط")
    installment_number = models.IntegerField(verbose_name="شماره قسط")
    due_date = models.DateField(verbose_name="تاریخ سررسید")
    amount = models.BigIntegerField(verbose_name="مبلغ قسط (تومان)")
    is_paid = models.BooleanField(default=False, verbose_name="پرداخت شده")
    paid_date = models.DateField(null=True, blank=True, verbose_name="تاریخ پرداخت")

    class Meta:
        verbose_name = "قسط وام"
        verbose_name_plural = "اقساط وام"
        ordering = ['installment_number']