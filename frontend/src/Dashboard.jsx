import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, Grid, Card, CardContent, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Divider, Box, TablePagination } from '@mui/material';
import { useNavigate } from 'react-router-dom';

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
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'; 
import ShowChartIcon from '@mui/icons-material/ShowChart';

function Dashboard() {
  const [data, setData] = useState(null);
  const [adminReport, setAdminReport] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const navigate = useNavigate();
  const queryParams = new URLSearchParams(window.location.search);
  const targetUserId = queryParams.get('user_id');

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('token');
      if (!token) { navigate('/'); return; }
      const config = { headers: { Authorization: `Token ${token}` } };

      try {
        const timeStamp = `_t=${Date.now()}`;
        let dashboardUrl = `/api/accounting/dashboard/?${timeStamp}`;
        let transactionsUrl = `/api/accounting/transactions/?${timeStamp}`;
        let withdrawalsUrl = `/api/accounting/withdrawals/?${timeStamp}`; 
        
        if (targetUserId) {
            dashboardUrl += `&user_id=${targetUserId}`;
            transactionsUrl += `&user_id=${targetUserId}`;
            withdrawalsUrl += `&user_id=${targetUserId}`;
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
                const reportRes = await axios.get(`/api/accounting/general-report/?${timeStamp}`, config);
                setAdminReport(reportRes.data);
            } catch (err) { console.error(err); }
        }

        const transRes = await axios.get(transactionsUrl, config);
        
        let pendingWithdrawals = [];
        try {
            const withRes = await axios.get(withdrawalsUrl, config);
            pendingWithdrawals = withRes.data
                .filter(w => w.status === 'PENDING')
                .map(w => ({
                    id: `w_${w.id}`,
                    amount: w.amount,
                    transaction_type: 'WITHDRAWAL_OTHER', 
                    date: w.created_at,
                    is_verified: false 
                }));
        } catch (e) { console.error("Error fetching withdrawals", e); }

        const allTrans = [...transRes.data, ...pendingWithdrawals]
            .sort((a, b) => new Date(b.date) - new Date(a.date));

        setTransactions(allTrans);
        setLoading(false);
      } catch (error) {
        if (error.response?.status === 401) { localStorage.removeItem('token'); navigate('/'); }
        if (error.response?.status === 403) { alert("دسترسی غیرمجاز"); navigate('/dashboard'); }
        setLoading(false);
      }
    };
    fetchData();
  }, [navigate, targetUserId]);

  const handleLogout = () => { localStorage.removeItem('token'); navigate('/'); };

  const handleChangePage = (event, newPage) => { setPage(newPage); };
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const typeTranslate = {
    'SHORT_TERM': 'پس‌انداز کوتاه‌مدت',
    'LONG_TERM': 'پس‌انداز بلندمدت',
    'MONTHLY': 'پس‌انداز بلندمدت', 
    'PROFIT_SAVING': 'پس‌انداز بلندمدت', 
    'LOAN_SAVING': 'پس‌انداز وام',
    'QARD': 'قرض‌الحسنه',
    'FEE': 'حق عضویت',
    'MANUAL_PROFIT': 'سود واریزی',
    'SADAQAH': 'صدقه',
    'SACRIFICE': 'قربانی',
    'BOOK': 'کتاب',
    'KHOMS_IMAM': 'سهم امام',
    'KHOMS_SADAT': 'سهم سادات',
    'WAQF': 'وقف (قدیم)',
    'WAQF_GEN': 'وقف عام',
    'WAQF_BOOK': 'وقف خاص (کتاب)',
    'WAQF_MEDIA': 'وقف خاص (محتوا)',
    'WAQF_INFRA': 'وقف خاص (زیرساخت)',
    'W_SHORT': 'برداشت (کوتاه‌مدت)',
    'W_LONG': 'برداشت (بلندمدت)',
    'W_SAVING': 'برداشت (پس‌انداز وام)',
    'W_PROFIT': 'برداشت (بلندمدت)', 
    'W_MONTHLY': 'برداشت (بلندمدت)', 
    'W_QARD': 'برداشت (قرض‌الحسنه)',
    'WITHDRAWAL_OTHER': 'برداشت وجه',
    'WITHDRAWAL': 'برداشت وجه',
    'W_FEE': 'برداشت (حق عضویت)',
    'W_MAN_PROFIT': 'برداشت از سود',
    'W_CULTURAL': 'برداشت (امور فرهنگی)'
  };

  if (loading) return <div style={{textAlign: 'center', marginTop: '50px'}}>در حال بارگذاری...</div>;
  if (!data) return <div>خطا در دریافت اطلاعات</div>;

  return (
    <Container maxWidth="md" style={{ marginTop: '30px', marginBottom: '50px' }}>
      
      {/* گزارش کلان هیئت مدیره (تفکیک شده و پاکسازی شده از موارد اضافی) */}
      {adminReport && (
        <Paper elevation={3} style={{ padding: '20px', marginBottom: '30px', borderTop: '5px solid #2e7d32', backgroundColor: '#f1f8e9' }}>
            <div style={{display:'flex', alignItems:'center', marginBottom:'15px', justifyContent:'space-between'}}>
                <div style={{display:'flex', alignItems:'center'}}>
                    <AdminPanelSettingsIcon color="success" style={{marginLeft:'10px'}}/>
                    <Typography variant="h6" color="success">گزارش کلان صندوق و امور فرهنگی</Typography>
                </div>
                <div style={{display:'flex', gap:'15px', fontSize:'0.9rem'}}>
                    <span style={{color:'#2e7d32', fontWeight:'bold'}}>✅ اعضای فعال: {adminReport.active_members}</span>
                </div>
            </div>
            <Divider style={{marginBottom:'15px'}} />
            <Grid container spacing={2}>
                <Grid item xs={6} md={3}><Typography variant="body2">کل اعضای سیستم: <strong>{adminReport.total_members}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">موجودی کل صندوق: <strong>{adminReport.total_capital?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">پس‌انداز وام: <strong>{adminReport.total_loan_saving?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">پس‌انداز کوتاه‌مدت: <strong>{adminReport.total_short_term?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">پس‌انداز بلندمدت: <strong>{adminReport.total_long_term?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2">قرض‌الحسنه: <strong>{adminReport.total_qard?.toLocaleString()}</strong></Typography></Grid>
            </Grid>

            <Divider style={{margin:'20px 0 15px 0', backgroundColor: '#81c784'}} />
            <Typography variant="subtitle2" style={{marginBottom:'15px', fontWeight: 'bold', color: '#1b5e20'}}>
                📊 موجودی تفکیک‌شده‌ی حساب‌های فرهنگی و خیریه:
            </Typography>
            <Grid container spacing={2} style={{backgroundColor: 'rgba(255,255,255,0.6)', padding: '10px', borderRadius: '8px'}}>
                <Grid item xs={6} md={4}><Typography variant="body2">صندوق صدقات: <strong style={{color:'#388e3c'}}>{adminReport.total_donation?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={4}><Typography variant="body2">صندوق قربانی: <strong style={{color:'#388e3c'}}>{adminReport.total_sacrifice?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={4}><Typography variant="body2">امور کتاب (صدقه): <strong style={{color:'#388e3c'}}>{adminReport.total_book?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={4}><Typography variant="body2">سهم امام: <strong style={{color:'#388e3c'}}>{adminReport.total_khoms_imam?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={4}><Typography variant="body2">سهم سادات: <strong style={{color:'#388e3c'}}>{adminReport.total_khoms_sadat?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2" style={{color: '#5d4037'}}>وقف عام: <strong>{adminReport.total_waqf_gen?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2" style={{color: '#5d4037'}}>وقف خاص کتاب: <strong>{adminReport.total_waqf_book?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2" style={{color: '#5d4037'}}>وقف خاص محتوا: <strong>{adminReport.total_waqf_media?.toLocaleString()}</strong></Typography></Grid>
                <Grid item xs={6} md={3}><Typography variant="body2" style={{color: '#5d4037'}}>وقف خاص زیرساخت: <strong>{adminReport.total_waqf_infra?.toLocaleString()}</strong></Typography></Grid>
            </Grid>
        </Paper>
      )}

      <Paper elevation={3} style={{ padding: '20px' }}>
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
                <Chip icon={<GroupAddIcon />} label={`معرفی: ${data.referrals_count || 0}`} color="primary" size="small" variant="outlined" style={{backgroundColor: '#e3f2fd', border: 'none', color: '#1565c0'}} />
                <Button variant="text" size="small" startIcon={<EditIcon />} onClick={() => navigate('/profile')}>ویرایش</Button>
                <Button variant="text" size="small" color="warning" startIcon={<KeyIcon />} onClick={() => navigate('/change-password')}>تغییر رمز</Button>
                
                {!targetUserId && (
                    <Button variant="outlined" size="small" color="secondary" startIcon={<FamilyRestroomIcon />} onClick={() => navigate('/family')}>ثبت نام خانواده</Button>
                )}
            </div>
          </div>
          
          <div style={{display:'flex', gap:'5px'}}>
              <Button variant="outlined" size="small" onClick={() => window.location.reload()}><RefreshIcon /></Button>
              <Button variant="outlined" color="error" onClick={handleLogout} size="small">خروج</Button>
          </div>
        </div>

        {/* کارت‌های آماری پروفایل شامل موجودی، سود تفکیک‌شده (برداشت شده و مانده قابل برداشت) و امتیاز وام */}
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card style={{ background: 'linear-gradient(135deg, #1e88e5 0%, #1565c0 100%)', color: 'white' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                    <AccountBalanceWalletIcon style={{ opacity: 0.8, marginLeft: '8px' }} />
                    <Typography variant="subtitle2" style={{ opacity: 0.9 }}>موجودی کل</Typography>
                </Box>
                <Typography variant="h5" style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                  {data.current_balance?.toLocaleString()} <span style={{fontSize:'0.6em'}}>تومان</span>
                </Typography>
                <div style={{ fontSize: '0.75rem', opacity: 0.9, backgroundColor: 'rgba(0,0,0,0.15)', padding: '6px', borderRadius: '5px' }}>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>⏳ کوتاه‌مدت:</span><span>{data.balances?.short_term?.toLocaleString()}</span></div>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>📈 بلندمدت:</span><span>{data.balances?.long_term?.toLocaleString()}</span></div>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>💰 پس‌انداز وام:</span><span>{data.balances?.loan_saving?.toLocaleString()}</span></div>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>🤝 قرض‌الحسنه:</span><span>{data.balances?.qard?.toLocaleString()}</span></div>
                </div>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card style={{ background: 'linear-gradient(135deg, #43a047 0%, #2e7d32 100%)', color: 'white' }}>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                    <TrendingUpIcon style={{ opacity: 0.8, marginLeft: '8px' }} />
                    <Typography variant="subtitle2" style={{ opacity: 0.9 }}>وضعیت سود</Typography>
                </Box>
                {/* نمایش باقی‌مانده سود قابل برداشت به عنوان مقدار اصلی */}
                <Typography variant="h5" style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                  {data.total_profit_received?.toLocaleString()} <span style={{fontSize:'0.6em'}}>تومان</span>
                </Typography>
                <div style={{ fontSize: '0.75rem', opacity: 0.9, backgroundColor: 'rgba(0,0,0,0.15)', padding: '6px', borderRadius: '5px' }}>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>📥 کل سود واریزی:</span><span>{data.total_profit_credited?.toLocaleString()}</span></div>
                    <div style={{display:'flex', justifyContent:'space-between'}}><span>📤 کل برداشت سود:</span><span>{data.profit_withdrawn?.toLocaleString()}</span></div>
                    <div style={{display:'flex', justifyContent:'space-between', fontWeight:'bold', color:'#fffde7'}}><span>✨ باقی‌مانده قابل برداشت:</span><span>{data.total_profit_received?.toLocaleString()}</span></div>
                </div>
              </CardContent>
            </Card>
          </Grid>

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
                    <div style={{display:'flex', justifyContent:'space-between', color:'#fffde7', fontWeight:'bold'}}><span>🔄استفاده‌شده:</span><span>{data.loan_points_details.from_transfers?.toLocaleString()}</span></div>
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

        <Typography variant="h6" gutterBottom style={{fontWeight:'bold', color:'#333'}}>دسترسی سریع</Typography>
        <Grid container spacing={2} style={{ marginBottom: '30px' }}>
            <Grid item xs={6} sm={3}>
                <Button variant="contained" fullWidth style={{ height: '60px', background: 'linear-gradient(45deg, #2e7d32 30%, #4caf50 90%)', fontSize:'1rem' }} startIcon={<AddIcon />} onClick={() => navigate(targetUserId ? `/deposit?user_id=${targetUserId}` : '/deposit')}>واریز وجه</Button>
            </Grid>
            <Grid item xs={6} sm={3}>
                <Button variant="contained" fullWidth style={{ height: '60px', background: 'linear-gradient(45deg, #c62828 30%, #e53935 90%)', fontSize:'1rem' }} startIcon={<RemoveIcon />} onClick={() => navigate(targetUserId ? `/withdraw?user_id=${targetUserId}` : '/withdraw')}>برداشت وجه</Button>
            </Grid>
            <Grid item xs={6} sm={3}>
                <Button variant="contained" fullWidth style={{ height: '60px', background: 'linear-gradient(45deg, #ef6c00 30%, #ff9800 90%)', fontSize:'1rem' }} startIcon={<CreditScoreIcon />} onClick={() => navigate(targetUserId ? `/loans?user_id=${targetUserId}` : '/loans')}>درخواست وام</Button>
            </Grid>
            <Grid item xs={6} sm={3}>
                <Button variant="contained" fullWidth style={{ height: '60px', background: 'linear-gradient(45deg, #6a1b9a 30%, #8e24aa 90%)', fontSize:'1rem' }} startIcon={<SwapHorizIcon />} onClick={() => navigate(targetUserId ? `/points?user_id=${targetUserId}` : '/points')}>انتقال امتیاز</Button>
            </Grid>
            
            {(data.role === 'ADMIN' || data.role === 'OBSERVER' || data.can_manage_loans) && (
                <Grid item xs={12}>
                    <Button variant="contained" fullWidth style={{ height: '60px', background: 'linear-gradient(45deg, #0277bd 30%, #039be5 90%)', fontSize:'1rem', marginTop: '10px' }} startIcon={<AdminPanelSettingsIcon />} onClick={() => navigate('/loan-manager')}>ورود به پنل اختصاصی مدیریت وام‌ها</Button>
                </Grid>
            )}
            
            {(data.role === 'ADMIN' || data.role === 'OBSERVER' || data.can_manage_investments) && (
                <Grid item xs={12}>
                    <Button variant="contained" fullWidth style={{ height: '60px', background: 'linear-gradient(45deg, #00695c 30%, #00897b 90%)', fontSize:'1rem', marginTop: '10px' }} startIcon={<ShowChartIcon />} onClick={() => navigate('/investment-manager')}>ورود به پنل اختصاصی مدیریت سرمایه‌گذاری‌ها</Button>
                </Grid>
            )}
        </Grid>

        <Typography variant="h6" gutterBottom>تراکنش‌های اخیر</Typography>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead style={{backgroundColor: '#f5f5f5'}}>
              <TableRow><TableCell>مبلغ</TableCell><TableCell>نوع</TableCell><TableCell>تاریخ</TableCell><TableCell align="center">وضعیت</TableCell></TableRow>
            </TableHead>
            <TableBody>
              {transactions.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((t) => {
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
        
        <Box sx={{ display: 'flex', justifyContent: 'center', width: '100%', direction: 'ltr', backgroundColor: '#f9f9f9', borderBottomLeftRadius: '8px', borderBottomRightRadius: '8px' }}>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50, 100]}
                component="div"
                count={transactions.length}
                page={page}
                onPageChange={handleChangePage}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                labelRowsPerPage="تعداد در صفحه:"
                labelDisplayedRows={({ from, to, count }) => `${from} تا ${to} از ${count}`}
                sx={{
                    borderTop: 'none',
                    '.MuiTablePagination-toolbar': { flexWrap: 'wrap', justifyContent: 'center' },
                    '.MuiTablePagination-selectLabel': { margin: 0, fontSize: '0.85rem' },
                    '.MuiTablePagination-displayedRows': { margin: 0, fontSize: '0.85rem' },
                    '.MuiTablePagination-actions': { marginLeft: '10px' }
                }}
            />
        </Box>
      </Paper>
    </Container>
  );
}

export default Dashboard;