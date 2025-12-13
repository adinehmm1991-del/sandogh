import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, MenuItem, Box, Alert } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DatePicker from "react-multi-date-picker";
import persian from "react-date-object/calendars/persian";
import persian_fa from "react-date-object/locales/persian_fa";
import CurrencyInput from './CurrencyInput';

function Deposit() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date());

  // لیست اعضای خانواده
  const [familyMembers, setFamilyMembers] = useState([]);
  
  const [formData, setFormData] = useState({
    amount: '',
    transaction_type: 'MONTHLY',
    description: '',
    receipt_image: null,
    target_user_id: '' // آی‌دی کسی که براش واریز میشه (خالی = خود کاربر)
  });

  const transactionTypes = [
    { value: 'MONTHLY', label: 'واریز ماهیانه' },
    { value: 'PROFIT_SAVING', label: 'پس‌انداز سود' },
    { value: 'LOAN_SAVING', label: 'پس‌انداز وام' },
    { value: 'QARD', label: 'قرض‌الحسنه' },
    { value: 'DONATION', label: 'کمک بلاعوض' },
    { value: 'FEE', label: 'حق عضویت' },
  ];

  // دریافت اطلاعات اولیه
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    // 1. دریافت لیست خانواده
    const fetchFamily = async () => {
        try {
            const res = await axios.get('https://sandogh-server.liara.run/api/users/family/', {
                headers: { Authorization: `Token ${token}` }
            });
            setFamilyMembers(res.data);
        } catch (e) { console.error(e); }
    };
    
    // 2. چک کردن پروفایل خود کاربر
    const checkProfile = async () => {
        try {
            const res = await axios.get('https://sandogh-server.liara.run/api/users/profile/', {
                headers: { Authorization: `Token ${token}` }
            });
            const data = res.data;
            if (!data.full_name || !data.national_code || !data.card_number) {
                alert("⛔ کاربر گرامی\nابتدا باید پروفایل خود را تکمیل کنید.");
                navigate('/profile');
            }
        } catch (e) { console.error(e); }
    };

    checkProfile();
    fetchFamily();
  }, [navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    let newData = { ...formData, [name]: value };

    // تنظیم خودکار مبلغ حق عضویت
    if (name === 'transaction_type') {
        if (value === 'FEE') {
            newData.amount = '1000000';
            newData.description = 'پرداخت حق عضویت ثابت';
        } else {
            newData.amount = '';
            newData.description = '';
        }
    }
    setFormData(newData);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData({ ...formData, receipt_image: file });
      setPreview(URL.createObjectURL(file));
    }
  };

  // --- تابع ارسال فرم (اصلاح شده) ---
  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);
    
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }

    // تنظیم تاریخ
    let finalDate = "";
    if (selectedDate) {
        if (selectedDate.toDate) finalDate = selectedDate.toDate().toISOString().split('T')[0];
        else finalDate = new Date().toISOString().split('T')[0];
    }

    // ساخت بسته اطلاعاتی
    const dataToSend = new FormData();
    dataToSend.append('amount', formData.amount);
    dataToSend.append('transaction_type', formData.transaction_type);
    dataToSend.append('date', finalDate);
    dataToSend.append('description', formData.description);

    // ارسال شناسه فرزند (اگر انتخاب شده باشد)
    if (formData.target_user_id) {
        dataToSend.append('target_user_id', formData.target_user_id);
    }

    if (formData.receipt_image) {
        dataToSend.append('receipt_image', formData.receipt_image);
    }

    try {
      await axios.post('https://sandogh-server.liara.run/api/accounting/transactions/', dataToSend, {
        headers: { 'Authorization': `Token ${token}` }
      });
      
      setMessage({ type: 'success', text: '✅ واریزی با موفقیت ثبت شد!' });
      
      // هدایت به داشبورد (با رفرش)
      setTimeout(() => navigate('/dashboard', { replace: true }), 2000);

    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.receipt_image ? "لطفا تصویر فیش را انتخاب کنید." : "خطا در ثبت اطلاعات.";
      setMessage({ type: 'error', text: errorMsg });
    } finally {
        setLoading(false);
    }
  };
  // --------------------------------

  return (
    <Container maxWidth="sm" style={{ marginTop: '50px', marginBottom: '50px' }}>
      <Paper elevation={3} style={{ padding: '30px' }}>
        <Typography variant="h5" gutterBottom>ثبت واریزی جدید</Typography>
        
        <Box component="form" noValidate autoComplete="off">
          
          {/* منوی انتخاب عضو خانواده */}
          <TextField
            select
            label="واریز برای:"
            name="target_user_id"
            value={formData.target_user_id}
            onChange={handleChange}
            fullWidth
            margin="normal"
            helperText="اگر برای عضو خانواده واریز می‌کنید، نام او را انتخاب کنید."
          >
            <MenuItem value=""><em>خودم (حساب اصلی)</em></MenuItem>
            {familyMembers.map((member) => (
              <MenuItem key={member.id} value={member.id}>
                {member.full_name} ({member.membership_code})
              </MenuItem>
            ))}
          </TextField>

          <TextField select label="نوع واریز" name="transaction_type" value={formData.transaction_type} onChange={handleChange} fullWidth margin="normal">
            {transactionTypes.map((option) => (
              <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
            ))}
          </TextField>

          <CurrencyInput 
            label="مبلغ (تومان)" 
            name="amount" 
            value={formData.amount} 
            onChange={handleChange} 
            fullWidth 
            margin="normal" 
            disabled={formData.transaction_type === 'FEE'}
          />

          <div style={{ marginTop: '16px', marginBottom: '8px' }}>
            <Typography variant="caption" color="textSecondary" style={{display: 'block', marginBottom: '5px'}}>تاریخ واریز (شمسی)</Typography>
            <DatePicker value={selectedDate} onChange={setSelectedDate} calendar={persian} locale={persian_fa} calendarPosition="bottom-right" style={{ width: "100%", height: "56px", borderRadius: "4px", border: "1px solid #c4c4c4", padding: "0 14px", fontFamily: "Tahoma" }} />
          </div>

          <TextField label="توضیحات (اختیاری)" name="description" value={formData.description} onChange={handleChange} fullWidth margin="normal" multiline rows={2} />

          <div style={{ margin: '20px 0', textAlign: 'center' }}>
            <input accept="image/*" style={{ display: 'none' }} id="raised-button-file" type="file" onChange={handleFileChange} />
            <label htmlFor="raised-button-file">
              <Button variant="outlined" component="span" startIcon={<CloudUploadIcon />}>انتخاب تصویر فیش</Button>
            </label>
            {preview && <div style={{ marginTop: '10px' }}><img src={preview} alt="fich" style={{ maxWidth: '100%', maxHeight: '200px', borderRadius: '8px' }} /></div>}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <Button variant="contained" color="primary" fullWidth onClick={handleSubmit} disabled={loading} style={{ padding: '10px' }}>
                {loading ? 'درحال ارسال...' : 'ثبت نهایی'}
            </Button>
            <Button variant="outlined" color="secondary" fullWidth onClick={() => navigate('/dashboard')}>انصراف</Button>
          </div>
        </Box>
        {message && <Alert severity={message.type} style={{ marginTop: '20px' }}>{message.text}</Alert>}
      </Paper>
    </Container>
  );
}

export default Deposit;