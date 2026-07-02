import React from 'react';
import { TextField, InputAdornment } from '@mui/material';
import { toEnglishDigits } from './utils'; // وارد کردن تابع تبدیل

function CurrencyInput({ label, value, onChange, name, ...props }) {
  
  // تابع نمایش (سه رقم سه رقم)
  const formatNumber = (num) => {
    if (!num) return '';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  };

  // تابع تغییر مقدار
  const handleChange = (e) => {
    // 1. حذف کاماها
    let rawValue = e.target.value.replace(/,/g, '');
    
    // 2. تبدیل اعداد فارسی/عربی به انگلیسی (مهم)
    rawValue = toEnglishDigits(rawValue);

    // 3. چک کردن اینکه آیا نتیجه عدد است؟
    if (!isNaN(rawValue)) {
      // ساختن یک رویداد (Event) مصنوعی برای ارسال به فرم والد
      onChange({ target: { name: name, value: rawValue } });
    }
  };

  return (
    <TextField
      {...props}
      label={label}
      value={formatNumber(value)}
      onChange={handleChange}
      name={name}
      dir="ltr"
      InputProps={{
        // تغییر مهم: کلمه تومان به سمت چپ (Start) منتقل شد
        startAdornment: <InputAdornment position="start">تومان</InputAdornment>,
      }}
    />
  );
}

export default CurrencyInput;