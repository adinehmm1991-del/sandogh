import React, { useState } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, Box, Alert } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CurrencyInput from './CurrencyInput';

function Withdraw() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  
  const [formData, setFormData] = useState({
    amount: '',
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
      // نکته حیاتی: https:// حتما باید باشد
      // نکته حیاتی ۲: بعد از .run فقط یک اسلش / باشد
      const url = 'https://sandogh-server.liara.run/api/accounting/withdrawals/';
      
      await axios.post(url, formData, {
        headers: { Authorization: `Token ${token}` }
      });
      
      setMessage({ type: 'success', text: '✅ درخواست برداشت ثبت شد.' });
      setTimeout(() => navigate('/dashboard', { replace: true }), 2000);
    } catch (error) {
      console.error("Error URL:", 'https://sandogh-server.liara.run/api/accounting/withdrawals/');
      console.error(error);
      setMessage({ type: 'error', text: 'خطا در ثبت درخواست.' });
    } finally {
        setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm" style={{ marginTop: '50px' }}>
      <Paper elevation={3} style={{ padding: '30px' }}>
        <Typography variant="h5" gutterBottom color="error">درخواست برداشت</Typography>
        <Box component="form">
          <CurrencyInput label="مبلغ (تومان)" name="amount" value={formData.amount} onChange={handleChange} fullWidth margin="normal" />
          <TextField label="توضیحات" name="description" value={formData.description} onChange={handleChange} fullWidth margin="normal" multiline rows={2} />
          
          <div style={{ display: 'flex', gap: '10px', marginTop:'20px' }}>
            <Button variant="contained" color="error" fullWidth onClick={handleSubmit} disabled={loading}>
                {loading ? '...' : 'ثبت'}
            </Button>
            <Button variant="outlined" fullWidth onClick={() => navigate('/dashboard')}>انصراف</Button>
          </div>
        </Box>
        {message && <Alert severity={message.type} style={{ marginTop: '20px' }}>{message.text}</Alert>}
      </Paper>
    </Container>
  );
}

export default Withdraw;