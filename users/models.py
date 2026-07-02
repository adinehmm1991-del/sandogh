from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import random
import string
from django.utils.translation import gettext_lazy as _

# 1. مدیر شخصی‌سازی شده (اصلاح شده برای موبایل)
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError(_('شماره موبایل باید وارد شود'))
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Roles.ADMIN) 
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('مدیر کل باید is_staff=True داشته باشد.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('مدیر کل باید is_superuser=True داشته باشد.'))

        return self.create_user(phone_number, password, **extra_fields)

# 2. جدول کاربران
class User(AbstractUser):
    username = None

    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', _('مدیر سیستم')
        OBSERVER = 'OBSERVER', _('ناظر')
        MEMBER = 'MEMBER', _('عضو عادی')
        BENEFACTOR = 'BENEFACTOR', _('خیر')
        FUND_ACCOUNT = 'FUND_ACCOUNT', _('حساب صندوق')
        CULTURAL = 'CULTURAL', _('حساب فرهنگی و خیریه') # <--- این خط اضافه شد

    class Gender(models.TextChoices):
        MALE = 'MALE', _('آقا')
        FEMALE = 'FEMALE', _('خانم')

    # موبایل دوباره یکتا (Unique) شد
    phone_number = models.CharField(max_length=11, unique=True, verbose_name=_("شماره موبایل"))
    national_code = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("کد ملی"))
    membership_code = models.CharField(max_length=20, unique=True, verbose_name=_("کد عضویت"))
    
    full_name = models.CharField(max_length=150, verbose_name=_("نام و نام خانوادگی"))
    gender = models.CharField(max_length=10, choices=Gender.choices, null=True, blank=True, verbose_name=_("جنسیت"))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ تولد"))
    social_id = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("آیدی پیام‌رسان"))
    
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.MEMBER, verbose_name=_("نقش"))
    can_manage_loans = models.BooleanField(default=False, verbose_name=_("دسترسی مدیریت وام (هیئت مدیره)"))
    can_manage_investments = models.BooleanField(default=False, verbose_name="دسترسی مدیریت سرمایه‌گذاری")
    card_number = models.CharField(max_length=16, null=True, blank=True, verbose_name=_("شماره کارت"))
    
    card_number = models.CharField(max_length=16, null=True, blank=True, verbose_name=_("شماره کارت"))
    shaba_number = models.CharField(max_length=26, null=True, blank=True, verbose_name=_("شماره شبا"))
    
    referral_code = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("کد معرف"))
    monthly_commitment = models.BigIntegerField(null=True, blank=True, verbose_name=_("تعهد واریز ماهیانه (ریال)"))
    # فیلد جدید: سرپرست (برای اعضای خانواده)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='family_members', verbose_name="سرپرست")
    # 🆕 فیلدهای تأیید مدیر (اضافه شود)
    
    


    # نام کاربری دوباره شد موبایل
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    
    def save(self, *args, **kwargs):
        # ۱. ابتدا بررسی می‌کنیم که آیا این یک ثبت‌نام جدید است یا خیر (قبل از ذخیره)
        is_new = self.pk is None
        
        # ۲. اگر کاربر جدید بود، کد عضویت ۳۱۳... برایش تولید می‌کنیم
        if is_new and not self.membership_code:
            # --- جراحی نهایی: پیدا کردن بزرگترین کد به صورت کاملاً ریاضی ---
            users_with_313 = User.objects.filter(membership_code__startswith='313')
            max_code = 313000
            
            for u in users_with_313:
                try:
                    code_int = int(u.membership_code)
                    if code_int > max_code:
                        max_code = code_int
                except ValueError:
                    pass
            
            new_code = max_code + 1
            
            # تله‌ی ضدتداخل: اگر به هر دلیلی این کد پر بود، آنقدر برو جلو تا یک جای خالی پیدا کنی!
            while User.objects.filter(membership_code=str(new_code)).exists():
                new_code += 1
                
            self.membership_code = str(new_code)

        # ۳. کاربر را در دیتابیس ذخیره می‌کنیم (این خط فقط باید یک بار نوشته شود!)
        super().save(*args, **kwargs)

        # ۴. ارسال پیامک به مدیر کل (فقط در صورتی که کاربر جدید باشد)
        if is_new:
            try:
                from users.utils import send_pattern_sms
                # چون کلاس NotificationSettings در همین فایل است، مستقیم از آن استفاده می‌کنیم
                settings_obj = NotificationSettings.objects.first()
                if settings_obj and settings_obj.general_phones:
                    phones = [p.strip() for p in settings_obj.general_phones.split(',') if p.strip()]
                    name_to_send = self.full_name if self.full_name else self.phone_number
                    
                    for phone in phones:
                        send_pattern_sms(
                            phone, 
                            'admin_alert', 
                            {'token1': 'ثبت‌نام کاربر جدید', 'token2': name_to_send, 'token3': '-'}
                        )
            except Exception:
                pass
        
    class Meta:
        verbose_name = _("کاربر")
        verbose_name_plural = _("کاربران")

    def __str__(self):
        return self.full_name if self.full_name else self.phone_number

# 3. مدل کد تایید (OTP)
class OTP(models.Model):
    phone_number = models.CharField(max_length=11)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_otp(cls, phone):
        cls.objects.filter(phone_number=phone).delete()
        code = ''.join(random.choices(string.digits, k=5))
        return cls.objects.create(phone_number=phone, code=code)

    def is_valid(self):
        now = timezone.now()
        diff = now - self.created_at
        return diff.total_seconds() < 120
    
# --- اضافه شدن جدول تنظیمات پیامک مدیران (فاز ۴) ---
class NotificationSettings(models.Model):
    financial_phones = models.CharField(max_length=255, null=True, blank=True, verbose_name="شماره‌های مسئول مالی", help_text="شماره‌ها را با ویرگول انگلیسی (,) جدا کنید. (دریافت پیامک واریز و برداشت)")
    loan_phones = models.CharField(max_length=255, null=True, blank=True, verbose_name="شماره‌های مسئول وام", help_text="شماره‌ها را با ویرگول (,) جدا کنید. (دریافت پیامک درخواست وام)")
    general_phones = models.CharField(max_length=255, null=True, blank=True, verbose_name="شماره‌های مدیر کل", help_text="شماره‌ها را با ویرگول (,) جدا کنید. (دریافت پیامک‌های عمومی مثل انتقال امتیاز)")

    class Meta:
        verbose_name = "تنظیمات پیامک مدیران"
        verbose_name_plural = "تنظیمات پیامک مدیران"

    def __str__(self):
        return "تنظیمات شماره‌های دریافت‌کننده پیامک"