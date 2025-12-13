import requests
import urllib.parse

# --- تنظیمات پنل ---
ACCESS_HASH = '20b9b796-4f4e-4686-bd89-71a75545f1d8'
SMS_SENDER = '90000716'
ADMIN_PHONE = '09365466536'

PATTERNS = {
    'otp': '585fb9c1-dad9-4826-9685-514d50d98b96',
    'welcome': 'c4105767-d8c6-49d8-adf5-94855c4f5c54',
    'admin_alert': '02f32b11-b357-4efd-89dd-ad29e8a6c69a',
    'verify_deposit': 'cc3bfe14-8635-4bc1-b533-b4241fe44763',
    'verify_withdraw': '70a2166f-1162-49e4-9e6b-fd14a97d8789',
    'monthly_reminder': '1aa96cf6-b745-4d95-9846-ca13494386b1',
}

def send_pattern_sms(receptor, pattern_key, tokens):
    url = "https://smspanel.trez.ir/SendPatternWithUrl.ashx"
    pattern_code = PATTERNS.get(pattern_key)
    
    if not pattern_code:
        return False

    params = {
        'AccessHash': ACCESS_HASH,
        'PhoneNumber': SMS_SENDER,
        'PatternId': pattern_code,
        'RecNumber': receptor,
        'Smsclass': '1',
    }
    params.update(tokens)
    
    try:
        # استفاده از تایم‌اوت برای جلوگیری از قفل شدن سرور
        requests.get(url, params=params, timeout=5)
        return True
    except:
        return False