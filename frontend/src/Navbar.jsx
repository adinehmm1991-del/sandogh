import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box, Avatar } from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import { useNavigate } from 'react-router-dom';

// 1. وارد کردن عکس لوگو از پوشه assets
// نکته: اگر اسم فایل شما فرق دارد، اینجا اصلاح کنید (مثلا logo.jpg)
import logoImage from './assets/logo.png'; 

function Navbar() {
  const navigate = useNavigate();
  const isLoggedIn = !!localStorage.getItem('token');

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  return (
    <AppBar position="static" color="primary" elevation={0} style={{ marginBottom: '20px' }}>
      <Toolbar>
        
        {/* 2. نمایش لوگو */}
        <Box 
            component="img"
            src={logoImage}
            alt="لوگو صندوق"
            sx={{ 
                width: 63,       // عرض لوگو (40 پیکسل)
                height: 63,      // ارتفاع لوگو
                mr: 1,           // فاصله از راست (Margin Right)
                ml: 1,           // فاصله از چپ
                borderRadius: '50%' // گرد کردن گوشه‌ها (اختیاری)
            }}
        />

        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
          صندوق ثنای حق
        </Typography>

        {isLoggedIn && (
          <Button 
            variant="contained" 
            onClick={handleLogout} 
            startIcon={<LogoutIcon />}
            style={{ 
              backgroundColor: '#ff8f00', 
              color: '#fff',
              fontWeight: 'bold',
              borderRadius: '20px'
            }}
          >
            خروج
          </Button>
        )}
      </Toolbar>
    </AppBar>
  );
}

export default Navbar;