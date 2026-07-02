import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, Box, Alert, MenuItem } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import DatePicker from "react-multi-date-picker";
import persian from "react-date-object/calendars/persian";
import persian_fa from "react-date-object/locales/persian_fa";

// آدرس اصلاح شد
const BASE_URL = ''; 

function Profile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [birthDate, setBirthDate] = useState(null);

  const [formData, setFormData] = useState({
    full_name: '',
    national_code: '',
    card_number: '',
    shaba_number: '',
    gender: 'MALE',
  });

  const genderOptions = [{ value: 'MALE', label: 'آقا' }, { value: 'FEMALE', label: 'خانم' }];

  useEffect(() => {
    const fetchProfile = async () => {
      const token = localStorage.getItem('token');
      if (!token) { navigate('/'); return; }
      try {
        const res = await axios.get(`${BASE_URL}/api/users/profile/`, {
          headers: { Authorization: `Token ${token}` }
        });
        const data = res.data;
        setFormData({
            full_name: data.full_name || '',
            national_code: data.national_code || '',
            card_number: data.card_number || '',
            shaba_number: data.shaba_number || '',
            gender: data.gender || 'MALE'
        });
        if (data.birth_date) setBirthDate(new Date(data.birth_date));
        setLoading(false);
      } catch (error) {
        console.error(error);
        setLoading(false); // حتی اگر خطا داد، لودینگ را بردار تا صفحه سفید نماند
      }
    };
    fetchProfile();
  }, [navigate]);

  const handleChange = (e) => { setFormData({ ...formData, [e.target.name]: e.target.value }); };

  const handleSubmit = async () => {
    const token = localStorage.getItem('token');
    let finalBirth = null;
    if (birthDate) {
        finalBirth = birthDate.toDate ? birthDate.toDate().toISOString().split('T')[0] : new Date(birthDate).toISOString().split('T')[0];
    }
    try {
      await axios.patch(`${BASE_URL}/api/users/profile/`, { ...formData, birth_date: finalBirth }, {
        headers: { Authorization: `Token ${token}` }
      });
      setMessage({ type: 'success', text: '✅ ذخیره شد.' });
      setTimeout(() => navigate('/dashboard', { replace: true }), 1500);
    } catch (error) {
      setMessage({ type: 'error', text: 'خطا در ذخیره.' });
    }
  };

  if (loading) return <div style={{textAlign:'center', marginTop:'50px'}}>درحال بارگذاری...</div>;

  return (
    <Container maxWidth="sm" style={{ marginTop: '30px' }}>
      <Paper elevation={3} style={{ padding: '20px' }}>
        <Typography variant="h5" gutterBottom>تکمیل مشخصات</Typography>
        <Box component="form">
          <TextField label="نام و نام خانوادگی" name="full_name" fullWidth margin="normal" value={formData.full_name} onChange={handleChange} />
          <TextField label="کد ملی" name="national_code" fullWidth margin="normal" value={formData.national_code} onChange={handleChange} dir="ltr" />
          <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <TextField select label="جنسیت" name="gender" value={formData.gender} onChange={handleChange} style={{width: '40%'}} size="small">
                {genderOptions.map((o) => (<MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>))}
              </TextField>
              <div style={{ width: '60%' }}>
                <DatePicker 
                  value={birthDate} 
                  onChange={setBirthDate} 
                  calendar={persian} 
                  locale={persian_fa} 
                  placeholder="📅 تاریخ تولد خود را انتخاب کنید" 
                  style={{ width: "100%", height: "40px", borderRadius: "4px", border: "1px solid #c4c4c4", padding: "0 14px", fontFamily: "inherit", fontSize: "0.9rem" }} 
                />
              </div>
          </div>
          <TextField label="شماره کارت" name="card_number" fullWidth margin="normal" value={formData.card_number} onChange={handleChange} dir="ltr" />
          <TextField label="شماره شبا" name="shaba_number" fullWidth margin="normal" value={formData.shaba_number} onChange={handleChange} dir="ltr" />
          <Button variant="contained" fullWidth onClick={handleSubmit} style={{ marginTop: '20px' }}>ذخیره</Button>
        </Box>
        {message && <Alert severity={message.type} style={{marginTop: '10px'}}>{message.text}</Alert>}
      </Paper>
    </Container>
  );
}
export default Profile;