from rest_framework import serializers
from .models import Transaction, WithdrawalRequest, LoanRequest, PointLog
from users.models import User
from django.db.models import Sum
import datetime

class TransactionSerializer(serializers.ModelSerializer):
    target_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'transaction_type', 
            'date', 'effective_date', 
            'description', 'receipt_image', 'is_verified',
            'target_user_id', 
            'user_name'       
        ]
        read_only_fields = ['id', 'is_verified', 'effective_date'] 

    def validate(self, data):
        if 'WITHDRAWAL' not in str(data.get('transaction_type', '')):
            if not data.get('receipt_image'):
                raise serializers.ValidationError({"receipt_image": "لطفاً تصویر فیش واریزی را آپلود کنید."})
        return data

    def create(self, validated_data):
        target_user_id = validated_data.pop('target_user_id', None)
        request_user = self.context['request'].user
        user_to_save = request_user
        trans_type = validated_data.get('transaction_type')

        # --- سیستم هوشمند هدایت پول به حساب‌های فرهنگی ---
        cultural_types = {
            'SADAQAH': 'صدقه', 'WAQF': 'وقف (قدیم)', 'SACRIFICE': 'قربانی',
            'BOOK': 'کتاب', 'KHOMS_IMAM': 'سهم امام', 'KHOMS_SADAT': 'سهم سادات',
            'WAQF_GEN': 'وقف عام', 'WAQF_BOOK': 'وقف خاص کتاب', 
            'WAQF_MEDIA': 'وقف خاص تولید محتوا', 'WAQF_INFRA': 'وقف خاص زیرساخت'
        }

        if trans_type in cultural_types:
            from users.models import User
            c_name = f"حساب {cultural_types[trans_type]}"
            
            # جراحی ضدگلوله: ابتدا با نام و نقش جستجو می‌کنیم تا اگر حساب از قبل هست، همان را بردارد
            cultural_user = User.objects.filter(role='CULTURAL', full_name=c_name).first()
            
            if not cultural_user:
                # اگر حساب وجود ندارد، یک کد و شماره موبایل تصادفیِ یکتا می‌سازیم تا تداخل ایجاد نشود
                import random
                while True:
                    rand_suffix = str(random.randint(10000, 99999))
                    test_phone = f"09999{rand_suffix}"
                    test_code = f"9{rand_suffix}"
                    
                    # چک می‌کنیم که این شماره تصادفی قبلاً در سیستم ثبت نشده باشد
                    if not User.objects.filter(phone_number=test_phone).exists() and not User.objects.filter(membership_code=test_code).exists():
                        cultural_user = User.objects.create(
                            role='CULTURAL',
                            full_name=c_name,
                            phone_number=test_phone,
                            membership_code=test_code,
                            is_active=True
                        )
                        break
            user_to_save = cultural_user 
            
            desc = validated_data.get('description', '')
            validated_data['description'] = f"خیّر: {request_user.full_name} | {desc}"
            
        elif target_user_id:
            try:
                from users.models import User
                target_user = User.objects.get(id=target_user_id, parent=request_user)
                user_to_save = target_user 
            except User.DoesNotExist:
                pass 

        # حذف فیلد کاربر از داده‌ها برای جلوگیری از تداخل و ثبت نهایی تراکنش
        validated_data.pop('user', None)
        return Transaction.objects.create(user=user_to_save, **validated_data)
    
class WithdrawalRequestSerializer(serializers.ModelSerializer):
    target_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = WithdrawalRequest
        fields = ['id', 'amount', 'source_type', 'description', 'status', 'created_at', 'admin_note', 'target_user_id']
        read_only_fields = ['id', 'status', 'created_at', 'admin_note']

    def validate(self, data):
        request_user = self.context['request'].user
        target_user_id = data.get('target_user_id')
        user_to_check = request_user

        if target_user_id:
            from users.models import User
            try:
                if request_user.role in [User.Roles.ADMIN, User.Roles.OBSERVER]:
                    user_to_check = User.objects.get(id=target_user_id)
                else:
                    user_to_check = User.objects.get(id=target_user_id, parent=request_user)
            except User.DoesNotExist:
                pass

        self.context['resolved_user'] = user_to_check

        amount = data.get('amount')
        source_type = data.get('source_type')

        related_deposit_types = []
        related_withdrawal_types = []

        if source_type == 'LOAN':
            related_deposit_types = [Transaction.Types.LOAN_SAVING]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_SAVING]
        elif source_type == 'PROFIT':
            related_deposit_types = [Transaction.Types.MANUAL_PROFIT]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_MANUAL_PROFIT]
        elif source_type == 'QARD':
            related_deposit_types = [Transaction.Types.QARD_HASAN]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_QARD]
        elif source_type == 'SHORT_TERM':
            related_deposit_types = [Transaction.Types.SHORT_TERM]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_SHORT]
        elif source_type == 'LONG_TERM':
            related_deposit_types = [Transaction.Types.LONG_TERM, Transaction.Types.PROFIT_SAVING, Transaction.Types.MONTHLY_DEPOSIT]
            related_withdrawal_types = [Transaction.Types.WITHDRAWAL_LONG, Transaction.Types.WITHDRAWAL_PROFIT, Transaction.Types.WITHDRAWAL_MONTHLY]
        elif source_type == 'CULTURAL':
            related_deposit_types = [
                'SADAQAH', 'WAQF', 'SACRIFICE', 'BOOK', 'KHOMS_IMAM', 'KHOMS_SADAT', 'MANUAL_PROFIT',
                'WAQF_GEN', 'WAQF_BOOK', 'WAQF_MEDIA', 'WAQF_INFRA' # <--- این ۴ مورد اضافه شد
            ]
            related_withdrawal_types = ['W_CULTURAL']

        total_deposited = Transaction.objects.filter(
            user=user_to_check, transaction_type__in=related_deposit_types, is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        total_withdrawn = Transaction.objects.filter(
            user=user_to_check, transaction_type__in=related_withdrawal_types, is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        current_balance = total_deposited - total_withdrawn

        if source_type == 'LONG_TERM' or source_type == 'CULTURAL':
            import datetime
            three_months_ago = datetime.date.today() - datetime.timedelta(days=90)
            
            if getattr(user_to_check, 'role', '') == 'CULTURAL':
                if amount > current_balance:
                    raise serializers.ValidationError({"amount": f"موجودی این حساب فرهنگی کافی نیست. موجودی: {current_balance:,} تومان"})
            else:
                unlocked_deposits = Transaction.objects.filter(
                    user=user_to_check, transaction_type__in=related_deposit_types, is_verified=True, effective_date__lte=three_months_ago
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                available_balance = max(0, unlocked_deposits - total_withdrawn)
                
                if amount > available_balance:
                    raise serializers.ValidationError({
                        "amount": f"مبلغ درخواستی بلوکه است. موجودی قابل برداشت (که ۳ ماه از آن گذشته) {available_balance:,} تومان می‌باشد."
                    })
        else:
            if amount > current_balance:
                raise serializers.ValidationError({
                    "amount": f"موجودی این حساب کافی نیست. موجودی فعلی: {current_balance:,} تومان"
                })

        return data

    def create(self, validated_data):
        target_user_id = validated_data.pop('target_user_id', None)
        user_to_save = self.context['request'].user
        if target_user_id:
            from users.models import User
            try:
                if user_to_save.role in [User.Roles.ADMIN, User.Roles.OBSERVER]:
                    user_to_save = User.objects.get(id=target_user_id)
                else:
                    user_to_save = User.objects.get(id=target_user_id, parent=user_to_save)
            except User.DoesNotExist:
                pass

        validated_data.pop('user', None)
        return WithdrawalRequest.objects.create(user=user_to_save, **validated_data)

class LoanRequestSerializer(serializers.ModelSerializer):
    target_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = LoanRequest
        fields = ['id', 'amount', 'description', 'status', 'points_cost', 'created_at', 'target_user_id']
        read_only_fields = ['id', 'status', 'points_cost', 'created_at']

    def validate(self, data):
        amount = data.get('amount')
        request_user = self.context['request'].user
        target_user_id = data.get('target_user_id')
        user_to_check = request_user

        # --- جراحی: پیدا کردن کاربر واقعی (سرپرست یا زیرمجموعه) ---
        if target_user_id:
            from users.models import User
            try:
                if request_user.role in [User.Roles.ADMIN, User.Roles.OBSERVER]:
                    user_to_check = User.objects.get(id=target_user_id)
                else:
                    user_to_check = User.objects.get(id=target_user_id, parent=request_user)
            except User.DoesNotExist:
                pass

        self.context['resolved_user'] = user_to_check
        user = user_to_check
        
       

        today = datetime.date.today()
        
        loan_transactions = Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.LOAN_SAVING, is_verified=True
        ).order_by('date')
        
        time_points = 0
        if loan_transactions.exists():
            first_deposit = loan_transactions.first()
            days_passed_since_start = (today - first_deposit.effective_date).days
            
            if days_passed_since_start >= 90:
                for trans in loan_transactions:
                    days_active = (today - trans.effective_date).days
                    if days_active > 0:
                        daily_score = (trans.amount / 1000000) * 7000
                        time_points += int(daily_score * days_active)
        
        donation_total = Transaction.objects.filter(
            user=user, transaction_type='SADAQAH', is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        donation_points = int(donation_total * 0.20)
        
        referral_count = Transaction.objects.filter(
            user__referral_code=user.membership_code, transaction_type=Transaction.Types.MEMBERSHIP_FEE, is_verified=True
        ).values('user').distinct().count()
        referral_points = (referral_count // 5) * 1000000

        manual_points = PointLog.objects.filter(user=user).aggregate(Sum('points'))['points__sum'] or 0

        total_eligible_points = time_points + donation_points + referral_points + manual_points

        if amount > total_eligible_points:
            raise serializers.ValidationError({
                "amount": f"امتیاز شما کافی نیست. حداکثر امتیاز قابل استفاده: {total_eligible_points:,} تومان"
            })

        return data

    def create(self, validated_data):
        target_user_id = validated_data.pop('target_user_id', None)
        validated_data['points_cost'] = validated_data.get('amount')
        user = self.context.get('resolved_user', self.context['request'].user)
        validated_data.pop('user', None)
        return LoanRequest.objects.create(user=user, **validated_data)
    
class PointTransferSerializer(serializers.Serializer):
    target_user_id = serializers.IntegerField(required=False, allow_null=True) # <--- اضافه شد
    target_membership_code = serializers.CharField(max_length=50, label="کد عضویت مقصد")
    points = serializers.IntegerField(min_value=1, label="میزان امتیاز")
    


class PointLogSerializer(serializers.ModelSerializer):
    description = serializers.CharField(read_only=True)
    
    class Meta:
        model = PointLog
        fields = ['id', 'points', 'log_type', 'description', 'created_at']

# --- فاز ۴: سریاالایزر اختصاصی مدیریت وام ---
class AdminLoanActionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    membership_code = serializers.CharField(source='user.membership_code', read_only=True)
    target_membership_code = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = LoanRequest
        fields = [
            'id', 'user_name', 'user_phone', 'membership_code', 'target_membership_code',
            'amount', 'description', 'status', 'points_cost', 'created_at',
            'duration_months', 'granted_date', 'is_manual'
        ]
        read_only_fields = ['id', 'user_name', 'user_phone', 'membership_code', 'created_at', 'points_cost']

    def validate(self, data):
        membership_code = data.get('target_membership_code')
        if data.get('is_manual'):
            data['points_cost'] = 0
            if self.instance is None and not membership_code:
                 raise serializers.ValidationError({"target_membership_code": "کد عضویت کاربر الزامی است."})
        elif self.instance is None:
             if not membership_code:
                 raise serializers.ValidationError({"target_membership_code": "کد عضویت کاربر الزامی است."})
             data['points_cost'] = data.get('amount')
             
        if self.instance is None and membership_code:
            from users.models import User
            try:
                user = User.objects.get(membership_code=membership_code)
                self.context['target_user'] = user
            except User.DoesNotExist:
                raise serializers.ValidationError({"target_membership_code": "کاربری با این کد عضویت یافت نشد."})
                
        return data

    def create(self, validated_data):
        validated_data.pop('target_membership_code', None)
        user = self.context.get('target_user')
        return LoanRequest.objects.create(user=user, **validated_data)
    

# =========================================================
# --- فاز ۵: سریالایزرهای سرمایه‌گذاری خارج از صندوق ---
# =========================================================
from django.db.models import Sum
from .models import ExternalInvestment, InvestmentTransaction

class InvestmentTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = InvestmentTransaction
        fields = '__all__'

class ExternalInvestmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    investment_type_display = serializers.CharField(source='get_investment_type_display', read_only=True)
    transactions = InvestmentTransactionSerializer(many=True, read_only=True)
    
    # فیلدهای محاسباتی برای نمایش وضعیت هر پروژه در جدول فرانت‌اند
    total_deposited = serializers.SerializerMethodField()
    total_withdrawn = serializers.SerializerMethodField()
    total_profit = serializers.SerializerMethodField()
    active_balance = serializers.SerializerMethodField()

    class Meta:
        model = ExternalInvestment
        fields = '__all__'

    def get_total_deposited(self, obj):
        return obj.transactions.filter(transaction_type='DEPOSIT').aggregate(Sum('amount'))['amount__sum'] or 0

    def get_total_withdrawn(self, obj):
        return obj.transactions.filter(transaction_type='WITHDRAWAL').aggregate(Sum('amount'))['amount__sum'] or 0

    def get_total_profit(self, obj):
        return obj.transactions.filter(transaction_type='PROFIT').aggregate(Sum('amount'))['amount__sum'] or 0

    def get_active_balance(self, obj):
        return self.get_total_deposited(obj) - self.get_total_withdrawn(obj)