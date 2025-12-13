from rest_framework import serializers
from .models import User

def clean_numbers(value):
    if value:
        value = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        arabic_digits = '٠١٢٣٤٥٦٧٨٩'
        english_digits = '0123456789'
        translation_table = str.maketrans(persian_digits + arabic_digits, english_digits * 2)
        return value.translate(translation_table)
    return value

# 1. فرم ثبت‌نام
class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['phone_number', 'full_name', 'national_code', 'password', 'referral_code', 'monthly_commitment']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_phone_number(self, value): return clean_numbers(value)
    def validate_password(self, value): return clean_numbers(value)
    def validate_national_code(self, value): return clean_numbers(value)
    def validate_referral_code(self, value): return clean_numbers(value)
    
    def validate_monthly_commitment(self, value):
        clean_val = clean_numbers(str(value))
        return clean_val if clean_val else None

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            national_code=validated_data.get('national_code', ''),
            referral_code=validated_data.get('referral_code', ''),
            monthly_commitment=validated_data.get('monthly_commitment', None),
        )
        return user

# 2. فرم ورود
class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField() # دوباره شد شماره موبایل
    password = serializers.CharField(write_only=True)

    def validate_phone_number(self, value): return clean_numbers(value)
    def validate_password(self, value): return clean_numbers(value)

# 3. فرم ویرایش پروفایل
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'full_name', 'national_code', 'gender', 'birth_date', 
            'card_number', 'shaba_number', 'monthly_commitment'
        ]

    def validate_national_code(self, value): return clean_numbers(value)
    def validate_card_number(self, value): return clean_numbers(value)
    def validate_shaba_number(self, value): return clean_numbers(value)
    def validate_monthly_commitment(self, value):
        clean_val = clean_numbers(str(value))
        return clean_val if clean_val else None

# 4. فرم درخواست فراموشی رمز
class ForgotPasswordRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    def validate_phone_number(self, value): return clean_numbers(value)

# 5. فرم تایید فراموشی رمز
class ForgotPasswordVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    def validate_phone_number(self, value): return clean_numbers(value)
    def validate_code(self, value): return clean_numbers(value)
    def validate_new_password(self, value): return clean_numbers(value)

# 6. تغییر رمز
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    def validate_old_password(self, value): return clean_numbers(value)
    def validate_new_password(self, value): return clean_numbers(value)

# سریالایزر افزودن عضو خانواده
# 3. افزودن عضو خانواده (اصلاح شده)
class AddFamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'national_code', 'gender', 'birth_date'] 

    def validate_national_code(self, value):
        # فقط تمیز کردن اعداد (حذف فاصله و تبدیل فارسی به انگلیسی)
        value = clean_numbers(value)
        
        # چک کردن تکراری بودن در کل سیستم (اختیاری: اگر می‌خواهید هر کد ملی فقط برای یک نفر باشد)
        # اگر می‌خواهید تکراری مجاز باشد، این ۳ خط پایین را حذف کنید:
        if User.objects.filter(national_code=value).exists():
            raise serializers.ValidationError("این کد ملی قبلاً در سیستم ثبت شده است.")
            
        return value