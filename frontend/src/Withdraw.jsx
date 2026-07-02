import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, Box, Alert, MenuItem } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CurrencyInput from './CurrencyInput'; 

function Withdraw() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  
  const [familyMembers, setFamilyMembers] = useState([]);
  const [userRole, setUserRole] = useState(null); // اضافه شدن متغیر نقش کاربر

  const [formData, setFormData] = useState({
    amount: '',
    source_type: 'SHORT_TERM',
    description: '',
    target_user_id: '' 
  });

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        // دریافت لیست خانواده
        const familyRes = await axios.get('/api/users/family/', {
          headers: { Authorization: `Token ${token}` }
        });
        setFamilyMembers(familyRes.data);

        // دریافت نقش کاربر برای نمایش هوشمند گزینه‌ها
        const dashRes = await axios.get('/api/accounting/dashboard/', {
           headers: { Authorization: `Token ${token}` }
        });
        setUserRole(dashRes.data.role);

      } catch (e) { 
        console.error("خطا در دریافت اطلاعات", e); 
      }
    };
    fetchData();
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }

    try {
      const url = '/api/accounting/withdrawals/';
      const dataToSend = { ...formData };
      if (!dataToSend.target_user_id) {
          delete dataToSend.target_user_id;
      }

      await axios.post(url, dataToSend, {
        headers: { Authorization: `Token ${token}` }
      });
      
      setMessage({ type: 'success', text: '✅ درخواست برداشت با موفقیت ثبت شد.' });
      setTimeout(() => navigate('/dashboard'), 2000);
   } catch (error) {
      console.error(error);
      let errorText = 'خطا در ثبت درخواست.';
      if (error.response && error.response.data) {
          const data = error.response.data;
          if (data.amount) errorText = data.amount[0]; 
          else if (data.error) errorText = data.error;
          else if (data.detail) errorText = data.detail;
      }
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
          <TextField select label="برداشت از حسابِ:" name="target_user_id" value={formData.target_user_id} onChange={handleChange} fullWidth margin="normal" variant="outlined" helperText="اگر می‌خواهید از حساب زیرمجموعه‌ها برداشت کنید، نام او را انتخاب کنید.">
            <MenuItem value=""><em>خودم (حساب اصلی)</em></MenuItem>
            {familyMembers.map((member) => (
              <MenuItem key={member.id} value={member.id}>
                {member.full_name} ({member.membership_code})
              </MenuItem>
            ))}
          </TextField>

          <TextField select label="برداشت از کدام صندوق؟" name="source_type" value={formData.source_type} onChange={handleChange} fullWidth margin="normal" variant="outlined">
            <MenuItem value="SHORT_TERM">⏳ پس‌انداز کوتاه‌مدت (روزشمار)</MenuItem>
            <MenuItem value="LONG_TERM">📈 پس‌انداز بلندمدت (۳ ماهه)</MenuItem>
            <MenuItem value="PROFIT">🎁 سودهای دریافتی (آزاد)</MenuItem>
            <MenuItem value="LOAN">💰 پس‌انداز وام (عادی)</MenuItem>
            <MenuItem value="QARD">🤝 قرض‌الحسنه</MenuItem>
            <MenuItem value="FEE">💳 حق عضویت (لغو عضویت)</MenuItem>
            
            {/* نمایش گزینه فرهنگی فقط برای مدیر، ناظر و خود حساب‌های فرهنگی */}
            {(userRole === 'ADMIN' || userRole === 'OBSERVER' || userRole === 'CULTURAL') && (
                <MenuItem value="CULTURAL">🕌 امور فرهنگی و خیریه (بدون قفل)</MenuItem>
            )}
          </TextField>

          {formData.source_type === 'LONG_TERM' && (
              <Alert severity="warning" style={{marginTop: '5px', marginBottom: '10px', fontSize:'0.85rem'}}>
                  توجه: برداشت از حساب بلندمدت، <strong>تنها پس از گذشت ۳ ماه</strong> از زمان واریز امکان‌پذیر است.
              </Alert>
          )}

          {formData.source_type === 'CULTURAL' && (
              <Alert severity="success" style={{marginTop: '5px', marginBottom: '10px', fontSize:'0.85rem'}}>
                  <strong>امور فرهنگی:</strong> برداشت از این حساب شامل محدودیت و قفل ۳ ماهه <strong>نمی‌شود</strong>.
              </Alert>
          )}

          {formData.source_type === 'FEE' && (
              <Alert severity="error" style={{marginTop: '5px', marginBottom: '10px', fontSize:'0.85rem'}}>
                  <strong>هشدار مهم:</strong> برداشت حق عضویت به منزله <strong>انصراف از صندوق</strong> است. با این کار حساب شما غیرفعال شده و دیگر سود و وامی به شما تعلق نمی‌گیرد.
              </Alert>
          )}

          <CurrencyInput label="مبلغ برداشت (تومان)" name="amount" value={formData.amount} onChange={handleChange} fullWidth margin="normal" />
          
          <TextField label="توضیحات (اختیاری)" name="description" value={formData.description} onChange={handleChange} fullWidth margin="normal" multiline rows={2} placeholder="مثلاً: بابت قسط وام / نیاز فوری..." />

          <div style={{ display: 'flex', gap: '15px', marginTop:'30px' }}>
            <Button variant="contained" color="error" fullWidth size="large" onClick={handleSubmit} disabled={loading} style={{ fontWeight: 'bold' }}>
                {loading ? 'درحال ثبت...' : 'ثبت نهایی'}
            </Button>
            <Button variant="outlined" color="inherit" fullWidth onClick={() => navigate('/dashboard')}>بازگشت</Button>
          </div>
        </Box>
        {message && <Alert severity={message.type} style={{ marginTop: '20px' }}>{message.text}</Alert>}
      </Paper>
    </Container>
  );
}

export default Withdraw;