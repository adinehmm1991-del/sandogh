// تابع تبدیل ارقام فارسی و عربی به انگلیسی (روش اصلاح شده)
export const toEnglishDigits = (str) => {
    if (!str) return '';
    
    // تبدیل به رشته
    str = str.toString();

    // لیست اعداد فارسی و عربی
    const persianNumbers = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    const arabicNumbers  = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];

    // حلقه برای جایگزینی تک‌تک اعداد
    for (let i = 0; i < 10; i++) {
        // جایگزینی فارسی با انگلیسی
        str = str.replaceAll(persianNumbers[i], i);
        // جایگزینی عربی با انگلیسی
        str = str.replaceAll(arabicNumbers[i], i);
    }

    return str;
};