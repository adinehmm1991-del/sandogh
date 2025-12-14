from rest_framework import serializers
# تغییر 1: اضافه کردن مدل‌های جدید به ایمپورت‌ها
from .models import Transaction, WithdrawalRequest, LoanRequest, PointLog
from users.models import User
from django.db.models import Sum
import datetime

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


# ... (ایمپورت‌ها مثل قبل)
from django.db.models import Sum

# ... (TransactionSerializer مثل قبل باشد)

class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ['id', 'amount', 'source_type', 'description', 'status', 'created_at', 'admin_note']
        read_only_fields = ['id', 'status', 'created_at', 'admin_note']

    def validate(self, data):
        user = self.context['request'].user
        amount = data.get('amount')
        source_type = data.get('source_type')

        # تعیین نوع تراکنش‌های ورودی بر اساس منبع انتخابی
        related_deposit_types = []
        related_withdrawal_types = []

        if source_type == WithdrawalRequest.Source.LOAN_SAVING:
            related_deposit_types = [Transaction.Types.LOAN_SAVING]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_SAVING]
        
        elif source_type == WithdrawalRequest.Source.PROFIT_SAVING:
            related_deposit_types = [Transaction.Types.PROFIT_SAVING]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_PROFIT]
            
        elif source_type == WithdrawalRequest.Source.MONTHLY:
            related_deposit_types = [Transaction.Types.MONTHLY_DEPOSIT]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_MONTHLY]
            
        elif source_type == WithdrawalRequest.Source.QARD:
            related_deposit_types = [Transaction.Types.QARD_HASAN]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_QARD]

        # محاسبه موجودی دقیق آن حساب
        total_deposited = Transaction.objects.filter(
            user=user, 
            transaction_type__in=related_deposit_types, 
            is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        total_withdrawn = Transaction.objects.filter(
            user=user, 
            transaction_type__in=related_withdrawal_types, 
            is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # اگر برداشت‌های کلی قدیمی هم هست، سخت‌گیرانه برخورد نمی‌کنیم چون تفکیک نشده‌اند
        # اما برای سیستم جدید، موجودی دقیق را چک می‌کنیم
        current_balance = total_deposited - total_withdrawn

        if amount > current_balance:
            raise serializers.ValidationError({
                "amount": f"موجودی این حساب کافی نیست. موجودی فعلی: {current_balance:,} تومان"
            })

        return data


# --- کلاس‌های جدید (تغییرات اضافه شده) ---

# تغییر 3: سریالایزر درخواست وام
class LoanRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        fields = ['id', 'amount', 'description', 'status', 'points_cost', 'created_at']
        read_only_fields = ['id', 'status', 'points_cost', 'created_at']

    def validate(self, data):
        amount = data.get('amount')
        user = self.context['request'].user
        
        # 1. محدودیت سقف ۳۰ میلیون تومان
        if amount > 30000000:
            raise serializers.ValidationError({"amount": "سقف درخواست وام ۳۰ میلیون تومان است."})

        # 2. محاسبه امتیاز کاربر (دقیقاً مشابه منطق ویو)
        today = datetime.date.today()
        
        # الف) امتیاز زمانی
        loan_transactions = Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.LOAN_SAVING, is_verified=True
        )
        time_points = 0
        for trans in loan_transactions:
            days_active = (today - trans.effective_date).days
            if days_active > 0:
                daily_score = (trans.amount / 1000000) * 6000
                time_points += int(daily_score * days_active)
        
        # ب) امتیاز بلاعوض (۲۰ درصد)
        donation_total = Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.DONATION, is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        donation_points = int(donation_total * 0.20)
        
        # ج) امتیاز معرف
        referral_count = Transaction.objects.filter(
            user__referral_code=user.membership_code, transaction_type=Transaction.Types.MEMBERSHIP_FEE, is_verified=True
        ).values('user').distinct().count()
        referral_points = (referral_count // 5) * 1000000

        # د) امتیاز دستی/انتقالی (مثبت یا منفی)
        manual_points = PointLog.objects.filter(user=user).aggregate(Sum('points'))['points__sum'] or 0

        # جمع کل امتیازات
        total_eligible_points = time_points + donation_points + referral_points + manual_points

        # 3. بررسی موجودی امتیاز
        if amount > total_eligible_points:
            raise serializers.ValidationError({
                "amount": f"مبلغ درخواستی بیشتر از امتیاز شماست. حداکثر وام قابل دریافت: {total_eligible_points:,} تومان"
            })

        return data
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