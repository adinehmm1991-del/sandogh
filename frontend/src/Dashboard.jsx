import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, Grid, Card, CardContent, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Divider, Box } from '@mui/material';
import { useNavigate } from 'react-router-dom';

// آیکون‌ها
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';
import EditIcon from '@mui/icons-material/Edit';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import CreditScoreIcon from '@mui/icons-material/CreditScore';
import GroupAddIcon from '@mui/icons-material/GroupAdd';
import KeyIcon from '@mui/icons-material/Key';
import FamilyRestroomIcon from '@mui/icons-material/FamilyRestroom';
import RefreshIcon from '@mui/icons-material/Refresh';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'; // آیکون انتقال

function Dashboard() {
  const [data, setData] = useState(null);
  const [adminReport, setAdminReport] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const BASE_URL = 'https://sandogh-server.liara.run';

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('token');
      if (!token) { navigate('/'); return; }
      const config = { headers: { Authorization: `Token ${token}` } };

      const queryParams = new URLSearchParams(window.location.search);
      const targetUserId = queryParams.get('user_id');

      try {
        const timeStamp = `_t=${Date.now()}`;
        let dashboardUrl = `${BASE_URL}/api/accounting/dashboard/?${timeStamp}`;
        let transactionsUrl = `${BASE_URL}/api/accounting/transactions/?${timeStamp}`;
        
        if (targetUserId) {
            dashboardUrl += `&user_id=${targetUserId}`;
            transactionsUrl += `&user_id=${targetUserId}`;
        }

        const res = await axios.get(dashboardUrl, config);
        setData(res.data);

        if (!targetUserId) {
            if (!res.data.full_name || res.data.full_name === res.data.phone) {
                 navigate('/profile');
                 return;
            }
        }

        if (!targetUserId && (res.data.role === 'ADMIN' || res.data.role === 'OBSERVER')) {
            try {
                const reportRes = await axios.get(`${BASE_URL}/api/accounting/general-report/?${timeStamp}`, config);
                setAdminReport(reportRes.data);
            } catch (err) { console.error(err); }
        }

        const transRes = await axios.get(transactionsUrl, config);
        setTransactions(transRes.data);
        
        setLoading(false);
      } catch (error) {
        if (error.response?.status === 401) { localStorage.removeItem('token'); navigate('/'); }
        if (error.response?.status === 403) { alert("دسترسی غیرمجاز"); navigate('/dashboard'); }
        setLoading(false);
      }
    };
    fetchData();
  }, [navigate, window.location.search]);

  const handleLogout = () => { localStorage.removeItem('token'); navigate('/'); };

  // ترجمه انواع تراکنش (شامل موارد جدید)
  const typeTranslate = {
    'MONTHLY': 'واریز ماهیانه',
    'PROFIT_SAVING': 'پس‌انداز سود',
    'LOAN_SAVING': 'پس‌انداز وام',
    'QARD': 'قرض‌الحسنه',
    'DONATION': 'بلاعوض',
    'FEE': 'حق عضویت',
    'WITHDRAWAL': 'برداشت وجه',
    // انواع جدید برداشت
    'W_SAVING': 'برداشت (پس‌انداز وام)',
    'W_PROFIT': 'برداشت (سود)',
    'W_MONTHLY': 'برداشت (ماهیانه)',
    'W_QARD': 'برداشت (قرض‌الحسنه)',
    'WITHDRAWAL_OTHER': 'برداشت'
  };

  if (loading) return <div style={{textAlign: 'center', marginTop: '50px'}}>در حال بارگذاری...</div>;
  if (!data) return <div>خطا در دریافت اطلاعات</div>;

  return (
    <Container maxWidth="md" style={{ marginTop: '30px', marginBottom: '50px' }}>
      
      {/* گزارش مدیر */}
      {adminReport && (
        <Paper elevation={3} style={{ padding: '20px', marginBottom: '30px', borderTop: '5px solid #2e7d32', backgroundColor: '#f1f8e9' }}>
            <div style={{display:'flex', alignItems:'center', marginBottom:'15px', justifyContent:'space-between'}}>
                <div style={{display:'flex', alignItems:'center'}}>
                    <AdminPanelSettingsIcon color="success" style={{marginLeft:'10px'}}/>
                    <Typography variant="h6" color="success">گزارش کلی صندوق</Typography>
                </div>
                <div style={{display:'flex', gap:'15px', fontSize:'0.9rem'}}>
                    <span style={{color:'#2e7d32', fontWeight:'bold'}}>✅ فعال: {adminReport.active_members}</span>
                    <span style={{color:'#c62828', fontWeight:'bold'}}>❌ غیرفعال: {adminReport.inactive_members}</span>
                </div>
            </div>
            <Divider style={{marginBottom:'15px'}} />
            <Grid container spacing={2}>
                <Grid item xs={6} md={3}><Typography variant="body2">تعداد اعضا: <strong>{adminReport.total_members}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">کل سرمایه: <strong>{adminReport.total_capital?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">پس‌انداز وام: <strong>{adminReport.total_loan_saving?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">پس‌انداز سود: <strong>{adminReport.total_profit_saving?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">قرض‌الحسنه: <strong>{adminReport.total_qard?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2" color="error">کل بلاعوض: <strong>{adminReport.total_donation?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">تعهدات ماهانه: <strong>{adminReport.total_commitments?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">کل برداشتی‌ها: <strong>{adminReport.total_withdrawal?.toLocaleString()}</strong></Typography></Grid>
            </Grid>
        </Paper>
      )}

      <Paper elevation={3} style={{ padding: '20px' }}>
        
        {/* هدر پروفایل */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '30px', flexWrap:'wrap', gap:'10px' }}>
          <div>
            <Typography variant="h5" style={{fontWeight: 'bold', marginBottom:'5px'}}>
              {data.full_name} 
            </Typography>
            <Typography variant="caption" color="textSecondary" display="block">
              کد عضویت: {data.membership_code || '---'}
            </Typography>
            
            <div style={{ marginTop: '10px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                <Chip label={data.status} color={data.is_active ? "success" : "error"} size="small" variant="outlined" />
                
                <Chip 
                    icon={<GroupAddIcon />} 
                    label={`معرفی: ${data.referrals_count || 0}`} 
                    color="primary" size="small" variant="outlined" 
                    style={{backgroundColor: '#e3f2fd', border: 'none', color: '#1565c0'}}
                />
                
                <Button variant="text" size="small" startIcon={<EditIcon />} onClick={() => navigate('/profile')}>
                    ویرایش
                </Button>
                <Button variant="text" size="small" color="warning" startIcon={<KeyIcon />} onClick={() => navigate('/change-password')}>
                    رمز
                </Button>
                
                {!new URLSearchParams(window.location.search).get('user_id') && (
                    <Button 
                        variant="outlined" size="small" color="secondary" 
                        startIcon={<FamilyRestroomIcon />} 
                        onClick={() => navigate('/family')}
                    >
                        خانواده
                    </Button>
                )}
            </div>
          </div>
          
          <div style={{display:'flex', gap:'5px'}}>
              <Button variant="outlined" size="small" onClick={() => window.location.reload()}>
                <RefreshIcon />
              </Button>
              <Button variant="outlined" color="error" onClick={handleLogout} size="small">خروج</Button>
          </div>
        </div>

        {/* کارت‌های آمار */}
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card style={{ background: 'linear-gradient(135deg, #1e88e5 0%, #1565c0 100%)', color: 'white' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                    <AccountBalanceWalletIcon style={{ opacity: 0.8, marginLeft: '8px' }} />
                    <Typography variant="subtitle2" style={{ opacity: 0.9 }}>موجودی کل</Typography>
                </Box>
                <Typography variant="h5" style={{ fontWeight: 'bold' }}>{data.current_balance?.toLocaleString()} <span style={{fontSize:'0.6em'}}>تومان</span></Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card style={{ background: 'linear-gradient(135deg, #43a047 0%, #2e7d32 100%)', color: 'white' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                    <TrendingUpIcon style={{ opacity: 0.8, marginLeft: '8px' }} />
                    <Typography variant="subtitle2" style={{ opacity: 0.9 }}>سود دریافتی</Typography>
                </Box>
                <Typography variant="h5" style={{ fontWeight: 'bold' }}>{data.total_profit_received?.toLocaleString()} <span style={{fontSize:'0.6em'}}>تومان</span></Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* کارت امتیاز وام (اصلاح شده با جزئیات جدید) */}
          <Grid item xs={12} md={4}>
            <Card style={{ background: 'linear-gradient(135deg, #fb8c00 0%, #ef6c00 100%)', color: 'white', position: 'relative' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                    <CreditScoreIcon style={{ opacity: 0.8, marginLeft: '8px' }} />
                    <Typography variant="subtitle2" style={{ opacity: 0.9 }}>امتیاز وام</Typography>
                </Box>
                <Typography variant="h5" style={{ fontWeight: 'bold', marginBottom: '10px' }}>
                  {data.loan_points_details.total_limit?.toLocaleString()} <span style={{fontSize:'0.6em'}}>تومان</span>
                </Typography>

                <div style={{ fontSize: '0.75rem', opacity: 0.9, marginBottom: '10px', backgroundColor: 'rgba(0,0,0,0.1)', padding: '5px', borderRadius: '5px' }}>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>🎁 بلاعوض:</span><span>{data.loan_points_details.from_donations?.toLocaleString()}</span></div>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>👥 معرف:</span><span>{data.loan_points_details.from_referrals?.toLocaleString()}</span></div>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>💰 سپرده:</span><span>{data.loan_points_details.from_savings?.toLocaleString()}</span></div>
                    {/* اضافه شدن بخش نقل و انتقالات */}
                    <div style={{display:'flex', justifyContent:'space-between', color:'#fffde7', fontWeight:'bold'}}><span>🔄 انتقالی:</span><span>{data.loan_points_details.from_transfers?.toLocaleString()}</span></div>
                </div>

                {data.loan_points_details.has_loan_deposit ? (
                    <div style={{ backgroundColor: 'rgba(255,255,255,0.2)', padding: '8px', borderRadius: '8px', fontSize: '0.85rem' }}>
                        {data.loan_points_details.is_eligible ? (
                            <div style={{ display: 'flex', alignItems: 'center' }}><span>✅</span><span style={{ marginRight: '5px' }}>شرط ۳ ماه تکمیل شد.</span></div>
                        ) : (
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                    <span>⏳ در انتظار</span><span>{data.loan_points_details.days_remaining} روز مانده</span>
                                </div>
                                <div style={{ width: '100%', height: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '2px' }}>
                                    <div style={{ width: `${Math.min(100, (data.loan_points_details.days_passed / 90) * 100)}%`, height: '100%', background: '#fff', borderRadius: '2px' }}></div>
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <Typography variant="caption" style={{ opacity: 0.8 }}>بدون پس‌انداز وام</Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Divider style={{ margin: '30px 0' }} />

        {/* --- بخش جدید: دکمه‌های دسترسی سریع --- */}
        <Typography variant="h6" gutterBottom style={{fontWeight:'bold', color:'#333'}}>دسترسی سریع</Typography>
        <Grid container spacing={2} style={{ marginBottom: '30px' }}>
            
            {/* دکمه واریز */}
            <Grid item xs={6} sm={3}>
                <Button 
                    variant="contained" fullWidth 
                    style={{ height: '60px', background: 'linear-gradient(45deg, #2e7d32 30%, #4caf50 90%)', fontSize:'1rem' }}
                    startIcon={<AddIcon />} 
                    onClick={() => navigate('/deposit')}
                >
                    واریز وجه
                </Button>
            </Grid>

            {/* دکمه برداشت */}
            <Grid item xs={6} sm={3}>
                <Button 
                    variant="contained" fullWidth 
                    style={{ height: '60px', background: 'linear-gradient(45deg, #c62828 30%, #e53935 90%)', fontSize:'1rem' }}
                    startIcon={<RemoveIcon />} 
                    onClick={() => navigate('/withdraw')}
                >
                    برداشت وجه
                </Button>
            </Grid>
            
            {/* دکمه وام */}
            <Grid item xs={6} sm={3}>
                <Button 
                    variant="contained" fullWidth 
                    style={{ height: '60px', background: 'linear-gradient(45deg, #ef6c00 30%, #ff9800 90%)', fontSize:'1rem' }}
                    startIcon={<CreditScoreIcon />} 
                    onClick={() => navigate('/loans')}
                >
                    درخواست وام
                </Button>
            </Grid>

            {/* دکمه انتقال امتیاز */}
            <Grid item xs={6} sm={3}>
                <Button 
                    variant="contained" fullWidth 
                    style={{ height: '60px', background: 'linear-gradient(45deg, #6a1b9a 30%, #8e24aa 90%)', fontSize:'1rem' }}
                    startIcon={<SwapHorizIcon />} 
                    onClick={() => navigate('/points')}
                >
                    انتقال امتیاز
                </Button>
            </Grid>
        </Grid>

        <Typography variant="h6" gutterBottom>تراکنش‌های اخیر</Typography>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead style={{backgroundColor: '#f5f5f5'}}>
              <TableRow><TableCell>مبلغ</TableCell><TableCell>نوع</TableCell><TableCell>تاریخ</TableCell><TableCell align="center">وضعیت</TableCell></TableRow>
            </TableHead>
            <TableBody>
              {transactions.slice(0, 10).map((t) => {
                // تشخیص رنگ و نوع برای تمام انواع برداشت
                const isWithdrawal = t.transaction_type.startsWith('W_') || t.transaction_type === 'WITHDRAWAL';
                
                return (
                    <TableRow key={t.id} hover>
                      <TableCell style={{fontWeight:'bold', color: isWithdrawal ? 'red' : 'green', direction:'ltr'}}>
                          {t.amount.toLocaleString()}
                      </TableCell>
                      <TableCell>{typeTranslate[t.transaction_type] || t.transaction_type}</TableCell>
                      <TableCell dir="ltr" style={{color:'#666', fontSize:'0.9em'}}>{new Date(t.date).toLocaleDateString('fa-IR')}</TableCell>
                      <TableCell align="center">
                          {t.is_verified ? <Chip label="تایید" color="success" size="small" variant="outlined"/> : <Chip label="انتظار" color="warning" size="small" variant="outlined"/>}
                      </TableCell>
                    </TableRow>
                );
              })}
              {transactions.length === 0 && <TableRow><TableCell colSpan={4} align="center" style={{padding:'20px'}}>هیچ تراکنشی یافت نشد.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Container>
  );
}

export default Dashboard;