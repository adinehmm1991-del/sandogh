from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
import datetime
import jdatetime

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
        MONTHLY_DEPOSIT = 'MONTHLY', 'واریز ماهیانه (تعهد)'
        PROFIT_SAVING = 'PROFIT_SAVING', 'پس‌انداز سود (سرمایه‌گذاری)'
        LOAN_SAVING = 'LOAN_SAVING', 'پس‌انداز وام'
        QARD_HASAN = 'QARD', 'قرض‌الحسنه'
        DONATION = 'DONATION', 'بلاعوض (کمک خیریه)'
        MEMBERSHIP_FEE = 'FEE', 'حق عضویت'
        
        # انواع برداشت
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
        
        # لیست امن برای تشخیص برداشت‌ها (هماهنگ با views.py)
        ALL_WITHDRAWAL_TYPES = [
            self.Types.WITHDRAWAL_SAVING,
            self.Types.WITHDRAWAL_PROFIT,
            self.Types.WITHDRAWAL_MONTHLY,
            self.Types.WITHDRAWAL_QARD,
            self.Types.WITHDRAWAL_OTHER,
            'WITHDRAWAL'
        ]

        # 1. تنظیم هوشمند تاریخ مؤثر
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

            # شرط: اگر جزء لیست برداشت‌ها نباشد => یعنی واریز است
            is_deposit = self.transaction_type not in ALL_WITHDRAWAL_TYPES

            # الف) پیامک به مدیر (فقط برای ثبت جدید واریزها)
            if is_new and not self.is_verified and is_deposit:
                send_pattern_sms(ADMIN_PHONE, 'admin_alert', {'token1': clean_type, 'token2': target_name, 'token3': f"{self.amount:,}"})

            # ب) پیامک تایید به کاربر (فقط برای واریزها)
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
        PROFIT_SAVING = 'PROFIT', 'پس‌انداز سود'
        MONTHLY = 'MONTHLY', 'ماهیانه'
        QARD = 'QARD', 'قرض‌الحسنه'

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

    class Meta:
        verbose_name = "درخواست وام"
        verbose_name_plural = "درخواست‌های وام"

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms, ADMIN_PHONE
        
        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_status = LoanRequest.objects.get(pk=self.pk).status
        
        super().save(*args, **kwargs)

        target_name = self.user.full_name or self.user.phone_number

        try:
            if is_new:
                send_pattern_sms(ADMIN_PHONE, 'loan_request_admin', {
                    'token1': target_name,
                    'token2': f"{self.amount:,}"
                })

            if not is_new and old_status != self.status and self.status in [self.Status.APPROVED, self.Status.REJECTED]:
                target_phone = self.user.parent.phone_number if self.user.parent else self.user.phone_number
                
                send_pattern_sms(target_phone, 'loan_result_user', {
                    'token1': target_name
                })
                
                if self.status == self.Status.APPROVED and self.points_cost > 0:
                    exists = PointLog.objects.filter(
                        user=self.user, 
                        log_type=PointLog.Types.LOAN_USED, 
                        description__contains=f"وام {self.id}"
                    ).exists()
                    
                    if not exists:
                        PointLog.objects.create(
                            user=self.user,
                            points=-self.points_cost,
                            log_type=PointLog.Types.LOAN_USED,
                            description=f"استفاده برای وام {self.amount:,} تومانی (شناسه {self.id})"
                        )
        except Exception as e:
            print(f"SMS Error: {e}")

# مدل‌های سود
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


# 5. درخواست انتقال امتیاز
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

    def __str__(self):
        return f"{self.sender} -> {self.receiver} ({self.amount})"

    def save(self, *args, **kwargs):
        from users.utils import send_pattern_sms, ADMIN_PHONE

        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_status = PointTransferRequest.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)
        
        try:
            if is_new:
                send_pattern_sms(ADMIN_PHONE, 'transfer_request_admin', {
                    'token1': self.sender.full_name,
                    'token2': self.receiver.full_name
                })

            if old_status != self.Status.APPROVED and self.status == self.Status.APPROVED:
                # اصلاح مهم: حذف شرط exists تاریخ‌دار که باعث باگ در انتقال‌های متعدد می‌شد.
                # همین که وضعیت از غیر تایید به تایید تغییر کرده، یعنی باید لاگ ثبت شود.
                
                PointLog.objects.create(
                    user=self.sender,
                    points=-self.amount,
                    log_type=PointLog.Types.TRANSFER_SENT,
                    related_user=self.receiver,
                    description=f"انتقال تایید شده به {self.receiver.full_name}"
                )
                PointLog.objects.create(
                    user=self.receiver,
                    points=self.amount,
                    log_type=PointLog.Types.TRANSFER_RECEIVED,
                    related_user=self.sender,
                    description=f"دریافت تایید شده از {self.sender.full_name}"
                )

                target_phone = self.receiver.parent.phone_number if self.receiver.parent else self.receiver.phone_number
                send_pattern_sms(target_phone, 'transfer_received_user', {
                    'token1': self.receiver.full_name,
                    'token2': f"{self.amount:,}"
                })

        except Exception as e:
            print(f"SMS/Log Error: {e}")