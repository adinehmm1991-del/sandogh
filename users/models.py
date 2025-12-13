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

    class Gender(models.TextChoices):
        MALE = 'MALE', _('آقا')
        FEMALE = 'FEMALE', _('خانم')

    # موبایل دوباره یکتا (Unique) شد
    phone_number = models.CharField(max_length=11, unique=True, verbose_name=_("شماره موبایل"))
    national_code = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("کد ملی"))
    membership_code = models.CharField(max_length=20, unique=True, editable=False, verbose_name=_("کد عضویت"))
    
    full_name = models.CharField(max_length=150, verbose_name=_("نام و نام خانوادگی"))
    gender = models.CharField(max_length=10, choices=Gender.choices, null=True, blank=True, verbose_name=_("جنسیت"))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ تولد"))
    social_id = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("آیدی پیام‌رسان"))
    
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.MEMBER, verbose_name=_("نقش"))
    
    card_number = models.CharField(max_length=16, null=True, blank=True, verbose_name=_("شماره کارت"))
    shaba_number = models.CharField(max_length=26, null=True, blank=True, verbose_name=_("شماره شبا"))
    
    referral_code = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("کد معرف"))
    monthly_commitment = models.BigIntegerField(null=True, blank=True, verbose_name=_("تعهد واریز ماهیانه (ریال)"))
    # فیلد جدید: سرپرست (برای اعضای خانواده)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='family_members', verbose_name="سرپرست")

    # نام کاربری دوباره شد موبایل
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.membership_code:
            last_user = User.objects.order_by('id').last()
            next_id = (last_user.id + 1) if last_user else 1
            self.membership_code = f"313{next_id}"
        super().save(*args, **kwargs)

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