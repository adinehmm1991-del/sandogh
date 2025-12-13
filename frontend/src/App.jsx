import React, { useState } from 'react';
import axios from 'axios';
import { Routes, Route, useNavigate, Link } from 'react-router-dom';
import { Container, Paper, TextField, Button, Typography, Box } from '@mui/material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import rtlPlugin from 'stylis-plugin-rtl';
import { CacheProvider } from '@emotion/react';
import createCache from '@emotion/cache';
import { prefixer } from 'stylis';

// --- وارد کردن تمام صفحات و ابزارها ---
import { toEnglishDigits } from './utils';
import Navbar from './Navbar';
import Dashboard from './Dashboard';
import Deposit from './Deposit';
import Register from './Register';
import Profile from './Profile';
import Withdraw from './Withdraw';
import ForgotPassword from './ForgotPassword';
import ChangePassword from './ChangePassword';
import Family from './Family'; // <--- صفحه خانواده اضافه شد

// تنظیمات تم سایت
const theme = createTheme({
  direction: 'rtl',
  typography: {
    fontFamily: 'Vazirmatn, Tahoma, Arial',
    h1: { fontWeight: 700, fontSize: '1.8rem' },
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    button: { fontWeight: 'bold' },
  },
  palette: {
    primary: { main: '#1565c0', light: '#5e92f3', dark: '#003c8f' },
    secondary: { main: '#ff8f00' },
    background: { default: '#f4f7f6', paper: '#ffffff' },
  },
  shape: { borderRadius: 12 },
});

const cacheRtl = createCache({
  key: 'muirtl',
  stylisPlugins: [prefixer, rtlPlugin],
});

// --- صفحه ورود (LoginPage) ---
function LoginPage() {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleLogin = async () => {
    setMessage('درحال بررسی...');
    try {
      const response = await axios.post('https://sandogh-server.liara.run/api/users/login/', {
        phone_number: phone,
        password: password
      });
      localStorage.setItem('token', response.data.token);
      setMessage('✅ ورود موفقیت‌آمیز بود!');
      setTimeout(() => navigate('/dashboard'), 1000);
    } catch (error) {
      console.error(error);
      setMessage('❌ خطا: شماره موبایل یا رمز عبور اشتباه است.');
    }
  };

  return (
    <Container maxWidth="xs">
      <Paper elevation={3} style={{ padding: '30px', textAlign: 'center', marginTop: '50px' }}>
        <Typography variant="h5" component="h1" gutterBottom>صندوق ثنای حق</Typography>
        <Typography variant="body2" color="textSecondary" style={{marginBottom: '20px'}}>
          ورود اعضا
        </Typography>

        <Box component="form">
          <TextField 
            label="شماره موبایل" fullWidth margin="normal" dir="ltr" 
            value={phone} onChange={(e) => setPhone(toEnglishDigits(e.target.value))} 
            inputProps={{ autoComplete: 'new-password' }}
          />
          <TextField 
            label="رمز عبور" type="password" fullWidth margin="normal" dir="ltr" 
            value={password} onChange={(e) => setPassword(toEnglishDigits(e.target.value))} 
            inputProps={{ autoComplete: 'new-password' }}
          />
          <Button 
            variant="contained" fullWidth 
            style={{ marginTop: '20px', padding: '10px', backgroundColor: '#ff8f00', color: '#fff', fontSize: '1.1rem' }} 
            onClick={handleLogin}
          >
            ورود
          </Button>
        </Box>
        
        {message && <Typography variant="body1" style={{ marginTop: '20px', color: message.includes('خطا') ? 'red' : 'green' }}>{message}</Typography>}
        
        <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '14px' }}>
            <Link to="/forgot-password" style={{textDecoration: 'none', color: '#1976d2'}}>رمز عبور را فراموش کرده‌اید؟</Link>
            <div>حساب کاربری ندارید؟ <Link to="/register" style={{textDecoration: 'none', fontWeight: 'bold', color: '#2e7d32'}}>ثبت‌نام کنید</Link></div>
        </div>
      </Paper>
    </Container>
  );
}

// --- بدنه اصلی سایت (مسیرها) ---
function App() {
  return (
    <CacheProvider value={cacheRtl}>
      <ThemeProvider theme={theme}>
        
        <Navbar />
        
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/deposit" element={<Deposit />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/withdraw" element={<Withdraw />} />
          
          {/* مسیرهای جدید که جا افتاده بودند */}
          <Route path="/family" element={<Family />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/change-password" element={<ChangePassword />} />
        </Routes>

      </ThemeProvider>
    </CacheProvider>
  );
}

export default App;