from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import *
from .models import User
from .utils import send_pattern_sms
import random
import string

# 1. ثبت‌نام
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            send_pattern_sms(user.phone_number, 'welcome', {
                'token1': user.full_name,
                'token2': user.membership_code
            })
            return Response({
                "message": "ثبت‌نام با موفقیت انجام شد.",
                "user_id": user.id,
                "phone": user.phone_number,
                "code": user.membership_code
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 2. ورود (حیاتی‌ترین بخش)
class LoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            password = serializer.validated_data['password']
            
            # احراز هویت (موبایل به عنوان نام کاربری)
            user = authenticate(username=phone, password=password)
            
            if user:
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    "message": "ورود موفقیت‌آمیز بود.",
                    "token": token.key,
                    "user_id": user.id,
                    "full_name": user.full_name,
                    "role": user.role
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "شماره موبایل یا رمز عبور اشتباه است."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 3. مدیریت خانواده (افزودن و لیست)
class FamilyMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        members = request.user.family_members.all()
        data = []
        for m in members:
            from accounting.models import Transaction
            has_paid = Transaction.objects.filter(user=m, transaction_type='FEE', is_verified=True).exists()
            data.append({
                'id': m.id,
                'full_name': m.full_name,
                'national_code': m.national_code,
                'membership_code': m.membership_code,
                'status': "فعال" if has_paid else "غیرفعال"
            })
        return Response(data)

    def post(self, request):
        serializer = AddFamilyMemberSerializer(data=request.data)
        if serializer.is_valid():
            import random, string
            
            # --- اصلاح شد: ساخت شماره مجازی ۱۱ رقمی ---
            # فرمت: 010 + 8 رقم تصادفی (مثلا: 01012345678)
            # این فرمت همیشه ۱۱ رقم است و در دیتابیس جا می‌شود.
            while True:
                random_part = ''.join(random.choices(string.digits, k=8))
                fake_phone = f"010{random_part}"
                # چک کنیم که شانسی تکراری نباشد
                if not User.objects.filter(phone_number=fake_phone).exists():
                    break
            # ------------------------------------------

            # ساخت کاربر جدید
            new_user = User.objects.create_user(
                national_code=serializer.validated_data.get('national_code'),
                phone_number=fake_phone, # شماره ۱۱ رقمی استاندارد
                password=''.join(random.choices(string.digits, k=8)),
                full_name=serializer.validated_data['full_name'],
                parent=request.user, 
                referral_code=request.user.membership_code, 
                gender=serializer.validated_data.get('gender'),
                birth_date=serializer.validated_data.get('birth_date')
            )

            # ارسال پیامک خوش‌آمد (به شماره پدر)
            send_pattern_sms(request.user.phone_number, 'welcome', {
                'token1': new_user.full_name,
                'token2': new_user.membership_code
            })

            return Response({"message": "عضو جدید با موفقیت اضافه شد.", "code": new_user.membership_code}, status=200)
        return Response(serializer.errors, status=400)
    
# بقیه ویوها (ProfileUpdate, ForgotPassword, ChangePassword)
class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
    def get_object(self): return self.request.user

class ForgotPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgotPasswordRequestSerializer
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            user = User.objects.filter(phone_number=phone).first()
            
            # جستجوی هوشمند (با صفر و بی صفر)
            if not user:
                if phone.startswith('0'): user = User.objects.filter(phone_number=phone[1:]).first()
                else: user = User.objects.filter(phone_number='0' + phone).first()

            if not user: return Response({"error": "کاربری یافت نشد."}, status=400)

            new_pass = ''.join(random.choices(string.digits, k=5))
            user.set_password(new_pass)
            user.save()
            send_pattern_sms(user.phone_number, 'otp', {'token1': new_pass})
            return Response({"message": "رمز جدید پیامک شد."}, status=200)
        return Response(serializer.errors, status=400)

class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({"error": "رمز اشتباه است."}, status=400)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "تغییر کرد."}, status=200)
        return Response(serializer.errors, status=400)