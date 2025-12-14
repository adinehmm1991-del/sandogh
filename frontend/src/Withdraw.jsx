import React, { useState } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, Box, Alert, MenuItem } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CurrencyInput from './CurrencyInput'; // فرض بر این است که این کامپوننت را دارید

function Withdraw() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  
  const [formData, setFormData] = useState({
    amount: '',
    source_type: 'LOAN', // پیش‌فرض
    description: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }

    try {
      // آدرس اصلاح شده و دقیق
      const url = 'https://sandogh-server.liara.run/api/accounting/withdrawals/';
      await axios.post(url, formData, {
        headers: { Authorization: `Token ${token}` }
      });
      
      setMessage({ type: 'success', text: '✅ درخواست برداشت با موفقیت ثبت شد.' });
      setTimeout(() => navigate('/dashboard'), 2000);
   } catch (error) {
      console.error(error);
      
      // --- شروع تغییر: دریافت متن خطای فارسی ---
      let errorText = 'خطا در ثبت درخواست.';
      if (error.response && error.response.data) {
          const data = error.response.data;
          // اگر خطا مربوط به مبلغ باشد (مثلا موجودی کافی نیست)
          if (data.amount) errorText = data.amount[0]; 
          // اگر خطای کلی باشد
          else if (data.error) errorText = data.error;
          // اگر خطای توضیحات باشد
          else if (data.detail) errorText = data.detail;
      }
      // --- پایان تغییر ---

      setMessage({ type: 'error', text: errorText });
    } finally {
        setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm" style={{ marginTop: '40px', marginBottom: '40px' }}>
      <Paper elevation={4} style={{ padding: '30px', borderRadius: '15px' }}>
        <Typography variant="h5" align="center" style={{ fontWeight: 'bold', color: '#d32f2f', marginBottom: '20px' }}>
           درخواست برداشت وجه
        </Typography>

        <Alert severity="info" style={{marginBottom:'20px', fontSize:'0.9rem'}}>
            توجه: مبلغ پس از تایید مدیر به شماره شبا ثبت شده در پروفایل واریز می‌شود.
        </Alert>

        <Box component="form">
          {/* انتخاب منبع برداشت */}
          <TextField
            select
            label="برداشت از کدام حساب؟"
            name="source_type"
            value={formData.source_type}
            onChange={handleChange}
            fullWidth
            margin="normal"
            variant="outlined"
          >
            <MenuItem value="LOAN">💰 پس‌انداز وام (عادی)</MenuItem>
            <MenuItem value="PROFIT">📈 پس‌انداز سود</MenuItem>
            <MenuItem value="MONTHLY">🗓 ماهیانه</MenuItem>
            <MenuItem value="QARD">🤝 قرض‌الحسنه</MenuItem>
          </TextField>

          <CurrencyInput label="مبلغ برداشت (تومان)" name="amount" value={formData.amount} onChange={handleChange} fullWidth margin="normal" />
          
          <TextField 
            label="توضیحات (اختیاری)" 
            name="description" 
            value={formData.description} 
            onChange={handleChange} 
            fullWidth margin="normal" 
            multiline rows={2} 
            placeholder="مثلاً: بابت قسط وام / نیاز فوری..."
          />

          <div style={{ display: 'flex', gap: '15px', marginTop:'30px' }}>
            <Button 
                variant="contained" 
                color="error" 
                fullWidth 
                size="large"
                onClick={handleSubmit} 
                disabled={loading}
                style={{ fontWeight: 'bold' }}
            >
                {loading ? 'درحال ثبت...' : 'ثبت نهایی'}
            </Button>
            <Button variant="outlined" color="inherit" fullWidth onClick={() => navigate('/dashboard')}>
                بازگشت
            </Button>
          </div>
        </Box>
        {message && <Alert severity={message.type} style={{ marginTop: '20px' }}>{message.text}</Alert>}
      </Paper>
    </Container>
  );
}

export default Withdraw;