from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
import datetime
from decimal import Decimal
from datetime import date

from .models import (
    Transaction, 
    ProfitPeriod, 
    ProfitDistribution, 
    WithdrawalRequest, 
    LoanRequest, 
    FundProfitAllocation,
    PointLog, 
    PointTransferRequest,
    add_jalali_months,
    ExternalInvestment, 
    InvestmentTransaction,
    LoanInstallment
)

from .serializers import (
    TransactionSerializer, 
    WithdrawalRequestSerializer, 
    LoanRequestSerializer, 
    PointTransferSerializer, 
    PointLogSerializer,
    AdminLoanActionSerializer,
    ExternalInvestmentSerializer, 
    InvestmentTransactionSerializer
)
from users.models import User

# --- تعریف لیست‌های کمکی ---
ALL_WITHDRAWAL_TYPES = [
    Transaction.Types.WITHDRAWAL_SHORT,
    Transaction.Types.WITHDRAWAL_LONG,
    Transaction.Types.WITHDRAWAL_SAVING,
    Transaction.Types.WITHDRAWAL_PROFIT,
    Transaction.Types.WITHDRAWAL_MONTHLY,
    Transaction.Types.WITHDRAWAL_QARD,
    Transaction.Types.WITHDRAWAL_OTHER,
    Transaction.Types.WITHDRAWAL_FEE,           # حق عضویت
    Transaction.Types.WITHDRAWAL_CULTURAL,      # امور فرهنگی
    Transaction.Types.WITHDRAWAL_MANUAL_PROFIT, # <--- مقصر اصلی! این مورد جا افتاده بود
    'WITHDRAWAL', # (برای سازگاری با داده‌های قدیمی)
]

PROFITABLE_TYPES = [
    Transaction.Types.SHORT_TERM, 
    Transaction.Types.LONG_TERM,
    Transaction.Types.MONTHLY_DEPOSIT, 
    Transaction.Types.PROFIT_SAVING
]

NON_PROFITABLE_TYPES = [
    Transaction.Types.LOAN_SAVING, 
    Transaction.Types.QARD_HASAN,
    Transaction.Types.MEMBERSHIP_FEE,
    'SADAQAH', 'SACRIFICE', 'BOOK', 'KHOMS_IMAM', 'KHOMS_SADAT', 'WAQF',
    'WAQF_GEN', 'WAQF_BOOK', 'WAQF_MEDIA', 'WAQF_INFRA' # <--- این خط اضافه شود
]

# --- بخش اول: ثبت و نمایش تراکنش‌ها ---
class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        family_ids = self.request.user.family_members.values_list('id', flat=True)
        all_ids = [self.request.user.id, *family_ids]
        
        target_id = self.request.query_params.get('user_id')
        if target_id:
             try: 
                 target = User.objects.get(id=target_id)
                 if target.id in all_ids:
                     return Transaction.objects.filter(user=target).order_by('-date')
             except: pass
        
        # --- جراحی: اگر آیدی کاربری ارسال نشد، فقط تراکنش‌های خود صاحب حساب نمایش داده شود ---
        return Transaction.objects.filter(user=self.request.user).order_by('-date')

    def perform_create(self, serializer):
        serializer.save()


# --- بخش دوم: محاسبه سود ---
class CalculateProfitView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, period_id):
        try:
            period = ProfitPeriod.objects.get(id=period_id)
        except ProfitPeriod.DoesNotExist:
            return Response({"error": "دوره مورد نظر یافت نشد."}, status=404)

        Transaction.objects.filter(profit_period=period).delete()
        ProfitDistribution.objects.filter(period=period).delete()

        total_days = (period.end_date - period.start_date).days
        number_of_steps = max(1, int(total_days / 30))
        step_duration = total_days / number_of_steps
        
        checkpoints = []
        for i in range(number_of_steps):
            cp_date = period.start_date + datetime.timedelta(days=(i + 1) * step_duration)
            checkpoints.append(cp_date)

        total_system_score = Decimal(0)
        distributed_profit = 0
        member_scores = {}

        members = User.objects.exclude(role=User.Roles.FUND_ACCOUNT)

        def get_balance_at(user, check_date, types):
            deposit = Transaction.objects.filter(
                user=user,
                effective_date__lte=check_date,
                transaction_type__in=types,
                is_verified=True
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            withdrawal = Transaction.objects.filter(
                user=user,
                effective_date__lte=check_date,
                transaction_type__in=ALL_WITHDRAWAL_TYPES, 
                is_verified=True
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            return max(0, deposit - withdrawal)

        for member in members:
            fee_dep = Transaction.objects.filter(user=member, transaction_type=Transaction.Types.MEMBERSHIP_FEE, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            fee_wit = Transaction.objects.filter(user=member, transaction_type='W_FEE', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            has_paid_fee = (fee_dep - fee_wit) > 0

            # --- تغییر مهم: حساب‌های فرهنگی نیازی به حق عضویت ندارند و سود می‌گیرند ---
            if not has_paid_fee and member.role != 'CULTURAL':
                continue 

            base_capital = get_balance_at(member, period.start_date, PROFITABLE_TYPES)
            final_user_score = Decimal(int(base_capital / 1000000)) * 1
            previous_balance = int(base_capital / 1000000)

            for i, cp_date in enumerate(checkpoints):
                current_balance_raw = get_balance_at(member, cp_date, PROFITABLE_TYPES)
                current_balance = int(current_balance_raw / 1000000)
                added_capital = max(0, current_balance - previous_balance)
                weight = Decimal(number_of_steps - i) / Decimal(number_of_steps)
                step_score = Decimal(added_capital) * weight
                final_user_score += step_score
                previous_balance = current_balance

            if final_user_score > 0:
                member_scores[member.id] = final_user_score
                total_system_score += final_user_score

        other_capitals = Transaction.objects.filter(
            effective_date__lte=period.end_date,
            transaction_type__in=NON_PROFITABLE_TYPES,
            is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        other_scores = Decimal(int(other_capitals / 1000000))
        final_denominator = total_system_score + other_scores

        distributable_profit = period.total_profit_amount * 0.5
        
        if final_denominator > 0:
            rate = distributable_profit / float(final_denominator)
        else:
            rate = 0

        for member_id, score in member_scores.items():
            amount = int(float(score) * rate)
            ProfitDistribution.objects.create(
                period=period, user_id=member_id, calculated_score=score, profit_amount=amount
            )
            if amount > 0:
                Transaction.objects.create(
                    user_id=member_id, amount=amount, transaction_type=Transaction.Types.PROFIT_SAVING,
                    date=datetime.datetime.now(), effective_date=period.end_date, is_verified=True,
                    description=f"سود دوره {period.name}", profit_period=period
                )
            distributed_profit += amount

        fund_share = period.total_profit_amount - distributed_profit
        fund_user = User.objects.filter(role=User.Roles.FUND_ACCOUNT).first()
        if fund_user:
            ProfitDistribution.objects.create(
                period=period, user=fund_user, calculated_score=other_scores, profit_amount=fund_share
            )
            if fund_share > 0:
                Transaction.objects.create(
                    user=fund_user, amount=fund_share, transaction_type=Transaction.Types.PROFIT_SAVING,
                    date=datetime.datetime.now(), effective_date=period.end_date, is_verified=True,
                    description=f"سود دوره {period.name}", profit_period=period
                )
        fund_share = period.total_profit_amount - distributed_profit
        fund_user = User.objects.filter(role=User.Roles.FUND_ACCOUNT).first()
        if fund_user:
            ProfitDistribution.objects.create(
                period=period, user=fund_user, calculated_score=other_scores, profit_amount=fund_share
            )
            if fund_share > 0:
                Transaction.objects.create(
                    user=fund_user, amount=fund_share, transaction_type=Transaction.Types.PROFIT_SAVING,
                    date=datetime.datetime.now(), effective_date=period.end_date, is_verified=True,
                    description=f"سود دوره {period.name}", profit_period=period
                )
        
        # --- کدهای جدید: استخراج هوشمندِ سهم پس‌انداز وام و ذخیره در جدول تخصیص ---
        loan_saving_capital = Transaction.objects.filter(
            effective_date__lte=period.end_date,
            transaction_type=Transaction.Types.LOAN_SAVING,
            is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        loan_saving_score = Decimal(int(loan_saving_capital / 1000000))
        loan_saving_profit_share = int(float(loan_saving_score) * rate)

        FundProfitAllocation.objects.update_or_create(
            date=period.end_date,
            defaults={
                'total_profit': period.total_profit_amount,
                'loan_saving_share': loan_saving_profit_share,
                'description': f"تخصیص خودکار از سود دوره {period.name}"
            }
        )   
        period.is_calculated = True
        period.save()

        return Response({"status": "OK"})


class UserDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        target_id = request.query_params.get('user_id')
        user = request.user
        
        if target_id:
            try:
                user = User.objects.get(id=target_id, parent=request.user)
            except User.DoesNotExist:
                pass 
        
        today = datetime.date.today()

        def get_sum(queryset):
            return queryset.aggregate(Sum('amount'))['amount__sum'] or 0

        # ۱. بررسی وضعیت فعالیت کاربر
        fee_dep = get_sum(Transaction.objects.filter(user=user, transaction_type=Transaction.Types.MEMBERSHIP_FEE, is_verified=True))
        fee_wit = get_sum(Transaction.objects.filter(user=user, transaction_type=Transaction.Types.WITHDRAWAL_FEE, is_verified=True))
        has_paid_fee = (fee_dep - fee_wit) > 0
        is_user_active = has_paid_fee or user.role == 'CULTURAL'

        # ۲. محاسبه امتیازات وام
        loan_saving_points = 0
        locked_saving_points = 0
        total_loan_points = 0
        first_deposit_date = None
        days_passed_since_start = 0
        days_remaining_to_unlock = 0
        is_eligible_for_loan = False

        loan_deposits = Transaction.objects.filter(user=user, transaction_type=Transaction.Types.LOAN_SAVING, is_verified=True).order_by('effective_date')
        loan_withdrawals = Transaction.objects.filter(user=user, transaction_type=Transaction.Types.WITHDRAWAL_SAVING, is_verified=True)

        if is_user_active:
            for t in loan_deposits:
                days_active = (today - t.effective_date).days
                if days_active > 0:
                    total_loan_points += int((t.amount / 1000000) * 7000 * days_active)
                    
            for w in loan_withdrawals:
                days_active = (today - w.effective_date).days
                if days_active > 0:
                    total_loan_points -= int((w.amount / 1000000) * 7000 * days_active)
                
            if loan_deposits.exists():
                first_deposit_date = loan_deposits.first().effective_date
                days_passed_since_start = (today - first_deposit_date).days
                if days_passed_since_start >= 90:
                    is_eligible_for_loan = True
                    loan_saving_points = max(0, total_loan_points)
                else:
                    locked_saving_points = max(0, total_loan_points)
                    days_remaining_to_unlock = 90 - days_passed_since_start

        donation_points = 0
        referral_loan_points = 0
        active_referrals_count = 0
        if is_user_active:
            donation_total = get_sum(Transaction.objects.filter(user=user, transaction_type='SADAQAH', is_verified=True))
            donation_points = int(donation_total * 0.20)
            
            active_referrals_count = Transaction.objects.filter(
                user__referral_code=user.membership_code,
                transaction_type=Transaction.Types.MEMBERSHIP_FEE,
                is_verified=True
            ).values('user').distinct().count()
            referral_loan_points = (active_referrals_count // 5) * 1000000

        manual_points = PointLog.objects.filter(user=user).aggregate(Sum('points'))['points__sum'] or 0
        total_unlocked_limit = (donation_points + loan_saving_points + referral_loan_points) + manual_points

        # ۳. محاسبه موجودی خالص تفکیک‌شده برای هر صندوق
        st_dep = get_sum(Transaction.objects.filter(user=user, transaction_type=Transaction.Types.SHORT_TERM, is_verified=True))
        st_wit = get_sum(Transaction.objects.filter(user=user, transaction_type=Transaction.Types.WITHDRAWAL_SHORT, is_verified=True))
        st_bal = max(0, st_dep - st_wit)

        # ⚠️ اصلاح نهایی: پس‌انداز سود (PROFIT_SAVING) دقیقاً به حساب بلندمدت اضافه شد
        lt_dep = get_sum(Transaction.objects.filter(user=user, transaction_type__in=[Transaction.Types.LONG_TERM, Transaction.Types.MONTHLY_DEPOSIT, Transaction.Types.PROFIT_SAVING], is_verified=True))
        lt_wit = get_sum(Transaction.objects.filter(user=user, transaction_type__in=[Transaction.Types.WITHDRAWAL_LONG, Transaction.Types.WITHDRAWAL_MONTHLY, Transaction.Types.WITHDRAWAL_PROFIT], is_verified=True))
        lt_bal = max(0, lt_dep - lt_wit)

        loan_dep_sum = get_sum(loan_deposits)
        loan_wit_sum = get_sum(loan_withdrawals)
        loan_bal = max(0, loan_dep_sum - loan_wit_sum)

        qard_dep = get_sum(Transaction.objects.filter(user=user, transaction_type=Transaction.Types.QARD_HASAN, is_verified=True))
        qard_wit = get_sum(Transaction.objects.filter(user=user, transaction_type=Transaction.Types.WITHDRAWAL_QARD, is_verified=True))
        qard_bal = max(0, qard_dep - qard_wit)

        fee_bal = max(0, fee_dep - fee_wit)

        # ۴. محاسبه دقیق سود (کارت سود حالا فقط و فقط متعلق به MANUAL_PROFIT است)
        profit_deposits = get_sum(Transaction.objects.filter(
            user=user, 
            transaction_type=Transaction.Types.MANUAL_PROFIT, 
            is_verified=True
        ))
        profit_withdrawn = get_sum(Transaction.objects.filter(
            user=user, 
            transaction_type=Transaction.Types.WITHDRAWAL_MANUAL_PROFIT, 
            is_verified=True
        ))
        net_profit_available = max(0, profit_deposits - profit_withdrawn)

        # ۵. موجودی کل
        current_balance = st_bal + lt_bal + loan_bal + qard_bal + fee_bal + net_profit_available
        
        return Response({
            "full_name": user.full_name if user.full_name else user.phone_number,
            "membership_code": user.membership_code,
            "role": user.role,
            "can_manage_loans": user.can_manage_loans,
            "can_manage_investments": getattr(user, 'can_manage_investments', False),
            "current_balance": current_balance,
            "total_profit_received": net_profit_available,  # مانده سود آزاد
            "total_profit_credited": profit_deposits,      # کل سودهای واریزی زنده
            "profit_withdrawn": profit_withdrawn,          # کل سود برداشت شده
            "balances": {
                "short_term": st_bal,
                "long_term": lt_bal,
                "loan_saving": loan_bal,
                "qard": qard_bal,
                "fee": fee_bal
            },
            "status": "فعال" if is_user_active else "غیرفعال",
            "is_active": is_user_active,
            "referrals_count": active_referrals_count,
            "loan_points_details": {
                "total_limit": total_unlocked_limit + locked_saving_points,
                "locked_limit": locked_saving_points,
                "from_donations": donation_points,
                "from_savings": loan_saving_points + locked_saving_points,
                "from_referrals": referral_loan_points,
                "from_transfers": manual_points,
                "loan_amount_limit": total_unlocked_limit,
                "has_loan_deposit": first_deposit_date is not None,
                "is_eligible": is_eligible_for_loan,
                "days_passed": days_passed_since_start,
                "days_remaining": days_remaining_to_unlock,
            }
        })
    
# --- بخش چهارم: گزارش مدیریتی (اصلاح شده برای نمایش سود حساب‌های فرهنگی) ---
# --- بخش چهارم: گزارش مدیریتی (ترازنامه دقیق با محاسبه مقادیر خالص) ---
class GeneralReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in [User.Roles.ADMIN, User.Roles.OBSERVER]:
            return Response({"error": "شما دسترسی ندارید."}, status=403)

        all_members = User.objects.exclude(role=User.Roles.FUND_ACCOUNT)
        total_members_count = all_members.count()
        active_members_count = 0
        inactive_members_count = 0

        for member in all_members:
            fee_dep = Transaction.objects.filter(user=member, transaction_type=Transaction.Types.MEMBERSHIP_FEE, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            fee_wit = Transaction.objects.filter(user=member, transaction_type='W_FEE', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            has_paid_fee = (fee_dep - fee_wit) > 0
            
            if member.is_active and (has_paid_fee or member.role == 'CULTURAL'): 
                active_members_count += 1
            else: 
                inactive_members_count += 1
        
        # --- تابع جادویی: محاسبه موجودی خالصِ هر دسته (واریزی‌ها منهای برداشت‌ها) ---
        def get_net_category(dep_types, wit_types):
            deps = Transaction.objects.filter(transaction_type__in=dep_types, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            wits = Transaction.objects.filter(transaction_type__in=wit_types, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            return deps - wits

        # ۱. خالص پس‌اندازهای سودده
        prof_deps = ['SHORT_TERM', 'LONG_TERM', 'MONTHLY_DEPOSIT', 'PROFIT_SAVING', 'MANUAL_PROFIT']
        prof_wits = ['W_SHORT', 'W_LONG', 'W_MONTHLY', 'W_PROFIT', 'W_MAN_PROFIT', 'WITHDRAWAL_OTHER', 'WITHDRAWAL']
        net_profit_saving = get_net_category(prof_deps, prof_wits)

        # ۲. خالص پس‌انداز وام
        net_loan_saving = get_net_category(['LOAN_SAVING'], ['W_SAVING'])

        # ۳. خالص قرض‌الحسنه
        net_qard = get_net_category(['QARD_HASAN'], ['W_QARD'])
        
        # ۴. خالص حق عضویت‌های پرداخت شده
        net_fee = get_net_category(['FEE'], ['W_FEE'])

        # ۵. خالص حساب‌های فرهنگی
        def get_cultural_balance(t_type, fa_name):
            try:
                cultural_user = User.objects.get(role='CULTURAL', full_name=f"حساب {fa_name}")
                deposits = Transaction.objects.filter(
                    user=cultural_user,
                    transaction_type__in=[t_type, 'MANUAL_PROFIT', 'PROFIT_SAVING'],
                    is_verified=True
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                withdrawals = Transaction.objects.filter(
                    user=cultural_user,
                    transaction_type__in=ALL_WITHDRAWAL_TYPES,
                    is_verified=True
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                return max(0, deposits - withdrawals)
            except User.DoesNotExist:
                return 0

        c_sadaqah = get_cultural_balance('SADAQAH', 'صدقه')
        c_sacrifice = get_cultural_balance('SACRIFICE', 'قربانی')
        c_book = get_cultural_balance('BOOK', 'کتاب')
        c_imam = get_cultural_balance('KHOMS_IMAM', 'سهم امام')
        c_sadat = get_cultural_balance('KHOMS_SADAT', 'سهم سادات')
        c_waqf = get_cultural_balance('WAQF', 'وقف (قدیم)')
        c_waqf_gen = get_cultural_balance('WAQF_GEN', 'وقف عام')
        c_waqf_book = get_cultural_balance('WAQF_BOOK', 'وقف خاص کتاب')
        c_waqf_media = get_cultural_balance('WAQF_MEDIA', 'وقف خاص تولید محتوا')
        c_waqf_infra = get_cultural_balance('WAQF_INFRA', 'وقف خاص زیرساخت')
        
        total_cultural = (c_sadaqah + c_sacrifice + c_book + c_imam + c_sadat + 
                          c_waqf + c_waqf_gen + c_waqf_book + c_waqf_media + c_waqf_infra)

        # --- ۶. فرمول قطعی موجودی کل صندوق (جمع تمام مقادیرِ خالص) ---
        total_capital = net_profit_saving + net_loan_saving + net_qard + net_fee + total_cultural
        
        total_withdrawal = Transaction.objects.filter(
            transaction_type__in=ALL_WITHDRAWAL_TYPES,
            is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_commitments = User.objects.aggregate(Sum('monthly_commitment'))['monthly_commitment__sum'] or 0

       # تفکیک دقیق کوتاه‌مدت و بلندمدت
        net_short_term = get_net_category(['SHORT_TERM'], ['W_SHORT'])
        net_long_term = get_net_category(['LONG_TERM', 'MONTHLY', 'PROFIT_SAVING', 'MANUAL_PROFIT'], ['W_LONG', 'W_MONTHLY', 'W_PROFIT', 'W_MAN_PROFIT', 'WITHDRAWAL_OTHER', 'WITHDRAWAL', 'W_CULTURAL'])

        return Response({
            "total_members": total_members_count,
            "active_members": active_members_count,
            "inactive_members": inactive_members_count,
            "total_capital": total_capital,
            "total_qard": net_qard,
            "total_short_term": net_short_term, # تفکیک شده
            "total_long_term": net_long_term,   # تفکیک شده
            "total_loan_saving": net_loan_saving,
            "total_donation": c_sadaqah,
            "total_sacrifice": c_sacrifice,
            "total_book": c_book,
            "total_khoms_imam": c_imam,
            "total_khoms_sadat": c_sadat,
            "total_waqf": c_waqf,
            "total_waqf_gen": c_waqf_gen,
            "total_waqf_book": c_waqf_book,
            "total_waqf_media": c_waqf_media,
            "total_waqf_infra": c_waqf_infra,
        })
# --- بخش پنجم: درخواست برداشت ---
class WithdrawalRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        target_id = self.request.query_params.get('user_id')
        
        # اگر مدیر وارد پرونده زیرمجموعه شده بود، فقط برداشت‌های زیرمجموعه را نشان بده
        if target_id:
            try:
                target = User.objects.get(id=target_id, parent=self.request.user)
                return WithdrawalRequest.objects.filter(user=target).order_by('-created_at')
            except User.DoesNotExist:
                pass
                
        # --- جراحی: اگر آیدی کاربری ارسال نشد، فقط برداشت‌های خود صاحب حساب نمایش داده شود ---
        return WithdrawalRequest.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save()

class LoanRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        target_id = self.request.query_params.get('user_id')
        if target_id:
            try:
                target = User.objects.get(id=target_id, parent=self.request.user)
                return LoanRequest.objects.filter(user=target).order_by('-created_at')
            except User.DoesNotExist:
                pass
        return LoanRequest.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # ذخیره با کاربر استخراج شده در سریالایزر انجام می‌شود
        serializer.save()

class PointLogListView(generics.ListAPIView):
    serializer_class = PointLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PointLog.objects.filter(user=self.request.user).order_by('-created_at')

# --- بخش هشتم: درخواست انتقال امتیاز ---
class PointTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # --- متد جدید برای ارسال لیست تاریخچه انتقال امتیاز ---
    def get(self, request):
        user = request.user
        target_id = request.query_params.get('user_id')
        if target_id:
            try:
                user = User.objects.get(id=target_id, parent=request.user)
            except User.DoesNotExist:
                pass
        
        import jdatetime
        from django.utils import timezone
        requests = PointTransferRequest.objects.filter(sender=user).order_by('-created_at')
        
        data = [{
            "id": r.id,
            "receiver_name": r.receiver.full_name,
            "receiver_code": r.receiver.membership_code,
            "amount": r.amount,
            "status": r.get_status_display(),
            "date": jdatetime.date.fromgregorian(date=timezone.localtime(r.created_at).date()).strftime("%Y/%m/%d")
        } for r in requests]
        
        return Response(data)

    def post(self, request):
        serializer = PointTransferSerializer(data=request.data)
        if serializer.is_valid():
            request_user = request.user
            target_user_id = serializer.validated_data.get('target_user_id')
            user = request_user
            
            if target_user_id:
                try:
                    user = User.objects.get(id=target_user_id, parent=request_user)
                except User.DoesNotExist:
                    return Response({"error": "کاربر زیرمجموعه یافت نشد."}, status=400)
            
            target_code = serializer.validated_data['target_membership_code']
            points = serializer.validated_data['points']

            if points <= 0:
                return Response({"error": "امتیاز باید بیشتر از صفر باشد."}, status=400)

            try:
                target_user = User.objects.get(membership_code=target_code)
            except User.DoesNotExist:
                return Response({"error": "کد عضویت مقصد یافت نشد."}, status=400)
            
            if target_user.id == user.id:
                return Response({"error": "نمی‌توانید به خودتان انتقال دهید."}, status=400)

            # --- فرمول دقیق و یکپارچه با داشبورد (با احتساب برداشت‌های وام و سقف صفر) ---
            today = datetime.date.today()
            loan_deposits = Transaction.objects.filter(user=user, transaction_type='LOAN_SAVING', is_verified=True).order_by('effective_date')
            loan_withdrawals = Transaction.objects.filter(user=user, transaction_type='W_SAVING', is_verified=True)
            
            total_loan_points = 0
            for t in loan_deposits:
                days_active = (today - t.effective_date).days
                if days_active > 0:
                    total_loan_points += int((t.amount / 1000000) * 7000 * days_active)
                    
            for w in loan_withdrawals:
                days_active = (today - w.effective_date).days
                if days_active > 0:
                    total_loan_points -= int((w.amount / 1000000) * 7000 * days_active)
            
            loan_saving_points = 0
            if loan_deposits.exists():
                first_date = loan_deposits.first().effective_date
                if (today - first_date).days >= 90:
                    loan_saving_points = max(0, total_loan_points)
            
            don = Transaction.objects.filter(user=user, transaction_type='SADAQAH', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            don_points = int(don * 0.20)
            
            refs = Transaction.objects.filter(user__referral_code=user.membership_code, transaction_type='FEE', is_verified=True).values('user').distinct().count()
            ref_points = (refs // 5) * 1000000
            
            man_points = PointLog.objects.filter(user=user).aggregate(Sum('points'))['points__sum'] or 0
            
            # محاسبه دقیق موجودی امتیاز با اعمال سقف صفر برای جلوگیری از منفی شدن
            current_total_points = max(0, loan_saving_points + don_points + ref_points + man_points)

            if current_total_points < points:
                return Response({"error": f"امتیاز آزاد شما کافی نیست یا حساب شما فاقد اعتبار است. موجودی قابل انتقال: {current_total_points:,}"}, status=400)

            PointTransferRequest.objects.create(
                sender=user,
                receiver=target_user,
                amount=points,
                status=PointTransferRequest.Status.APPROVED, 
                description=f"انتقال مستقیم امتیاز به {target_user.full_name} ({target_user.membership_code})"
            )

            return Response({"message": "✅ انتقال امتیاز با موفقیت انجام شد."})
        
        return Response(serializer.errors, status=400)
    
class LoanDashboardReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_loans', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)
        
        # ۱. کل پس‌انداز وام (هم اعضا و هم سودهایی که به حساب صندوق واریز شده)
        deposits = Transaction.objects.filter(transaction_type='LOAN_SAVING', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
        withdrawals = Transaction.objects.filter(transaction_type='W_SAVING', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
        total_loan_saving = deposits - withdrawals

        # ۲. ظرفیت پایه وام‌دهی (فقط ۵۰٪ کل پس‌انداز وام) - سود مجزا حذف شد چون داخل موجودی است
        base_capacity = int(total_loan_saving * 0.5)

        # ۳. محاسبه اقساط پرداخت شده واقعی
        approved_loans = LoanRequest.objects.filter(status='APPROVED', granted_date__isnull=False)
        
        total_paid_loans = 0
        total_actual_returned = 0

        for loan in approved_loans:
            total_paid_loans += loan.amount
            paid_sum = loan.installments.filter(is_paid=True).aggregate(Sum('amount'))['amount__sum'] or 0
            total_actual_returned += paid_sum

        total_actual_returned = int(total_actual_returned)
        
        # ۵. سرمایه درگیر فعلی
        active_debt = total_paid_loans - total_actual_returned
        
        # ۶. ظرفیت آزاد واقعی برای وام‌دهی
        free_capacity = base_capacity - active_debt

        return Response({
            "total_loan_saving": total_loan_saving,
            "total_allocated_profit": 0, # این را صفر می‌فرستیم تا فرانت‌اند دچار خطای Undefined نشود
            "base_capacity": base_capacity,
            "total_paid_loans": total_paid_loans,
            "total_virtual_returned": total_actual_returned, 
            "active_debt": active_debt,
            "free_capacity": free_capacity
        })
    
# --- فاز ۴: API مدیریت لیست وام‌ها برای مدیر ---
class AdminLoanManagementView(generics.ListCreateAPIView):
    serializer_class = AdminLoanActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # فقط مدیران یا کسانی که تیک دسترسی وام دارند
        if self.request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(self.request.user, 'can_manage_loans', False):
            return LoanRequest.objects.none()
        
        # برگرداندن تمام وام‌ها (جدیدترین در ابتدا)
        return LoanRequest.objects.all().order_by('-created_at')

    def list(self, request, *args, **kwargs):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_loans', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_loans', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)
        return super().create(request, *args, **kwargs)

class AdminLoanDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AdminLoanActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LoanRequest.objects.all()

    def update(self, request, *args, **kwargs):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_loans', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)
        
        # ۱. انجام عملیات ذخیره (آپدیت پرونده اصلی وام)
        response = super().update(request, *args, **kwargs)
        
        # ۲. دریافت اطلاعات جدید پرونده از دیتابیس
        instance = self.get_object()
        
        # ۳. --- جراحی هوشمند: آپدیت همگامِ اقساط ---
        if instance.status == 'APPROVED' and instance.granted_date and instance.duration_months > 0:
            from accounting.models import LoanInstallment
            import datetime
            
            installments = LoanInstallment.objects.filter(loan=instance)
            has_paid_installments = installments.filter(is_paid=True).exists()
            
            if not has_paid_installments:
                # الف) اگر هیچ قسطی پرداخت نشده، اقساط قبلی را پاک کرده و با تاریخ و تعداد ماه‌های جدید از نو می‌سازیم
                installments.delete()
                installment_amount = instance.amount // instance.duration_months
                installments_to_create = []
                for i in range(1, instance.duration_months + 1):
                    due = add_jalali_months(instance.granted_date, i)
                    installments_to_create.append(
                        LoanInstallment(loan=instance, installment_number=i, due_date=due, amount=installment_amount)
                    )
                LoanInstallment.objects.bulk_create(installments_to_create)
            else:
                # ب) اگر حتی یک قسط پرداخت شده، برای جلوگیری از به هم ریختن تراز مالی، فقط تاریخ سررسیدها را شیفت می‌دهیم
                for inst in installments:
                    inst.due_date = add_jalali_months(instance.granted_date, inst.installment_number)
                    inst.save()
                    
        return response
# --- فاز ۴: گزارش وضعیت پس‌انداز اعضا برای داشبورد وام ---
class AdminLoanSavingsReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_loans', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)

        users_with_savings = User.objects.filter(
            transaction__transaction_type='LOAN_SAVING',
            transaction__is_verified=True
        ).distinct()

        today = datetime.date.today()
        report = []

        for u in users_with_savings:
            l_trans = Transaction.objects.filter(user=u, transaction_type='LOAN_SAVING', is_verified=True).order_by('effective_date')
            if not l_trans.exists(): continue
            
            first_date = l_trans.first().effective_date
            days_passed = (today - first_date).days
            days_remaining = max(0, 90 - days_passed)
            
            # --- جراحی ۱: محاسبه مجموع برداشت‌های وام ---
            w_trans = Transaction.objects.filter(user=u, transaction_type='W_SAVING', is_verified=True)
            total_withdrawals = w_trans.aggregate(Sum('amount'))['amount__sum'] or 0
            
            # کسر برداشت‌ها از اصل موجودی وام
            total_saving = (l_trans.aggregate(Sum('amount'))['amount__sum'] or 0) - total_withdrawals
            
            # --- جراحی ۲: محاسبه دقیق امتیاز کل وام با کسر امتیاز برداشت‌ها ---
            loan_saving_points = 0
            for t in l_trans:
                d_passed = (today - t.effective_date).days
                if d_passed > 0:
                    loan_saving_points += int((t.amount / 1000000) * 7000 * d_passed)
            
            for w in w_trans:
                d_passed = (today - w.effective_date).days
                if d_passed > 0:
                    loan_saving_points -= int((w.amount / 1000000) * 7000 * d_passed)
                    
            loan_saving_points = max(0, loan_saving_points)
            
            # ۲. امتیاز حاصل از صدقات
            donation_total = Transaction.objects.filter(user=u, transaction_type='SADAQAH', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            donation_points = int(donation_total * 0.20)
            
            # ۳. امتیاز حاصل از معرفی اعضا
            active_referrals_count = Transaction.objects.filter(
                user__referral_code=u.membership_code,
                transaction_type=Transaction.Types.MEMBERSHIP_FEE,
                is_verified=True
            ).values('user').distinct().count()
            referral_points = (active_referrals_count // 5) * 1000000
            
            # ۴. امتیازهای ثبت شده دستی (انتقالی یا اهدایی)
            manual_points = PointLog.objects.filter(user=u).aggregate(Sum('points'))['points__sum'] or 0
            
            # جمع کل امتیازاتی که کاربر در پنل خود می‌بیند
            total_current_points = loan_saving_points + donation_points + referral_points + manual_points

            report.append({
                "id": u.id,
                "full_name": u.full_name,
                "membership_code": u.membership_code,
                "first_deposit_date": first_date,
                "days_passed": days_passed,
                "days_remaining": days_remaining,
                "total_saving": total_saving,
                "current_points": total_current_points
            })
        
        return Response(report)
# =========================================================
# --- فاز ۵: ویوها و APIهای سرمایه‌گذاری خارج از صندوق ---
# =========================================================
from .models import ExternalInvestment, InvestmentTransaction
from .serializers import ExternalInvestmentSerializer, InvestmentTransactionSerializer

class InvestmentDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_investments', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)

        # ۱. محاسبه کل منابع مالی صندوق (سینک شده ۱۰۰٪ با پنل گزارشات هیئت مدیره)
        valid_deposit_types = [
            Transaction.Types.MONTHLY_DEPOSIT, 
            Transaction.Types.PROFIT_SAVING,
            'SHORT_TERM', 
            'LONG_TERM', 
            'MANUAL_PROFIT',
            Transaction.Types.LOAN_SAVING, 
            Transaction.Types.QARD_HASAN,
            Transaction.Types.MEMBERSHIP_FEE, 
            'SADAQAH', 'SACRIFICE', 'BOOK', 
            'KHOMS_IMAM', 'KHOMS_SADAT', 'WAQF',
            'WAQF_GEN', 'WAQF_BOOK', 'WAQF_MEDIA', 'WAQF_INFRA'
        ]
        
        deposits = Transaction.objects.filter(
            transaction_type__in=valid_deposit_types, 
            is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        withdrawals = Transaction.objects.filter(
            transaction_type__in=ALL_WITHDRAWAL_TYPES, 
            is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_fund_capital = deposits - withdrawals

        # ۲. محاسبه سرمایه درگیر در وام (بر اساس فرمول دقیق ۳۰ روزه که قبلاً نوشتیم)
        today = date.today()
        approved_loans = LoanRequest.objects.filter(status='APPROVED', granted_date__isnull=False)
        total_paid_loans = 0
        total_virtual_returned = 0

        for loan in approved_loans:
            total_paid_loans += loan.amount
            days_passed = (today - loan.granted_date).days
            months_passed = 0 if days_passed < 0 else days_passed // 30
            
            if loan.duration_months and loan.duration_months > 0:
                if months_passed > loan.duration_months:
                    months_passed = loan.duration_months
                monthly_installment = loan.amount / loan.duration_months
                total_virtual_returned += (monthly_installment * months_passed)

        active_loans_debt = total_paid_loans - int(total_virtual_returned)

        # ۳. محاسبه سرمایه درگیر در پروژه‌های سرمایه‌گذاری
        inv_deposits = InvestmentTransaction.objects.filter(transaction_type='DEPOSIT').aggregate(Sum('amount'))['amount__sum'] or 0
        inv_withdrawals = InvestmentTransaction.objects.filter(transaction_type='WITHDRAWAL').aggregate(Sum('amount'))['amount__sum'] or 0
        active_investments_debt = inv_deposits - inv_withdrawals

        # ۴. نقدینگی کاملاً آزاد سرمایه (پولی که در حساب بانک خوابیده و آماده تخصیص است)
        free_main_capital = total_fund_capital - active_loans_debt - active_investments_debt

        # ۵. کل سود محقق شده (جیب دوم - پول‌های تولید شده که هنوز تقسیم نشده‌اند)
        total_realized_profit = InvestmentTransaction.objects.filter(transaction_type='PROFIT', 
            is_settled=False).aggregate(Sum('amount'))['amount__sum'] or 0

        return Response({
            "total_fund_capital": total_fund_capital,
            "active_loans_debt": active_loans_debt,
            "active_investments_debt": active_investments_debt,
            "free_main_capital": free_main_capital,
            "total_realized_profit": total_realized_profit
        })

class ExternalInvestmentListCreateView(generics.ListCreateAPIView):
    serializer_class = ExternalInvestmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ExternalInvestment.objects.all().order_by('-start_date')

    def list(self, request, *args, **kwargs):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_investments', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)
        return super().list(request, *args, **kwargs)


class ExternalInvestmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExternalInvestmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ExternalInvestment.objects.all()


class InvestmentTransactionCreateView(generics.CreateAPIView):
    serializer_class = InvestmentTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_investments', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)
        
        # اعتبارسنجی: جلوگیری از برداشت بیشتر از سرمایه درگیر در یک پروژه
        inv_id = request.data.get('investment')
        t_type = request.data.get('transaction_type')
        amount = int(str(request.data.get('amount', '0')).replace(',', '')) # حذف کاما در صورت وجود

        if t_type == 'WITHDRAWAL':
            deposited = InvestmentTransaction.objects.filter(investment_id=inv_id, transaction_type='DEPOSIT').aggregate(Sum('amount'))['amount__sum'] or 0
            withdrawn = InvestmentTransaction.objects.filter(investment_id=inv_id, transaction_type='WITHDRAWAL').aggregate(Sum('amount'))['amount__sum'] or 0
            active_balance = deposited - withdrawn
            
            if amount > active_balance:
                return Response({"error": f"خطا: مبلغ آزادسازی ({amount:,} تومان) نمی‌تواند از سرمایه درگیرِ فعلی این پروژه ({active_balance:,} تومان) بیشتر باشد!"}, status=400)

        # اگر نوع تراکنش تزریق یا سود باشد، یا برداشت مجاز باشد، تراکنش ثبت می‌شود
        request.data['amount'] = amount
        return super().create(request, *args, **kwargs)
    

class SettleInvestmentProfitsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_investments', False):
            return Response({"error": "شما دسترسی ندارید."}, status=403)
        
        updated_count = InvestmentTransaction.objects.filter(
            transaction_type='PROFIT', 
            is_settled=False
        ).update(is_settled=True)
        
        return Response({"message": f"تعداد {updated_count} تراکنش سود با موفقیت صفر/تسویه شد."})

from .models import LoanInstallment, LoanRequest

class AdminLoanInstallmentsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, loan_id):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_loans', False):
            return Response({"error": "عدم دسترسی"}, status=403)
        
        import datetime
        
        try:
            loan = LoanRequest.objects.get(id=loan_id)
        except LoanRequest.DoesNotExist:
            return Response({"error": "وام یافت نشد"}, status=404)

        # --- جراحی هوشمند: تولید خودکار اقساط برای وام‌های قدیمی که قسط ندارند ---
        if loan.status == 'APPROVED' and loan.granted_date and loan.duration_months > 0:
            if not LoanInstallment.objects.filter(loan=loan).exists():
                installment_amount = loan.amount // loan.duration_months
                installments_to_create = []
                for i in range(1, loan.duration_months + 1):
                    due = add_jalali_months(loan.granted_date, i)
                    installments_to_create.append(
                        LoanInstallment(loan=loan, installment_number=i, due_date=due, amount=installment_amount)
                    )
                LoanInstallment.objects.bulk_create(installments_to_create)

        installments = LoanInstallment.objects.filter(loan=loan).order_by('installment_number')
        data = [{
            "id": i.id, "number": i.installment_number, 
            "due_date": i.due_date, "amount": i.amount, 
            "is_paid": i.is_paid, "paid_date": i.paid_date
        } for i in installments]
        return Response(data)

    def patch(self, request, loan_id):
        if request.user.role not in ['ADMIN', 'OBSERVER'] and not getattr(request.user, 'can_manage_loans', False):
            return Response({"error": "عدم دسترسی"}, status=403)
        
        import datetime
        inst_id = request.data.get('id')
        
        try:
            inst = LoanInstallment.objects.get(id=inst_id, loan_id=loan_id)
            
            # ۱. مدیریت وضعیت پرداخت
            if 'is_paid' in request.data:
                inst.is_paid = request.data['is_paid']
                if inst.is_paid and not inst.paid_date:
                    inst.paid_date = datetime.date.today()
                elif not inst.is_paid:
                    inst.paid_date = None
                    
            # ۲. جراحی هوشمند: مدیریت مبلغ مازاد و توازن اقساط آتی
            if 'amount' in request.data:
                # تبدیل مبلغ ورودی به عدد (حذف کاما)
                new_amount = int(str(request.data['amount']).replace(',', ''))
                old_amount = inst.amount
                difference = new_amount - old_amount
                
                # بروزرسانی مبلغ قسط فعلی
                inst.amount = new_amount
                
                # اگر مبلغ را زیاد کرده باشیم، باید از اقساط آخر کم کنیم
                if difference > 0:
                    # پیدا کردن تمام اقساط پرداخت نشده (بجز قسط فعلی) به ترتیب از آخر به اول
                    remaining_insts = LoanInstallment.objects.filter(
                        loan_id=loan_id, 
                        is_paid=False
                    ).exclude(id=inst_id).order_by('-installment_number')
                    
                    for other in remaining_insts:
                        if difference <= 0:
                            break
                        
                        if other.amount >= difference:
                            other.amount -= difference
                            difference = 0
                        else:
                            difference -= other.amount
                            other.amount = 0
                        other.save()
            
            inst.save()
            return Response({"message": "تغییرات اعمال و توازن اقساط با موفقیت انجام شد."})
        except LoanInstallment.DoesNotExist:
            return Response({"error": "قسط یافت نشد"}, status=404)