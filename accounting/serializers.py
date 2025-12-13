from rest_framework import serializers
# تغییر 1: اضافه کردن مدل‌های جدید به ایمپورت‌ها
from .models import Transaction, WithdrawalRequest, LoanRequest, PointLog
from users.models import User

class TransactionSerializer(serializers.ModelSerializer):
    # فیلد اختیاری برای دریافت شناسه فرزند (فقط نوشتنی)
    target_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # فیلد نمایشی برای نشان دادن نام صاحب تراکنش در لیست
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'transaction_type', 
            'date', 'effective_date', 
            'description', 'receipt_image', 'is_verified',
            'target_user_id', # <--- این فیلد حیاتی است
            'user_name'       # برای نمایش نام در پاسخ
        ]
        read_only_fields = ['id', 'is_verified', 'effective_date'] 

    def validate(self, data):
        # منطق شما: اگر برداشت نبود، تصویر فیش اجباری است
        if data.get('transaction_type') != 'WITHDRAWAL':
            if not data.get('receipt_image'):
                raise serializers.ValidationError({"receipt_image": "لطفاً تصویر فیش واریزی را آپلود کنید."})
        return data

    def create(self, validated_data):
        # منطق شما: مدیریت ثبت برای فرزند
        target_user_id = validated_data.pop('target_user_id', None)
        
        # کاربر پیش‌فرض = کاربری که لاگین کرده (پدر)
        user = self.context['request'].user
        
        # اگر target_user_id ارسال شده بود، چک کن که فرزندِ این پدر باشد
        if target_user_id:
            try:
                target_user = User.objects.get(id=target_user_id, parent=user)
                user = target_user # اگر پیدا شد، کاربر تراکنش می‌شود فرزند
            except User.DoesNotExist:
                pass
        
        transaction = Transaction.objects.create(user=user, **validated_data)
        return transaction


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        # تغییر 2: اضافه شدن source_type به فیلدها
        fields = ['id', 'amount', 'source_type', 'description', 'status', 'created_at', 'admin_note']
        read_only_fields = ['id', 'status', 'created_at', 'admin_note']


# --- کلاس‌های جدید (تغییرات اضافه شده) ---

# تغییر 3: سریالایزر درخواست وام
class LoanRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        fields = ['id', 'amount', 'description', 'status', 'points_cost', 'created_at']
        read_only_fields = ['id', 'status', 'points_cost', 'created_at']

# تغییر 4: سریالایزر فرم انتقال امتیاز
class PointTransferSerializer(serializers.Serializer):
    target_membership_code = serializers.CharField(max_length=50, label="کد عضویت مقصد")
    points = serializers.IntegerField(min_value=1, label="میزان امتیاز")

# تغییر 5: سریالایزر سوابق امتیاز
class PointLogSerializer(serializers.ModelSerializer):
    description = serializers.CharField(read_only=True)
    
    class Meta:
        model = PointLog
        fields = ['id', 'points', 'log_type', 'description', 'created_at']