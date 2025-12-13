from rest_framework import serializers
from .models import Transaction, WithdrawalRequest
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
        if data.get('transaction_type') != 'WITHDRAWAL':
            if not data.get('receipt_image'):
                raise serializers.ValidationError({"receipt_image": "لطفاً تصویر فیش واریزی را آپلود کنید."})
        return data

    def create(self, validated_data):
        # جدا کردن target_user_id از داده‌ها
        target_user_id = validated_data.pop('target_user_id', None)
        
        # کاربر پیش‌فرض = کاربری که لاگین کرده (پدر)
        user = self.context['request'].user
        
        # اگر target_user_id ارسال شده بود، چک کن که فرزندِ این پدر باشد
        if target_user_id:
            try:
                # تلاش برای پیدا کردن فرزند
                target_user = User.objects.get(id=target_user_id, parent=user)
                user = target_user # اگر پیدا شد، کاربر تراکنش می‌شود فرزند
            except User.DoesNotExist:
                # اگر آی‌دی نامعتبر بود یا فرزندش نبود، همان پدر می‌ماند (برای امنیت)
                pass
        
        # ساخت تراکنش با کاربر نهایی
        transaction = Transaction.objects.create(user=user, **validated_data)
        return transaction


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ['id', 'amount', 'description', 'status', 'created_at', 'admin_note']
        read_only_fields = ['id', 'status', 'created_at', 'admin_note']