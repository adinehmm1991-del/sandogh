from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
import datetime
import jdatetime

# 1. ثبت سوابق دستی امتیاز (انتقال یا استفاده) - (جدید)
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
    
    # کاربر مرتبط (مثلاً کسی که امتیاز را به او داده‌ایم)
    related_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='point_related', verbose_name="کاربر مرتبط")

    class Meta:
        verbose_name = "سجل امتیاز"
        verbose_name_plural = "سوابق امتیازات"

    def __str__(self):
        return f"{self.user} - {self.points} ({self.get_log_type_display()})"


# 2. جدول تراکنش‌ها (تغییر یافته)
class Transaction(models.Model):
    class Types(models.TextChoices):
        MONTHLY_DEPOSIT = 'MONTHLY', 'واریز ماهیانه (تعهد)'
        PROFIT_SAVING = 'PROFIT_SAVING', 'پس‌انداز سود (سرمایه‌گذاری)'
        LOAN_SAVING = 'LOAN_SAVING', 'پس‌انداز وام'
        QARD_HASAN = 'QARD', 'قرض‌الحسنه'
        DONATION = 'DONATION', 'بلاعوض (کمک خیریه)'
        MEMBERSHIP_FEE = 'FEE', 'حق عضویت'
        
        # انواع جدید برداشت (تفکیک شده)
        WITHDRAWAL_SAVING = 'W_SAVING', 'برداشت از پس‌انداز وام'
        WITHDRAWAL_PROFIT = 'W_PROFIT', 'برداشت از سود'
        WITHDRAWAL_MONTHLY = 'W_MONTHLY', 'برداشت از ماهیانه'
        WITHDRAWAL_QARD = 'W_QARD', 'برداشت از قرض‌الحسنه'
        WITHDRAWAL_OTHER = 'WITHDRAWAL', 'برداشت (سایر)'

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

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms, ADMIN_PHONE
        
        # 1. تنظیم هوشمند تاریخ مؤثر (قانون ۵ روز اول ماه)
        if not self.effective_date:
            base_date = self.date if self.date else datetime.datetime.now()
            j_date = jdatetime.date.fromgregorian(date=base_date.date())
            
            if self.transaction_type in [self.Types.MONTHLY_DEPOSIT, self.Types.PROFIT_SAVING]:
                if j_date.day <= 5:
                    self.effective_date = base_date.date()
                else:
                    if j_date.month == 12: next_year, next_month = j_date.year + 1, 1
                    else: next_year, next_month = j_date.year, j_date.month + 1
                    next_month_j = jdatetime.date(next_year, next_month, 1)
                    self.effective_date = next_month_j.togregorian()
            else:
                self.effective_date = base_date.date()

        is_new = self.pk is None
        old_verified = False
        if not is_new: old_verified = Transaction.objects.get(pk=self.pk).is_verified

        super().save(*args, **kwargs)

        # --- بخش ارسال پیامک ---
        try:
            target_phone = self.user.parent.phone_number if self.user.parent else self.user.phone_number
            target_name = self.user.full_name
            
            raw_type = str(self.get_transaction_type_display())
            clean_type = raw_type.split('(')[0].strip()

            # الف) پیامک به مدیر (فقط برای ثبت جدید)
            if is_new and not self.is_verified and not self.transaction_type.startswith('W_') and self.transaction_type != 'WITHDRAWAL':
                send_pattern_sms(ADMIN_PHONE, 'admin_alert', {'token1': clean_type, 'token2': target_name, 'token3': f"{self.amount:,}"})

            # ب) پیامک تایید به کاربر
            if not old_verified and self.is_verified:
                if not self.transaction_type.startswith('W_') and self.transaction_type != 'WITHDRAWAL':
                    # پیامک تایید واریز
                    send_pattern_sms(target_phone, 'verify_deposit', {'token1': target_name, 'token2': clean_type, 'token3': f"{self.amount:,}"})
        except: pass

    class Meta:
        verbose_name = "تراکنش"
        verbose_name_plural = "تراکنش‌ها"
    def __str__(self): return f"{self.user} - {self.amount}"


# 3. درخواست برداشت (اصلاح شده با منبع)
class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار'
        APPROVED = 'APPROVED', 'تایید شده (واریز شد)'
        REJECTED = 'REJECTED', 'رد شده'

    class Source(models.TextChoices):
        LOAN_SAVING = 'LOAN', 'پس‌انداز وام'
        PROFIT_SAVING = 'PROFIT', 'پس‌انداز سود'
        MONTHLY = 'MONTHLY', 'ماهیانه'
        QARD = 'QARD', 'قرض‌الحسنه'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    amount = models.BigIntegerField(verbose_name="مبلغ (تومان)")
    description = models.TextField(null=True, blank=True, verbose_name="شماره کارت/شبا")
    
    # فیلد جدید: منبع برداشت
    source_type = models.CharField(max_length=10, choices=Source.choices, default=Source.LOAN_SAVING, verbose_name="محل کسر وجه")
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="وضعیت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ درخواست")
    admin_note = models.TextField(null=True, blank=True, verbose_name="پاسخ مدیر")

    class Meta:
        verbose_name = "درخواست برداشت"
        verbose_name_plural = "درخواست‌های برداشت"

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms, ADMIN_PHONE
        
        is_new = self.pk is None
        old_status = None
        if not is_new: old_status = WithdrawalRequest.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)
        
        target_phone = self.user.parent.phone_number if self.user.parent else self.user.phone_number
        target_name = self.user.full_name

        try:
            if is_new:
                send_pattern_sms(ADMIN_PHONE, 'admin_alert', {'token1': "درخواست برداشت", 'token2': target_name, 'token3': f"{self.amount:,}"})

            # اگر تایید شد، تراکنش برداشت ثبت کن
            if old_status != self.Status.APPROVED and self.status == self.Status.APPROVED:
                # تشخیص نوع تراکنش بر اساس منبع
                t_type = Transaction.Types.WITHDRAWAL_OTHER
                if self.source_type == self.Source.LOAN_SAVING: t_type = Transaction.Types.WITHDRAWAL_SAVING
                elif self.source_type == self.Source.PROFIT_SAVING: t_type = Transaction.Types.WITHDRAWAL_PROFIT
                elif self.source_type == self.Source.MONTHLY: t_type = Transaction.Types.WITHDRAWAL_MONTHLY
                elif self.source_type == self.Source.QARD: t_type = Transaction.Types.WITHDRAWAL_QARD

                Transaction.objects.create(
                    user=self.user,
                    amount=self.amount,
                    transaction_type=t_type,
                    date=timezone.now(),
                    is_verified=True,
                    description=f"برداشت بابت درخواست {self.id} (از محل {self.get_source_type_display()}) - {self.admin_note or ''}"
                )
                
                send_pattern_sms(target_phone, 'verify_withdraw', {'token1': target_name, 'token2': f"{self.amount:,}"})
        except: pass


# 4. درخواست وام (جدید)
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
    
    # فیلد امتیاز کسر شده (که مدیر موقع تایید پر میکند)
    points_cost = models.BigIntegerField(default=0, verbose_name="امتیاز کسر شده")

    class Meta:
        verbose_name = "درخواست وام"
        verbose_name_plural = "درخواست‌های وام"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new: old_status = LoanRequest.objects.get(pk=self.pk).status
        
        super().save(*args, **kwargs)

        # اگر تایید شد و هزینه امتیاز داشت، از سوابق امتیاز کسر کن
        if old_status != self.Status.APPROVED and self.status == self.Status.APPROVED:
            if self.points_cost > 0:
                PointLog.objects.create(
                    user=self.user,
                    points=-self.points_cost, # منفی یعنی کسر شود
                    log_type=PointLog.Types.LOAN_USED,
                    description=f"استفاده برای وام {self.amount:,} تومانی"
                )

# مدل‌های سود (بدون تغییر)
class ProfitPeriod(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    total_profit_amount = models.BigIntegerField(default=0)
    is_calculated = models.BooleanField(default=False)
    def __str__(self): return self.name

class ProfitDistribution(models.Model):
    period = models.ForeignKey(ProfitPeriod, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    calculated_score = models.DecimalField(max_digits=20, decimal_places=4)
    profit_amount = models.BigIntegerField()