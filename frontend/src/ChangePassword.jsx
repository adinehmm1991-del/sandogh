import React, { useState } from 'react';
import axios from 'axios';
import { Container, Paper, TextField, Button, Typography, Alert, Box } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { toEnglishDigits } from './utils';

function ChangePassword() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    // تبدیل اعداد فارسی به انگلیسی هنگام تایپ
    setFormData({ ...formData, [e.target.name]: toEnglishDigits(e.target.value) });
  };

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);

    if (formData.new_password !== formData.confirm_password) {
        setMessage({ type: 'error', text: 'تکرار رمز عبور مطابقت ندارد.' });
        setLoading(false);
        return;
    }

    const token = localStorage.getItem('token');
    try {
      await axios.put('https://sandogh-server.liara.run/api/users/change-password/', {
          old_password: formData.old_password,
          new_password: formData.new_password
      }, {
        headers: { Authorization: `Token ${token}` }
      });
      
      setMessage({ type: 'success', text: '✅ رمز عبور با موفقیت تغییر کرد.' });
      setTimeout(() => navigate('/dashboard'), 2000);

    } catch (error) {
      if (error.response && error.response.data && error.response.data.error) {
          setMessage({ type: 'error', text: error.response.data.error });
      } else {
          setMessage({ type: 'error', text: 'خطا در تغییر رمز.' });
      }
    } finally {
        setLoading(false);
    }
  };

  return (
    <Container maxWidth="xs" style={{ marginTop: '50px' }}>
      <Paper elevation={3} style={{ padding: '30px' }}>
        <Typography variant="h6" gutterBottom>تغییر رمز عبور</Typography>
        
        <Box component="form">
            <TextField 
                label="رمز عبور فعلی" name="old_password" type="password"
                fullWidth margin="normal" dir="ltr"
                value={formData.old_password} onChange={handleChange} 
            />
            <TextField 
                label="رمز عبور جدید" name="new_password" type="password"
                fullWidth margin="normal" dir="ltr"
                value={formData.new_password} onChange={handleChange} 
            />
            <TextField 
                label="تکرار رمز جدید" name="confirm_password" type="password"
                fullWidth margin="normal" dir="ltr"
                value={formData.confirm_password} onChange={handleChange} 
            />

            <Button 
                variant="contained" color="primary" fullWidth 
                onClick={handleSubmit} disabled={loading} 
                style={{ marginTop: '20px' }}
            >
                {loading ? 'درحال ذخیره...' : 'تغییر رمز'}
            </Button>
            
            <Button variant="outlined" color="secondary" fullWidth onClick={() => navigate('/dashboard')} style={{ marginTop: '10px' }}>
                انصراف
            </Button>
        </Box>

        {message && <Alert severity={message.type} style={{marginTop: '20px'}}>{message.text}</Alert>}
      </Paper>
    </Container>
  );
}

export default ChangePassword;