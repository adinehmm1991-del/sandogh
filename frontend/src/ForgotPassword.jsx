import React, { useState } from 'react';
import axios from 'axios';
import { Container, Paper, TextField, Button, Typography, Alert } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { toEnglishDigits } from './utils';

function ForgotPassword() {
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);
    try {
      await axios.post('https://sandogh-server.liara.run/api/users/forgot-password/', {
        phone_number: phone
      });
      setMessage({ type: 'success', text: '✅ رمز عبور جدید پیامک شد.' });
      setTimeout(() => navigate('/'), 3000);
    } catch (error) {
      setMessage({ type: 'error', text: 'خطا: شماره موبایل یافت نشد.' });
    } finally {
        setLoading(false);
    }
  };

  return (
    <Container maxWidth="xs" style={{ marginTop: '100px' }}>
      <Paper elevation={3} style={{ padding: '30px', textAlign: 'center' }}>
        <Typography variant="h6" gutterBottom>بازیابی رمز عبور</Typography>
        <Typography variant="body2" color="textSecondary" mb={2}>
            شماره موبایل خود را وارد کنید تا رمز جدید پیامک شود.
        </Typography>
        
        <TextField 
            label="شماره موبایل" fullWidth margin="normal" dir="ltr"
            value={phone} onChange={(e) => setPhone(toEnglishDigits(e.target.value))} 
        />
        
        <Button variant="contained" color="warning" fullWidth onClick={handleSubmit} disabled={loading} style={{marginTop: '20px'}}>
            {loading ? 'درحال ارسال...' : 'ارسال رمز جدید'}
        </Button>

        {message && <Alert severity={message.type} style={{marginTop: '20px'}}>{message.text}</Alert>}
        
        <Button variant="text" onClick={() => navigate('/')} style={{marginTop: '10px'}}>بازگشت به ورود</Button>
      </Paper>
    </Container>
  );
}
export default ForgotPassword;