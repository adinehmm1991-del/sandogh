from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
import datetime
import jdatetime

# 1. جدول تراکنش‌ها
class Transaction(models.Model):
    class Types(models.TextChoices):
        MONTHLY_DEPOSIT = 'MONTHLY', 'واریز ماهیانه (تعهد)'
        PROFIT_SAVING = 'PROFIT_SAVING', 'پس‌انداز سود (سرمایه‌گذاری)'
        LOAN_SAVING = 'LOAN_SAVING', 'پس‌انداز وام'
        QARD_HASAN = 'QARD', 'قرض‌الحسنه'
        DONATION = 'DONATION', 'بلاعوض (کمک خیریه)'
        MEMBERSHIP_FEE = 'FEE', 'حق عضویت'
        WITHDRAWAL = 'WITHDRAWAL', 'برداشت وجه'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    amount = models.BigIntegerField(verbose_name="مبلغ (تومان)")
    transaction_type = models.CharField(max_length=20, choices=Types.choices, verbose_name="نوع تراکنش")
    
    date = models.DateTimeField(verbose_name="تاریخ دقیق واریز")
    effective_date = models.DateField(verbose_name="تاریخ مؤثر (مبنای محاسبه)", null=True, blank=True)
    
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات")
    is_verified = models.BooleanField(default=False, verbose_name="تایید شده")
    receipt_image = models.ImageField(upload_to='receipts/', null=True, blank=True, verbose_name="تصویر فیش")

    bank_tracking_code = models.CharField(max_length=100, null=True, blank=True, verbose_name="کد رهگیری بانک")
    gateway_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="نام درگاه")

    profit_period = models.ForeignKey('ProfitPeriod', on_delete=models.CASCADE, null=True, blank=True, verbose_name="مرتبط با دوره سود")

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms, ADMIN_PHONE 

        # 1. تنظیم تاریخ مؤثر
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

        # بررسی وضعیت
        is_new = self.pk is None
        old_verified = False
        if not is_new:
            old_verified = Transaction.objects.get(pk=self.pk).is_verified

        super().save(*args, **kwargs)

        # --- هوشمندسازی گیرنده پیامک ---
        # اگر کاربر سرپرست داشت (فرزند بود)، پیامک به سرپرست برود. اگر نه، به خودش.
        target_phone = self.user.parent.phone_number if self.user.parent else self.user.phone_number
        target_name = self.user.full_name # نام خودِ کاربر (فرزند) در متن پیامک باشد

        try:
            # تمیز کردن متن نوع تراکنش
            raw_type = str(self.get_transaction_type_display())
            clean_type = raw_type.split('(')[0].strip()

            # الف) پیامک به مدیر (ثبت جدید)
            if is_new and not self.is_verified and self.transaction_type not in [self.Types.PROFIT_SAVING, self.Types.WITHDRAWAL]:
                send_pattern_sms(ADMIN_PHONE, 'admin_alert', {
                    'token1': clean_type,
                    'token2': target_name, # نام کسی که پول داده
                    'token3': f"{self.amount:,}"
                })

            # ب) پیامک به کاربر (تایید شدن)
            if not old_verified and self.is_verified and self.transaction_type not in [self.Types.WITHDRAWAL, self.Types.PROFIT_SAVING]:
                deposits = Transaction.objects.filter(user=self.user, is_verified=True).exclude(transaction_type='WITHDRAWAL').aggregate(Sum('amount'))['amount__sum'] or 0
                withdrawals = Transaction.objects.filter(user=self.user, is_verified=True, transaction_type='WITHDRAWAL').aggregate(Sum('amount'))['amount__sum'] or 0
                balance = deposits - withdrawals

                send_pattern_sms(target_phone, 'verify_deposit', {
                    'token1': target_name, # نام فرزند
                    'token2': clean_type,
                    'token3': f"{self.amount:,}",
                    'token4': f"{balance:,}"
                })
        except: pass

    class Meta:
        verbose_name = "تراکنش"
        verbose_name_plural = "تراکنش‌ها"

    def __str__(self):
        return f"{self.user} - {self.amount}"


# 2. مدل درخواست برداشت
class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار بررسی'
        APPROVED = 'APPROVED', 'تایید شده (واریز شد)'
        REJECTED = 'REJECTED', 'رد شده'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر")
    amount = models.BigIntegerField(verbose_name="مبلغ درخواستی (تومان)")
    description = models.TextField(null=True, blank=True, verbose_name="توضیحات (شماره کارت و...)")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="وضعیت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ درخواست")
    admin_note = models.TextField(null=True, blank=True, verbose_name="پاسخ مدیر")

    class Meta:
        verbose_name = "درخواست برداشت"
        verbose_name_plural = "درخواست‌های برداشت"

    def __str__(self):
        return f"{self.user} - {self.amount}"

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms, ADMIN_PHONE 
        
        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_status = WithdrawalRequest.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # هوشمندسازی گیرنده
        target_phone = self.user.parent.phone_number if self.user.parent else self.user.phone_number
        target_name = self.user.full_name

        try:
            # الف) پیامک به مدیر
            if is_new:
                send_pattern_sms(ADMIN_PHONE, 'admin_alert', {
                    'token1': "درخواست برداشت",
                    'token2': target_name,
                    'token3': f"{self.amount:,}"
                })

            # ب) پیامک به کاربر (تایید و واریز)
            if old_status != self.Status.APPROVED and self.status == self.Status.APPROVED:
                Transaction.objects.create(
                    user=self.user,
                    amount=self.amount,
                    transaction_type=Transaction.Types.WITHDRAWAL,
                    date=timezone.now(),
                    is_verified=True,
                    description=f"برداشت خودکار بابت درخواست {self.id} - {self.admin_note or ''}"
                )
                
                send_pattern_sms(target_phone, 'verify_withdraw', {
                    'token1': target_name,
                    'token2': f"{self.amount:,}"
                })
        except: pass


# 3. مدل‌های سود (بدون تغییر)
class ProfitPeriod(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دوره")
    start_date = models.DateField(verbose_name="تاریخ شروع")
    end_date = models.DateField(verbose_name="تاریخ پایان")
    total_profit_amount = models.BigIntegerField(default=0, verbose_name="کل سود (تومان)")
    is_calculated = models.BooleanField(default=False, verbose_name="محاسبه شده؟")

    class Meta:
        verbose_name = "دوره سود"
        verbose_name_plural = "دوره‌های سود"

    def __str__(self):
        return self.name

class ProfitDistribution(models.Model):
    period = models.ForeignKey(ProfitPeriod, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    calculated_score = models.DecimalField(max_digits=20, decimal_places=4, verbose_name="امتیاز وزنی")
    profit_amount = models.BigIntegerField(verbose_name="سود تعلق گرفته")

    class Meta:
        verbose_name = "توزیع سود"
        verbose_name_plural = "لیست توزیع سود"
        unique_together = ('period', 'user')