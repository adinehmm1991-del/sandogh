import os
import django
import sys

# تنظیمات اولیه جنگو
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command

# باز کردن فایل با فرمت UTF-8 (که فارسی را پشتیبانی کند)
with open('data.json', 'w', encoding='utf-8') as f:
    print("درحال تهیه نسخه پشتیبان از اطلاعات...")
    try:
        # اجرای دستور dumpdata و ریختن نتیجه در فایل
        call_command(
            'dumpdata', 
            exclude=['auth.permission', 'contenttypes', 'sessions', 'admin.logentry'], 
            indent=2, 
            stdout=f
        )
        print("✅ فایل data.json با موفقیت ساخته شد.")
    except Exception as e:
        print(f"❌ خطا: {e}")