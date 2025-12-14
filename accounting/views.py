from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
import datetime
from decimal import Decimal

# --- بخش ایمپورت مدل‌ها (تمیز و مرتب) ---
from .models import (
    Transaction, 
    ProfitPeriod, 
    ProfitDistribution, 
    WithdrawalRequest, 
    LoanRequest, 
    PointLog, 
    PointTransferRequest
)

# --- بخش ایمپورت سریالایزرها ---
from .serializers import (
    TransactionSerializer, 
    WithdrawalRequestSerializer, 
    LoanRequestSerializer, 
    PointTransferSerializer, 
    PointLogSerializer
)

from users.models import User

# ... ادامه کدهای کلاس‌ها از اینجا به بعد ...

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
        
        return Transaction.objects.filter(user__in=all_ids).order_by('-date')

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
                transaction_type__in=[Transaction.Types.WITHDRAWAL_SAVING, Transaction.Types.WITHDRAWAL_PROFIT, Transaction.Types.WITHDRAWAL_MONTHLY, Transaction.Types.WITHDRAWAL_QARD, Transaction.Types.WITHDRAWAL_OTHER],
                is_verified=True
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            return max(0, deposit - withdrawal)

        for member in members:
            has_paid_fee = Transaction.objects.filter(
                user=member, 
                transaction_type=Transaction.Types.MEMBERSHIP_FEE, 
                is_verified=True
            ).exists()

            if not has_paid_fee:
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
            
        period.is_calculated = True
        period.save()

        return Response({"status": "OK"})


# --- بخش سوم: داشبورد کاربر (به‌روزرسانی با PointLog) ---
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

        # 1. محاسبه امتیاز سیستمی (زمانی)
        loan_transactions = Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.LOAN_SAVING, is_verified=True
        ).order_by('date')
        
        loan_saving_points = 0
        first_deposit_date = None
        days_passed_since_start = 0
        
        if loan_transactions.exists():
            first_deposit_date = loan_transactions.first().effective_date
            days_passed_since_start = (today - first_deposit_date).days
            
            for trans in loan_transactions:
                days_active = (today - trans.effective_date).days
                if days_active > 0:
                    daily_score = (trans.amount / 1000000) * 6000
                    loan_saving_points += int(daily_score * days_active)

        # 2. امتیاز بلاعوض
        donation_total = get_sum(Transaction.objects.filter(
            user=user, transaction_type=Transaction.Types.DONATION, is_verified=True
        ))
        donation_points = int(donation_total * 0.20)
        
        # 3. امتیاز معرف
        active_referrals_count = Transaction.objects.filter(
            user__referral_code=user.membership_code,
            transaction_type=Transaction.Types.MEMBERSHIP_FEE,
            is_verified=True
        ).values('user').distinct().count()

        referral_loan_points = (active_referrals_count // 5) * 1000000

        # 4. امتیازات دستی (جدید: شامل انتقال‌ها و وام‌های گرفته شده)
        # اگر کاربر امتیاز گرفته باشد (مثبت) یا داده باشد/وام گرفته باشد (منفی)
        manual_points = PointLog.objects.filter(user=user).aggregate(Sum('points'))['points__sum'] or 0

        # --- محاسبه نهایی امتیاز قابل استفاده ---
        total_loan_limit = (donation_points + loan_saving_points + referral_loan_points) + manual_points
        
        # شرط 90 روز
        is_eligible_for_loan = False
        days_remaining_to_unlock = 0
        if days_passed_since_start >= 90:
             is_eligible_for_loan = True
        else:
             days_remaining_to_unlock = 90 - days_passed_since_start


        # موجودی کل (آپدیت شده با انواع برداشت)
        user_deposit_types = [
            Transaction.Types.MONTHLY_DEPOSIT, Transaction.Types.PROFIT_SAVING,
            Transaction.Types.LOAN_SAVING, Transaction.Types.QARD_HASAN,
            Transaction.Types.MEMBERSHIP_FEE 
        ]
        user_deposits = get_sum(Transaction.objects.filter(
            user=user, transaction_type__in=user_deposit_types, is_verified=True
        ))
        
        # جمع تمام انواع برداشت‌ها
        user_withdrawals = get_sum(Transaction.objects.filter(
            user=user, transaction_type__startswith='W_', is_verified=True
        ))
        # بعلاوه برداشت های قدیمی اگر تایپشان WITHDRAWAL بوده
        user_withdrawals += get_sum(Transaction.objects.filter(
            user=user, transaction_type='WITHDRAWAL', is_verified=True
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
            "current_balance": current_balance,
            "total_profit_received": total_profit_received,
            "status": "فعال" if has_paid_fee else "غیرفعال",
            "is_active": has_paid_fee,
            "referrals_count": active_referrals_count,
            "loan_points_details": {
                "total_limit": total_loan_limit, # امتیاز نهایی برای نمایش
                "from_donations": donation_points,
                "from_savings": loan_saving_points,
                "from_referrals": referral_loan_points,
                "from_transfers": manual_points, # نمایش امتیاز دستی/انتقالی
                
                "loan_amount_limit": total_loan_limit,
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
        
        # جمع تمام برداشت‌ها
        w1 = get_total(Transaction.Types.WITHDRAWAL_SAVING)
        w2 = get_total(Transaction.Types.WITHDRAWAL_PROFIT)
        w3 = get_total(Transaction.Types.WITHDRAWAL_MONTHLY)
        w4 = get_total(Transaction.Types.WITHDRAWAL_QARD)
        w5 = get_total(Transaction.Types.WITHDRAWAL_OTHER)
        w_old = get_total('WITHDRAWAL')
        total_withdrawal = w1 + w2 + w3 + w4 + w5 + w_old

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


# --- بخش ششم: درخواست وام (جدید) ---
class LoanRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LoanRequest.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# --- بخش هفتم: لیست سوابق امتیاز (جدید) ---
class PointLogListView(generics.ListAPIView):
    serializer_class = PointLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PointLog.objects.filter(user=self.request.user).order_by('-created_at')


# --- بخش هشتم: انتقال امتیاز (جدید - منطق اصلی) ---
# یادتان باشد در بالای فایل models را کامل ایمپورت کنید:
# from .models import Transaction, ..., PointTransferRequest

# --- بخش هشتم: درخواست انتقال امتیاز (اصلاح شده با تایید مدیر) ---
class PointTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PointTransferSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            target_code = serializer.validated_data['target_membership_code']
            points = serializer.validated_data['points']

            if points <= 0:
                return Response({"error": "امتیاز باید بیشتر از صفر باشد."}, status=400)

            # 1. پیدا کردن گیرنده
            try:
                target_user = User.objects.get(membership_code=target_code)
            except User.DoesNotExist:
                return Response({"error": "کد عضویت مقصد یافت نشد."}, status=400)
            
            if target_user.id == user.id:
                return Response({"error": "نمی‌توانید به خودتان انتقال دهید."}, status=400)

            # 2. محاسبه امتیاز فعلی کاربر (آیا امتیاز کافی دارد؟)
            # (کد محاسبات شما دقیقاً حفظ شده است)
            
            # الف) زمانی
            today = datetime.date.today()
            l_trans = Transaction.objects.filter(user=user, transaction_type='LOAN_SAVING', is_verified=True)
            sys_points = 0
            if l_trans.exists():
                for t in l_trans:
                    d = (today - t.effective_date).days
                    if d > 0: sys_points += int((t.amount / 1000000) * 6000 * d)
            
            # ب) بلاعوض
            don = Transaction.objects.filter(user=user, transaction_type='DONATION', is_verified=True).aggregate(Sum('amount'))['amount__sum'] or 0
            don_points = int(don * 0.20)
            
            # ج) معرف
            refs = Transaction.objects.filter(user__referral_code=user.membership_code, transaction_type='FEE', is_verified=True).values('user').distinct().count()
            ref_points = (refs // 5) * 1000000
            
            # د) دستی
            man_points = PointLog.objects.filter(user=user).aggregate(Sum('points'))['points__sum'] or 0
            
            current_total_points = sys_points + don_points + ref_points + man_points

            # بررسی موجودی
            if current_total_points < points:
                return Response({"error": f"موجودی امتیاز کافی نیست. موجودی شما: {current_total_points:,}"}, status=400)

            # 3. ثبت درخواست (تغییر یافته: به جای انتقال مستقیم، درخواست ثبت می‌شود)
            PointTransferRequest.objects.create(
                sender=user,
                receiver=target_user,
                amount=points,
                status=PointTransferRequest.Status.PENDING, # وضعیت در انتظار
                description=f"درخواست انتقال امتیاز به {target_user.full_name} ({target_user.membership_code})"
            )

            # پیام موفقیت تغییر کرد
            return Response({"message": "✅ درخواست انتقال امتیاز ثبت شد و پس از تایید مدیر انجام می‌شود."})
        
        return Response(serializer.errors, status=400)