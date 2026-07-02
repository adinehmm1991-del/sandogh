from django.core.management.base import BaseCommand
from users.models import User
from users.utils import send_pattern_sms
import jdatetime

class Command(BaseCommand):
    help = 'ارسال پیامک یادآوری پرداخت ماهیانه به اعضا'

    def handle(self, *args, **options):
        # چاپ نسخه برای اطمینان از آپدیت شدن کد
        self.stdout.write("--- Executing Script V4 (Correct Arguments) ---")
        
        today = jdatetime.date.today()
        self.stdout.write(f"Checking date: {today} (Day: {today.day})")

        # ⚠️ توجه: برای تست امروز، عدد روز جاری (مثلاً 2) را بگذارید.
        # بعد از اینکه تست موفق بود، این عدد را به 1 تغییر دهید.
        if today.day == 1: 
            self.stdout.write("Starting reminder process...")
            
            # فقط کاربرانی که تعهد ماهیانه دارند
            active_users = User.objects.filter(monthly_commitment__gt=0)
            
            count = 0
            for user in active_users:
                try:
                    # --- اصلاح نهایی ---
                    # آرگومان اول: شماره موبایل (receptor)
                    # آرگومان دوم: کلید پترن (pattern_key)
                    # آرگومان سوم: دیکشنری توکن‌ها (tokens)
                    send_pattern_sms(
                        user.phone_number,  
                        'monthly_reminder', 
                        {
                            'token1': user.full_name,
                            'token2': f"{user.monthly_commitment:,}"
                        }
                    )
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f"Sent to {user.full_name}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed for {user.phone_number}: {e}"))
            
            self.stdout.write(self.style.SUCCESS(f"Done! Sent {count} messages."))
        else:
            self.stdout.write(self.style.WARNING("Today is not the scheduled day."))