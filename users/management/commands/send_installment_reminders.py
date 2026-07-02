from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime
from accounting.models import LoanInstallment
from users.utils import send_pattern_sms

class Command(BaseCommand):
    help = 'بررسی اقساط و ارسال خودکار پیامک یادآوری'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔍 شروع بررسی اقساط...")
        
        # استفاده از منطقه زمانی تنظیم شده در جنگو (ایران) تا با ساعت لیارا تداخل نکند
        today = timezone.localdate()
        tomorrow = today + datetime.timedelta(days=1)
        
        self.stdout.write(f"📅 تاریخ امروز: {today} | تاریخ فردا (هدف جستجو): {tomorrow}")
        
        installments = LoanInstallment.objects.filter(
            is_paid=False, 
            due_date=tomorrow,
            loan__status='APPROVED'
        ).select_related('loan__user', 'loan__user__parent')

        count = installments.count()
        self.stdout.write(f"📊 تعداد اقساط یافت شده برای فردا: {count} مورد")

        if count == 0:
            self.stdout.write(self.style.WARNING("⚠️ هیچ قسطی برای فردا در سیستم ثبت نشده است! (اگر در حال تست هستید، باید سررسید یک قسط را به صورت دستی در پنل ادمین جنگو به فردا تغییر دهید)"))
            return

        success_count = 0
        for inst in installments:
            user = inst.loan.user
            
            if user.parent:
                phone_to_send = user.parent.phone_number
                name_to_send = f"{user.full_name} (زیرمجموعه)"
            else:
                phone_to_send = user.phone_number
                name_to_send = user.full_name
                
            amount_formatted = f"{inst.amount:,}"
            
            self.stdout.write(f"✉️ در حال درخواست ارسال به {name_to_send} ({phone_to_send}) برای مبلغ {amount_formatted} تومان...")
            
            try:
                result = send_pattern_sms(
                    receptor=phone_to_send,
                    pattern_key='installment_reminder',
                    tokens={
                        'token1': name_to_send,
                        'token2': str(inst.installment_number),
                        'token3': amount_formatted
                    }
                )
                if result:
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(f"✅ پاسخ سامانه پیامکی: موفق!"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ خطا: سامانه پیامکی تایید نکرد."))
            except Exception as e:
                self.stderr.write(f"❌ خطای غیرمنتظره در ارسال به {phone_to_send}: {e}")

        self.stdout.write(self.style.SUCCESS(f"🎉 عملیات پایان یافت. تعداد ارسال موفق: {success_count}"))