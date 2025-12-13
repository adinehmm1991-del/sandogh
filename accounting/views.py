from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from .models import Transaction, ProfitPeriod, ProfitDistribution, WithdrawalRequest
from .serializers import TransactionSerializer, WithdrawalRequestSerializer
from users.models import User
import datetime
from decimal import Decimal

# --- بخش اول: ثبت و نمایش تراکنش‌ها ---
# --- بخش اول: ثبت و نمایش تراکنش‌ها ---
# --- بخش اول: ثبت و نمایش تراکنش‌ها ---
class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 1. لیست تمام اعضای خانواده (خودش + فرزندان)
        family_ids = self.request.user.family_members.values_list('id', flat=True)
        all_ids = [self.request.user.id, *family_ids]
        
        # 2. اگر در آدرس، user_id خاصی خواسته شده (فیلتر کردن برای نمایش)
        target_id = self.request.query_params.get('user_id')
        if target_id:
             try: 
                 target = User.objects.get(id=target_id)
                 if target.id in all_ids:
                     return Transaction.objects.filter(user=target).order_by('-date')
             except: pass
        
        # پیش‌فرض: نمایش همه تراکنش‌های خانوادگی
        return Transaction.objects.filter(user__in=all_ids).order_by('-date')

    def perform_create(self, serializer):
        # تغییر مهم: ما user را اینجا ست نمی‌کنیم!
        # خود سریالایزر (TransactionSerializer) مسئول پیدا کردن کاربر از روی target_user_id است.
        serializer.save()

# --- بخش دوم: محاسبه سود (اصلاح شده با شرط حق عضویت) ---
class CalculateProfitView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, period_id):
        try:
            period = ProfitPeriod.objects.get(id=period_id)
        except ProfitPeriod.DoesNotExist:
            return Response({"error": "دوره مورد نظر یافت نشد."}, status=404)

        # 1. پاکسازی هوشمند
        Transaction.objects.filter(profit_period=period).delete()
        ProfitDistribution.objects.filter(period=period).delete()

        # 2. محاسبه بازه های زمانی
        total_days = (period.end_date - period.start_date).days
        number_of_steps = max(1, int(total_days / 30))
        step_duration = total_days / number_of_steps
        
        checkpoints = []
        for i in range(number_of_steps):
            cp_date = period.start_date + datetime.timedelta(days=(i + 1) * step_duration)
            checkpoints.append(cp_date)

        PROFITABLE_TYPES = [Transaction.Types.MONTHLY_DEPOSIT, Transaction.Types.PROFIT_SAVING]
        
        NON_PROFITABLE_TYPES = [
            Transaction.Types.LOAN_SAVING, 
            Transaction.Types.QARD_HASAN,
            Transaction.Types.MEMBERSHIP_FEE,
            Transaction.Types.DONATION
        ]

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
                transaction_type__in=[Transaction.Types.WITHDRAWAL],
                is_verified=True
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            return max(0, deposit - withdrawal)

        # 3. محاسبه امتیاز اعضا
        for member in members:
            # --- شرط جدید: آیا حق عضویت پرداخت کرده؟ ---
            has_paid_fee = Transaction.objects.filter(
                user=member, 
                transaction_type=Transaction.Types.MEMBERSHIP_FEE, 
                is_verified=True
            ).exists()

            # اگر حق عضویت نداده، کلاً از محاسبه سود حذف می‌شود
            if not has_paid_fee:
                continue 
            # --------------------------------------------

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

        # 4. محاسبه امتیاز صندوق
        other_capitals = Transaction.objects.filter(
            effective_date__lte=period.end_date,
            transaction_type__in=NON_PROFITABLE_TYPES,
            is_verified=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        other_scores = Decimal(int(other_capitals / 1000000))
        final_denominator = total_system_score + other_scores

        # 5. محاسبه نرخ سود
        distributable_profit = period.total_profit_amount * 0.5
        
        if final_denominator > 0:
            rate = distributable_profit / float(final_denominator)
        else:
            rate = 0

        # 6. واریز سود اعضا
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

        # 7. واریز سهم صندوق
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
            
        period.is_calculated = True
        period.save()

        return Response({
            "status": "موفق",
            "message": f"محاسبه سود انجام شد (اعضای غیرفعال حذف شدند).",
            "total_profit": period.total_profit_amount,
            "rate_per_score": rate,
            "distributed_to_members": distributed_profit,
            "fund_share_total": fund_share,
            "final_denominator": final_denominator
        })


# --- بخش سوم: داشبورد کاربر (اصلاح شمارش معرف) ---
class UserDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        target_id = request.query_params.get('user_id')
        user = request.user
        
        if target_id:
            try:
                # چک میکنیم آیا این آیدی، فرزندِ این کاربر است؟
                user = User.objects.get(id=target_id, parent=request.user)
            except User.DoesNotExist:
                pass # اگر نبود، همان کاربر اصلی میماند
        today = datetime.date.today()
        six_months_ago = today - datetime.timedelta(days=30 * 6)

        def get_sum(queryset):
            return queryset.aggregate(Sum('amount'))['amount__sum'] or 0

        # امتیاز وام (روزشمار)
        loan_transactions = Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.LOAN_SAVING, is_verified=True
        ).order_by('date')
        loan_saving_points = 0
        first_deposit_date = None
        days_passed_since_start = 0
        days_remaining_to_unlock = 0
        is_eligible_for_loan = False

        if loan_transactions.exists():
            first_deposit_date = loan_transactions.first().effective_date
            days_passed_since_start = (today - first_deposit_date).days
            if days_passed_since_start >= 90:
                is_eligible_for_loan = True; days_remaining_to_unlock = 0
            else:
                is_eligible_for_loan = False; days_remaining_to_unlock = 90 - days_passed_since_start

            for trans in loan_transactions:
                days_active = (today - trans.effective_date).days
                if days_active > 0:
                    daily_score = (trans.amount / 1000000) * 6000
                    loan_saving_points += int(daily_score * days_active)

        # امتیاز بلاعوض
        donation_total = get_sum(Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.DONATION, is_verified=True
        ))
        donation_points = int(donation_total * 0.20)
        
        # امتیاز معرف (و تعداد نفرات)
        # 1. فقط کسانی که حق عضویت داده‌اند شمرده می‌شوند
        active_referrals_count = Transaction.objects.filter(
            user__referral_code=user.membership_code,
            transaction_type=Transaction.Types.MEMBERSHIP_FEE,
            is_verified=True
        ).values('user').distinct().count()

        referral_loan_points = (active_referrals_count // 5) * 1000000

        # موجودی کل
        user_deposit_types = [
            Transaction.Types.MONTHLY_DEPOSIT, Transaction.Types.PROFIT_SAVING,
            Transaction.Types.LOAN_SAVING, Transaction.Types.QARD_HASAN,
            Transaction.Types.MEMBERSHIP_FEE 
        ]
        user_deposits = get_sum(Transaction.objects.filter(
            user=user, transaction_type__in=user_deposit_types, is_verified=True
        ))
        user_withdrawals = get_sum(Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.WITHDRAWAL, is_verified=True
        ))
        current_balance = user_deposits - user_withdrawals

        if user.role == User.Roles.FUND_ACCOUNT:
            all_donations = get_sum(Transaction.objects.filter(
                transaction_type=Transaction.Types.DONATION, is_verified=True
            ))
            current_balance += all_donations

        total_profit_received = ProfitDistribution.objects.filter(user=user).aggregate(Sum('profit_amount'))['profit_amount__sum'] or 0
        has_paid_fee = Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.MEMBERSHIP_FEE, is_verified=True
        ).exists()

        return Response({
            "full_name": user.full_name if user.full_name else user.phone_number,
            "membership_code": user.membership_code,
            "role": user.role,
            "national_code": user.national_code,
            "card_number": user.card_number,
            "shaba_number": user.shaba_number,
            "monthly_commitment": user.monthly_commitment,
            "current_balance": current_balance,
            "total_profit_received": total_profit_received,
            "status": "فعال" if has_paid_fee else "غیرفعال (منتظر پرداخت حق عضویت)",
            "is_active": has_paid_fee,
            
            # این عدد در داشبورد نمایش داده می‌شود (فقط فعال‌ها)
            "referrals_count": active_referrals_count,

            "loan_points_details": {
                "from_donations": donation_points,
                "from_savings": loan_saving_points,
                "from_referrals": referral_loan_points,
                "active_referrals": active_referrals_count,
                "loan_amount_limit": (donation_points + loan_saving_points + referral_loan_points),
                "has_loan_deposit": first_deposit_date is not None,
                "is_eligible": is_eligible_for_loan,
                "days_passed": days_passed_since_start,
                "days_remaining": days_remaining_to_unlock,
            }
        })


# --- بخش چهارم: گزارش مدیریتی ---
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
            has_paid_fee = Transaction.objects.filter(
                user=member, transaction_type=Transaction.Types.MEMBERSHIP_FEE, is_verified=True
            ).exists()
            if member.is_active and has_paid_fee: active_members_count += 1
            else: inactive_members_count += 1
        
        def get_total(t_type):
            return Transaction.objects.filter(transaction_type=t_type, is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0

        total_monthly_deposit = get_total(Transaction.Types.MONTHLY_DEPOSIT)
        total_profit_saving = get_total(Transaction.Types.PROFIT_SAVING)
        total_loan_saving = get_total(Transaction.Types.LOAN_SAVING)
        total_qard = get_total(Transaction.Types.QARD_HASAN)
        total_donation = get_total(Transaction.Types.DONATION)
        total_fee = get_total(Transaction.Types.MEMBERSHIP_FEE)
        total_withdrawal = get_total(Transaction.Types.WITHDRAWAL)

        total_capital = (total_monthly_deposit + total_profit_saving + 
                         total_loan_saving + total_qard + total_donation + total_fee) - total_withdrawal

        total_commitments = User.objects.aggregate(Sum('monthly_commitment'))['monthly_commitment__sum'] or 0

        return Response({
            "total_members": total_members_count,
            "active_members": active_members_count,
            "inactive_members": inactive_members_count,
            "total_capital": total_capital,
            "total_qard": total_qard,
            "total_profit_saving": total_profit_saving,
            "total_loan_saving": total_loan_saving,
            "total_donation": total_donation,
            "total_commitments": total_commitments,
            "total_withdrawal": total_withdrawal
        })

# --- بخش پنجم: درخواست برداشت ---
class WithdrawalRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WithdrawalRequest.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)