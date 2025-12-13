from django import forms
from .models import User

class UserCreationForm(forms.ModelForm):
    # تعریف فیلدهای رمز عبور که در دیتابیس نیستند اما در فرم لازم‌اند
    password = forms.CharField(label='رمز عبور', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='تکرار رمز عبور', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('phone_number', 'full_name')

    # بررسی اینکه دو رمز یکی باشند
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("رمزهای عبور مغایرت دارند.")
        return cleaned_data

    # ذخیره کاربر با رمز هش شده (امن)
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user