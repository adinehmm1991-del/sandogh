import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, Box, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CurrencyInput from './CurrencyInput'; 
import { toEnglishDigits } from './utils';

function PointTransfer() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [history, setHistory] = useState([]);
  
  const queryParams = new URLSearchParams(window.location.search);
  const targetUserId = queryParams.get('user_id');

  const [formData, setFormData] = useState({
    target_membership_code: '',
    points: ''
  });

  const fetchHistory = async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      let url = '/api/accounting/points/transfer/';
      if (targetUserId) url += `?user_id=${targetUserId}`;
      const res = await axios.get(url, { headers: { Authorization: `Token ${token}` } });
      setHistory(res.data);
    } catch (err) {
      console.error('خطا در دریافت تاریخچه:', err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [targetUserId]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }

    try {
      const payload = {
          target_membership_code: toEnglishDigits(formData.target_membership_code),
          points: formData.points.replace(/,/g, '') 
      };
      if (targetUserId) payload.target_user_id = targetUserId; 

      await axios.post('/api/accounting/points/transfer/', payload, {
        headers: { Authorization: `Token ${token}` }
      });
      
      setMessage({ type: 'success', text: '✅ انتقال امتیاز با موفقیت انجام شد.' });
      setFormData({ target_membership_code: '', points: '' });
      fetchHistory(); // بروزرسانی جدول پس از ثبت موفق
   } catch (error) {
      let errorText = 'خطا در ثبت درخواست.';
      if (error.response?.data?.error) {
          errorText = error.response.data.error;
      } else if (error.response?.data) {
          errorText = Object.values(error.response.data)[0];
      }
      setMessage({ type: 'error', text: errorText });
    } finally {
        setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" style={{ marginTop: '40px', marginBottom: '40px' }}>
      <Paper elevation={4} style={{ padding: '30px', borderRadius: '15px', marginBottom: '30px' }}>
        <Typography variant="h5" align="center" style={{ fontWeight: 'bold', color: '#6a1b9a', marginBottom: '20px' }}>
           انتقال امتیاز وام {targetUserId ? '(زیرمجموعه)' : ''}
        </Typography>

        <Box component="form">
          <TextField 
            label="کد عضویت مقصد" 
            name="target_membership_code" 
            value={formData.target_membership_code} 
            onChange={handleChange} 
            fullWidth margin="normal" dir="ltr"
          />
          
          <CurrencyInput 
            label="مقدار امتیاز (تومان)" 
            name="points" 
            value={formData.points} 
            onChange={handleChange} 
            fullWidth margin="normal" 
          />

          <div style={{ display: 'flex', gap: '15px', marginTop:'30px' }}>
            <Button variant="contained" color="secondary" fullWidth size="large" onClick={handleSubmit} disabled={loading}>
                {loading ? 'درحال ثبت...' : 'ثبت درخواست'}
            </Button>
            <Button variant="outlined" color="inherit" fullWidth onClick={() => navigate(targetUserId ? `/dashboard?user_id=${targetUserId}` : '/dashboard')}>
                بازگشت
            </Button>
          </div>
        </Box>
        {message && <Alert severity={message.type} style={{ marginTop: '20px' }}>{message.text}</Alert>}
      </Paper>

      {history.length > 0 && (
        <Paper elevation={3} style={{ padding: '20px', borderRadius: '15px' }}>
          <Typography variant="h6" style={{ marginBottom: '15px', color: '#333' }}>تاریخچه درخواست‌های انتقال</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow style={{ backgroundColor: '#f5f5f5' }}>
                  <TableCell><strong>گیرنده</strong></TableCell>
                  <TableCell><strong>مقدار امتیاز</strong></TableCell>
                  <TableCell><strong>وضعیت</strong></TableCell>
                  <TableCell><strong>تاریخ</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.receiver_name} ({row.receiver_code})</TableCell>
                    <TableCell>{row.amount.toLocaleString()} تومان</TableCell>
                    <TableCell>{row.status}</TableCell>
                    <TableCell>{row.date}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Container>
  );
}

export default PointTransfer;