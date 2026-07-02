import { Checkbox, FormControlLabel, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions } from '@mui/material';
import React, { useState } from 'react';
import axios from 'axios';
import { Container, Paper, TextField, Button, Typography, Box, Alert, MenuItem } from '@mui/material';
import { useNavigate, Link } from 'react-router-dom';
import CurrencyInput from './CurrencyInput';
import { toEnglishDigits } from './utils'; // ایمپورت تابع تبدیل

function Register() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [openTerms, setOpenTerms] = useState(false); // برای باز کردن پنجره قوانین
  const [commitmentSelect, setCommitmentSelect] = useState(''); 

  const [formData, setFormData] = useState({
    phone_number: '',
    password: '',
    full_name: '',
    national_code: '',
    referral_code: '',
    monthly_commitment: '0',
  });

  const commitmentOptions = [
    { value: '0', label: 'قصد واریز ماهیانه ندارم' },
    { value: '100000', label: '۱۰۰,۰۰۰ تومان' },
    { value: '200000', label: '۲۰۰,۰۰۰ تومان' },
    { value: '300000', label: '۳۰۰,۰۰۰ تومان' },
    { value: '400000', label: '۴۰۰,۰۰۰ تومان' },
    { value: '500000', label: '۵۰۰,۰۰۰ تومان' },
    { value: '600000', label: '۶۰۰,۰۰۰ تومان' },
    { value: '700000', label: '۷۰۰,۰۰۰ تومان' },
    { value: '800000', label: '۸۰۰,۰۰۰ تومان' },
    { value: '900000', label: '۹۰۰,۰۰۰ تومان' },
    { value: '1000000', label: '۱,۰۰۰,۰۰۰ تومان' },
    { value: 'CUSTOM', label: 'بیش از ۱ میلیون تومان (وارد کردن دستی)' },
  ];

  const handleChange = (e) => {
    let { name, value } = e.target;
    
    // اگر فیلد عددی بود، تبدیل کن
    if (['phone_number', 'national_code', 'referral_code', 'password'].includes(name)) {
        value = toEnglishDigits(value);
    }

    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleCommitmentSelectChange = (e) => {
    const selected = e.target.value;
    setCommitmentSelect(selected);

    if (selected !== 'CUSTOM') {
        setFormData(prev => ({ ...prev, monthly_commitment: selected }));
    } else {
        setFormData(prev => ({ ...prev, monthly_commitment: '' }));
    }
  };

  const handleCustomAmountChange = (e) => {
      // CurrencyInput خودش تبدیل عدد را انجام می‌دهد، پس مستقیم ست می‌کنیم
      setFormData(prev => ({ ...prev, monthly_commitment: e.target.value }));
  };

  const handleRegister = async () => {
    setLoading(true);
    setMessage(null);

    if (!formData.phone_number || !formData.password || !formData.full_name) {
        setMessage({ type: 'error', text: 'لطفاً نام، موبایل و رمز عبور را وارد کنید.' });
        setLoading(false);
        return;
    }

    try {
      // تغییر مهم: آدرس لیارا حذف شد
      const response = await axios.post('/api/users/register/', formData);
      const newCode = response.data.code;
      setMessage({ type: 'success', text: `✅ ثبت‌نام موفقیت‌آمیز بود! کد عضویت شما: ${newCode}` });
      setTimeout(() => navigate('/'), 3000);
    } catch (error) {
      console.error(error);
      if (error.response && error.response.data) {
          let errorText = "";
          const data = error.response.data;
          if (typeof data === 'object') {
              for (const key in data) { errorText += `${data[key]} `; }
          } else { errorText = "خطا در ثبت اطلاعات."; }
          setMessage({ type: 'error', text: errorText });
      } else {
          setMessage({ type: 'error', text: 'خطا در ارتباط با سرور.' });
      }
    } finally {
        setLoading(false);
    }
  };

  return (
    <Container maxWidth="xs">
      <Paper elevation={3} style={{ padding: '30px', textAlign: 'center', marginTop: '50px' }}>
        <Typography variant="h5" component="h1" gutterBottom>عضویت در صندوق</Typography>
        <Typography variant="body2" color="textSecondary" style={{marginBottom: '20px'}}>
          مشخصات خود را وارد کنید
        </Typography>

        <Box component="form" noValidate autoComplete="off">
          <TextField label="نام و نام خانوادگی" name="full_name" fullWidth margin="dense" value={formData.full_name} onChange={handleChange} />
          
          <TextField label="شماره موبایل" name="phone_number" fullWidth margin="dense" dir="ltr" value={formData.phone_number} onChange={handleChange} inputProps={{ autoComplete: 'new-password' }} />

          <TextField label="کد ملی" name="national_code" fullWidth margin="dense" dir="ltr" value={formData.national_code} onChange={handleChange} />

          <TextField select label="تعهد واریز ماهیانه" value={commitmentSelect} onChange={handleCommitmentSelectChange} fullWidth margin="dense">
            {commitmentOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
            ))}
          </TextField>

          {commitmentSelect === 'CUSTOM' && (
             <Box mt={1} p={2} bgcolor="#e3f2fd" borderRadius={2}>
                <Typography variant="caption" color="primary">مبلغ دلخواه خود را وارد کنید:</Typography>
                <CurrencyInput 
                    label="مبلغ تعهد (تومان)" 
                    name="monthly_commitment" 
                    value={formData.monthly_commitment} 
                    onChange={handleCustomAmountChange} 
                    fullWidth margin="dense" 
                />
             </Box>
          )}

          <TextField label="کد معرف (اختیاری)" name="referral_code" fullWidth margin="dense" dir="ltr" value={formData.referral_code} onChange={handleChange} />

          <TextField label="رمز عبور" name="password" type="password" fullWidth margin="dense" dir="ltr" value={formData.password} onChange={handleChange} inputProps={{ autoComplete: 'new-password' }} />
          {/* چک‌باکس قوانین */}
          <div style={{display:'flex', alignItems:'center', marginTop:'10px'}}>
              <Checkbox 
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                color="primary"
              />
              <Typography variant="body2">
                  من <span 
                        style={{color:'#1976d2', cursor:'pointer', textDecoration:'underline'}}
                        onClick={() => setOpenTerms(true)}
                     >
                        شرایط و قوانین صندوق
                     </span> را مطالعه کرده و می‌پذیرم.
              </Typography>
          </div>

          <Button 
            variant="contained" color="success" fullWidth 
            style={{ marginTop: '10px', padding: '10px' }} 
            onClick={handleRegister}
            disabled={loading || !termsAccepted} // تا تیک نزند، دکمه خاموش است
          >
            {loading ? 'درحال ثبت...' : 'ثبت‌نام نهایی'}
          </Button>

          {/* پنجره نمایش قوانین (مودال) */}
          <Dialog open={openTerms} onClose={() => setOpenTerms(false)}>
            <DialogTitle>قوانین و مقررات صندوق ثنای حق</DialogTitle>
            <DialogContent>
              <DialogContentText style={{textAlign: 'justify'}}>
                این صندوق با هدف ترویج مباحث دینی و فرهنگی تاسیس شده است لذا تقاضا داریم با نیت خیر در این صندوق سرمایه گذاری کنید. 
                <br/>
                <br/>
                ۱. به تعهد واریز ماهیانه (درصورت انتخاب )پایبند هستم  .
                <br/>
                ۲. واریز سرمایه برای دریافت سود باید تا پنجم هر ماه انجام شود.
                <br/>
                 ۲. واریزی تا به یک میلیون نرسیده به آن سود تعلق نمی گیرد(سود به هر ۱ میلیون تومان تعلق می گیرد).
                <br/>
                ۳. پس انداز وام بعد از شش ماه سپرده گذاری واجد دریافت می شود.
                 <br/>
                 <br/>
                 <br/>


                تمام اصول و قواعد صندوق در کانال ایتا{' '}
                <a 
                    href="https://eitaa.com/S_thanayehaq" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: '#1976d2', textDecoration: 'none', fontWeight: 'bold' }}
                >
                    https://eitaa.com/S_sanayehaq
                </a>
                {' '}را مطالعه کردم و می پذیرم .
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenTerms(false)} color="primary">بستن</Button>
            </DialogActions>
          </Dialog>

            
         
        </Box>

        {message && <Alert severity={message.type} style={{ marginTop: '20px', textAlign: 'right' }}>{message.text}</Alert>}

        <div style={{ marginTop: '20px', fontSize: '14px' }}>
            قبلاً ثبت‌نام کرده‌اید؟ <Link to="/" style={{textDecoration: 'none', fontWeight: 'bold'}}>وارد شوید</Link>
        </div>
      </Paper>
    </Container>
  );
}

export default Register;