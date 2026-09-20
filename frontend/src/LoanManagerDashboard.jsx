import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
  Container, Paper, Typography, Grid, Card, CardContent, Button, Divider, Box,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, FormControl, InputLabel, Select, MenuItem,
  Tabs, Tab, Checkbox
} from '@mui/material';

import DatePicker from "react-multi-date-picker";
import persian from "react-date-object/calendars/persian";
import persian_fa from "react-date-object/locales/persian_fa";

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import EditIcon from '@mui/icons-material/Edit';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import SavingsIcon from '@mui/icons-material/Savings';
import ListAltIcon from '@mui/icons-material/ListAlt';

// --- کامپوننت اختصاصی ورودی مبلغ برای جلوگیری از قفل شدن کیبورد ---
const InstallmentInput = ({ inst, installments, setInstallments }) => {
    const [isFocused, setIsFocused] = useState(false);

    return (
        <input 
            type="text"
            inputMode="numeric"
            value={isFocused ? inst.amount : (inst.amount ? Number(inst.amount).toLocaleString() : '')}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onChange={(e) => {
                const val = e.target.value.replace(/\D/g, '');
                setInstallments(installments.map(i => i.id === inst.id ? { ...i, amount: val } : i));
            }}
            style={{
                width: '120px',
                padding: '8px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                textAlign: 'left',
                direction: 'ltr',
                fontFamily: 'inherit',
                backgroundColor: isFocused ? '#fffde7' : '#fff', 
                outline: isFocused ? '2px solid #1976d2' : 'none'
            }}
        />
    );
};

const LoanManagerDashboard = () => {
    const [data, setData] = useState(null);
    const [loans, setLoans] = useState([]);
    const [savingsReport, setSavingsReport] = useState([]);
    const [loading, setLoading] = useState(true);
    const [tabIndex, setTabIndex] = useState(0);
    const navigate = useNavigate();

    const [openApproveDialog, setOpenApproveDialog] = useState(false);
    const [selectedLoan, setSelectedLoan] = useState(null);
    const [approveData, setApproveData] = useState({ duration_months: 12, granted_date: new Date().toISOString().split('T')[0], status: 'APPROVED' });

    const [openManualDialog, setOpenManualDialog] = useState(false);
    const [manualData, setManualData] = useState({ target_membership_code: '', amount: '', duration_months: 12, granted_date: new Date().toISOString().split('T')[0], description: 'وام دستی مصوب' });

    const [openInstallmentsDialog, setOpenInstallmentsDialog] = useState(false);
    const [installments, setInstallments] = useState([]);
    const [selectedLoanForInst, setSelectedLoanForInst] = useState(null);

    useEffect(() => {
        fetchDashboardData();
        fetchLoans();
        fetchSavingsReport();
    }, []);

    const fetchDashboardData = async () => {
        try {
            const token = localStorage.getItem('token'); 
            const config = { headers: { Authorization: `Token ${token}` } };
            const response = await axios.get(`/api/accounting/reports/loan-dashboard/?_t=${Date.now()}`, config);
            setData(response.data);
            setLoading(false);
        } catch (err) { setLoading(false); }
    };

    const fetchLoans = async () => {
        try {
            const token = localStorage.getItem('token'); 
            const config = { headers: { Authorization: `Token ${token}` } };
            const response = await axios.get(`/api/accounting/manager/loans/?_t=${Date.now()}`, config);
            setLoans(response.data);
        } catch (err) {}
    };

    const fetchSavingsReport = async () => {
        try {
            const token = localStorage.getItem('token'); 
            const config = { headers: { Authorization: `Token ${token}` } };
            const response = await axios.get(`/api/accounting/manager/loan-savings/?_t=${Date.now()}`, config);
            setSavingsReport(response.data);
        } catch (err) {}
    };

    const openInstallments = async (loan) => {
        setSelectedLoanForInst(loan);
        setOpenInstallmentsDialog(true);
        fetchInstallments(loan.id);
    };

    const fetchInstallments = async (loanId) => {
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`/api/accounting/manager/loans/${loanId}/installments/`, { headers: { Authorization: `Token ${token}` } });
            setInstallments(res.data);
        } catch (err) { console.error("خطا در دریافت اقساط"); }
    };

    const toggleInstallmentStatus = async (inst) => {
        try {
            const token = localStorage.getItem('token');
            await axios.patch(`/api/accounting/manager/loans/${selectedLoanForInst.id}/installments/`, {
                id: inst.id,
                is_paid: !inst.is_paid
            }, { headers: { Authorization: `Token ${token}` } });
            fetchInstallments(selectedLoanForInst.id); 
            fetchDashboardData(); // آپدیت ظرفیت آزاد در پس‌زمینه
        } catch (err) { alert('خطا در ذخیره وضعیت پرداخت'); }
    };

    const saveInstallmentAmount = async (inst) => {
        try {
            const token = localStorage.getItem('token');
            await axios.patch(`/api/accounting/manager/loans/${selectedLoanForInst.id}/installments/`, {
                id: inst.id,
                amount: inst.amount
            }, { headers: { Authorization: `Token ${token}` } });
            alert('✅ مبلغ قسط بروزرسانی شد.');
            fetchInstallments(selectedLoanForInst.id);
            fetchDashboardData();
        } catch (err) { alert('خطا در بروزرسانی مبلغ'); }
    };

    const handleOpenApprove = (loan, isEdit = false) => {
        setSelectedLoan(loan);
        setApproveData({ 
            duration_months: loan.duration_months || 12, 
            granted_date: loan.granted_date || new Date().toISOString().split('T')[0],
            status: isEdit ? loan.status : 'APPROVED'
        });
        setOpenApproveDialog(true);
    };

    const submitApprove = async () => {
        try {
            const token = localStorage.getItem('token'); 
            const config = { headers: { Authorization: `Token ${token}` } };
            await axios.patch(`/api/accounting/manager/loans/${selectedLoan.id}/`, approveData, config);
            
            alert('✅ تغییرات با موفقیت ذخیره شد.');
            setOpenApproveDialog(false);
            fetchDashboardData(); 
            fetchLoans();         
        } catch (err) { alert('❌ خطا در ارتباط با سرور!'); }
    };

    const submitManualLoan = async () => {
        if(!manualData.target_membership_code || !manualData.amount){ alert('کد عضویت و مبلغ الزامی است!'); return; }
        try {
            const token = localStorage.getItem('token'); 
            const config = { headers: { Authorization: `Token ${token}` } };
            await axios.post(`/api/accounting/manager/loans/`, {
                target_membership_code: manualData.target_membership_code,
                amount: manualData.amount.replace(/,/g, ''),
                status: 'APPROVED',
                is_manual: true,
                duration_months: manualData.duration_months,
                granted_date: manualData.granted_date,
                description: manualData.description
            }, config);
            
            alert('✅ وام دستی ثبت شد.');
            setOpenManualDialog(false);
            setManualData({ ...manualData, target_membership_code: '', amount: '' });
            fetchDashboardData();
            fetchLoans();
        } catch (err) { alert(err.response?.data?.target_membership_code || '❌ خطا در ثبت وام دستی!'); }
    };

    const handleAmountChange = (e, stateSetter, stateData, fieldName) => {
        const rawValue = e.target.value.replace(/,/g, '');
        if (!isNaN(rawValue)) { stateSetter({ ...stateData, [fieldName]: rawValue }); }
    };

    const handleDateChange = (date, stateSetter, stateData, fieldName) => {
        if (date) {
            const d = date.toDate();
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            stateSetter({ ...stateData, [fieldName]: `${year}-${month}-${day}` });
        }
    };

    if (loading) return <div style={{textAlign: 'center', marginTop: '50px', direction: 'rtl', fontFamily: 'Tahoma'}}>در حال بارگذاری...</div>;
    if (!data) return null;

    const totalPaidInst = installments.filter(i => i.is_paid).reduce((sum, i) => sum + Number(i.amount), 0);
    const totalRemInst = installments.filter(i => !i.is_paid).reduce((sum, i) => sum + Number(i.amount), 0);
    const delayedInst = installments.filter(i => !i.is_paid && new Date(i.due_date) < new Date()).length;

    return (
        <Container maxWidth="lg" style={{ marginTop: '40px', marginBottom: '50px', direction: 'rtl', fontFamily: 'Tahoma' }}>
            <Paper elevation={4} style={{ padding: '30px', borderRadius: '15px' }}>
                
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                    <Typography variant="h5" style={{ fontWeight: 'bold', color: '#1565c0' }}>داشبورد اختصاصی مدیریت وام</Typography>
                    <Button variant="outlined" startIcon={<ArrowBackIcon style={{marginLeft:'8px'}} />} onClick={() => navigate('/dashboard')}>بازگشت</Button>
                </Box>

                <Divider style={{ marginBottom: '25px' }} />

                <Typography variant="subtitle1" style={{ fontWeight: 'bold', color: '#424242', marginBottom: '15px' }}>منابع مالی وام‌دهی صندوق</Typography>
                <Grid container spacing={3} mb={4} justifyContent="center">
                    <Grid item xs={12} md={6}>
                        <Card style={{ backgroundColor: '#f8f9fa', border: '1px solid #e0e0e0', boxShadow: 'none', height: '100%' }}>
                            <CardContent>
                                <Box display="flex" alignItems="center" mb={1} color="textSecondary">
                                    <AccountBalanceWalletIcon style={{ marginLeft: '8px', fontSize: '1.2rem' }} />
                                    <Typography variant="subtitle2">کل سرمایه پس‌انداز وام (اعضا + صندوق)</Typography>
                                </Box>
                                <Typography variant="h5" style={{ fontWeight: 'bold', color: '#1976d2', marginTop: '5px' }}>
                                    {data.total_loan_saving?.toLocaleString()} <span style={{fontSize:'0.6em', color:'gray', fontWeight: 'normal'}}>تومان</span>
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                        <Card style={{ background: 'linear-gradient(135deg, #1e88e5 0%, #1565c0 100%)', color: 'white', height: '100%' }}>
                            <CardContent>
                                <Box display="flex" alignItems="center" mb={1}>
                                    <SavingsIcon style={{ marginLeft: '8px', opacity: 0.9, fontSize: '1.2rem' }} />
                                    <Typography variant="subtitle2" style={{fontWeight: 'bold'}}>ظرفیت پایه وام‌دهی</Typography>
                                </Box>
                                <Typography variant="h4" style={{ fontWeight: 'bold', marginTop: '5px' }}>
                                    {data.base_capacity?.toLocaleString()} <span style={{fontSize:'0.5em', opacity: 0.8, fontWeight: 'normal'}}>تومان</span>
                                </Typography>
                                <Typography variant="caption" style={{ opacity: 0.8, display: 'block', marginTop: '5px' }}>(۵۰٪ کل سرمایه پس‌انداز وام)</Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>

                <Typography variant="subtitle1" style={{ fontWeight: 'bold', color: '#424242', marginBottom: '15px' }}>گردش مالی و موجودی فعلی</Typography>
                <Grid container spacing={3} mb={4}>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card elevation={2} style={{ height: '100%' }}><CardContent>
                            <Typography variant="caption" color="textSecondary">کل وام‌های پرداختی (معرفی شده)</Typography>
                            <Typography variant="h6" style={{fontWeight:'bold', color:'#616161', marginTop:'5px'}}>{data.total_paid_loans?.toLocaleString()}</Typography>
                        </CardContent></Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card elevation={2} style={{ height: '100%' }}><CardContent>
                            <Typography variant="caption" color="textSecondary">اقساط برگشتی</Typography>
                            <Typography variant="h6" style={{fontWeight:'bold', color:'#00897b', marginTop:'5px'}}>{data.total_virtual_returned?.toLocaleString()}</Typography>
                        </CardContent></Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card elevation={2} style={{ height: '100%' }}><CardContent>
                            <Typography variant="caption" color="textSecondary">سرمایه درگیر (تسویه‌نشده)</Typography>
                            <Typography variant="h6" style={{fontWeight:'bold', color:'#e65100', marginTop:'5px'}}>{data.active_debt?.toLocaleString()}</Typography>
                        </CardContent></Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card elevation={6} style={{ height: '100%', backgroundColor: data.free_capacity >= 0 ? '#e8f5e9' : '#ffebee', border: `2px solid ${data.free_capacity >= 0 ? '#4caf50' : '#ef5350'}` }}>
                            <CardContent>
                                <Typography variant="caption" style={{color: data.free_capacity >= 0 ? '#2e7d32' : '#c62828', fontWeight:'bold'}}>موجودی آزاد برای وام جدید</Typography>
                                <Typography variant="h5" style={{fontWeight:'900', color: data.free_capacity >= 0 ? '#1b5e20' : '#b71c1c', marginTop:'5px'}}>
                                    {data.free_capacity?.toLocaleString()} <span style={{fontSize:'0.6em', fontWeight:'normal'}}>تومان</span>
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>

                <Tabs value={tabIndex} onChange={(e, val) => setTabIndex(val)} indicatorColor="primary" textColor="primary" style={{marginBottom: '20px', borderBottom: '1px solid #e0e0e0'}}>
                    <Tab label="پرونده‌های وام و درخواست‌ها" style={{fontWeight: 'bold', fontSize: '1rem'}} />
                    <Tab label="گزارش پس‌انداز وام اعضا" style={{fontWeight: 'bold', fontSize: '1rem'}} />
                </Tabs>

                {tabIndex === 0 && (
                    <>
                        <Box display="flex" justifyContent="space-between" mb={2}>
                            <Typography variant="h6" style={{fontWeight:'bold'}}>لیست درخواست‌ها</Typography>
                            <Button variant="contained" color="success" startIcon={<AddCircleOutlineIcon />} onClick={() => setOpenManualDialog(true)}>ثبت وام دستی</Button>
                        </Box>
                        <TableContainer component={Paper} variant="outlined">
                            <Table size="small">
                                <TableHead style={{backgroundColor: '#eceff1'}}>
                                    <TableRow>
                                        <TableCell>متقاضی</TableCell>
                                        <TableCell>کد عضویت</TableCell>
                                        <TableCell>مبلغ</TableCell>
                                        <TableCell>مدت</TableCell>
                                        <TableCell>تاریخ ثبت / اعطا</TableCell>
                                        <TableCell align="center">وضعیت</TableCell>
                                        <TableCell align="center">عملیات</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {loans.map((loan) => (
                                        <TableRow key={loan.id} hover>
                                            <TableCell>{loan.user_name} {loan.is_manual && <Chip label="دستی" size="small" color="primary" variant="outlined" style={{height:'20px', fontSize:'0.7rem'}}/>}</TableCell>
                                            <TableCell>{loan.membership_code}</TableCell>
                                            <TableCell style={{fontWeight:'bold', color: '#1565c0'}} dir="ltr">{loan.amount.toLocaleString()}</TableCell>
                                            <TableCell>{loan.duration_months} ماه</TableCell>
                                            <TableCell dir="ltr" style={{fontSize: '0.85rem'}}>
                                                {loan.status === 'APPROVED' && loan.granted_date 
                                                    ? `اعطا: ${new Date(loan.granted_date).toLocaleDateString('fa-IR')}` 
                                                    : `ثبت: ${new Date(loan.created_at).toLocaleDateString('fa-IR')}`
                                                }
                                            </TableCell>
                                            <TableCell align="center">
                                                {loan.status === 'PENDING' && <Chip label="در انتظار" color="warning" size="small"/>}
                                                {loan.status === 'APPROVED' && <Chip label="تایید شده" color="success" size="small"/>}
                                                {loan.status === 'REJECTED' && <Chip label="رد شده" color="error" size="small"/>}
                                            </TableCell>
                                            <TableCell align="center">
                                                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap', minWidth: '160px' }}>
                                                    {loan.status === 'PENDING' ? (
                                                        <Button size="small" variant="contained" color="success" onClick={() => handleOpenApprove(loan)}>تایید / رد</Button>
                                                    ) : (
                                                        <>
                                                            <Button size="small" variant="outlined" color="primary" onClick={() => handleOpenApprove(loan, true)} startIcon={<EditIcon />}>ویرایش</Button>
                                                            {loan.status === 'APPROVED' && (
                                                                <Button size="small" variant="contained" color="info" startIcon={<ListAltIcon/>} onClick={() => openInstallments(loan)}>اقساط</Button>
                                                            )}
                                                        </>
                                                    )}
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </>
                )}

                {tabIndex === 1 && (
                    <TableContainer component={Paper} variant="outlined">
                        <Table size="small">
                            <TableHead style={{backgroundColor: '#e8eaf6'}}>
                                <TableRow><TableCell>عضو</TableCell><TableCell>کل پس‌انداز</TableCell><TableCell>تاریخ اولین واریز</TableCell><TableCell>روزهای گذشته</TableCell><TableCell align="center">وضعیت دوره ۹۰ روزه</TableCell><TableCell>امتیاز فعلی</TableCell></TableRow>
                            </TableHead>
                            <TableBody>
                                {savingsReport.map((user) => (
                                    <TableRow key={user.id} hover>
                                        <TableCell><strong>{user.full_name}</strong><br/><span style={{fontSize:'0.8rem', color:'gray'}}>{user.membership_code}</span></TableCell>
                                        <TableCell style={{fontWeight:'bold'}} dir="ltr">{user.total_saving.toLocaleString()}</TableCell>
                                        <TableCell dir="ltr">{new Date(user.first_deposit_date).toLocaleDateString('fa-IR')}</TableCell>
                                        <TableCell>{user.days_passed} روز</TableCell>
                                        <TableCell align="center">
                                            {user.days_remaining === 0 
                                                ? <Chip label="✅ تکمیل شده" color="success" size="small"/> 
                                                : <Chip label={`⏳ ${user.days_remaining} روز مانده`} color="warning" size="small"/>}
                                        </TableCell>
                                        <TableCell style={{color: '#d84315', fontWeight:'bold'}} dir="ltr">{user.current_points.toLocaleString()}</TableCell>
                                    </TableRow>
                                ))}
                                {savingsReport.length === 0 && <TableRow><TableCell colSpan={6} align="center">کسی پس‌انداز وام ندارد.</TableCell></TableRow>}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}
            </Paper>

            {/* مودال مدیریت اقساط */}
            <Dialog open={openInstallmentsDialog} onClose={() => setOpenInstallmentsDialog(false)} fullWidth maxWidth="md" dir="rtl">
                <DialogTitle style={{fontFamily:'Tahoma', fontWeight:'bold', backgroundColor: '#e3f2fd', color: '#1565c0'}}>
                    وضعیت اقساط وام: {selectedLoanForInst?.user_name}
                </DialogTitle>
                <DialogContent style={{ padding: '20px' }}>
                    <Grid container spacing={2} style={{marginBottom: '20px'}}>
                        <Grid item xs={4}>
                            <Paper style={{padding:'10px', textAlign:'center', backgroundColor:'#e8f5e9', border:'1px solid #c8e6c9'}}>
                                <Typography variant="caption" color="textSecondary">پرداخت شده</Typography>
                                <Typography variant="h6" style={{color:'#2e7d32', fontWeight:'bold'}}>{totalPaidInst.toLocaleString()}</Typography>
                            </Paper>
                        </Grid>
                        <Grid item xs={4}>
                            <Paper style={{padding:'10px', textAlign:'center', backgroundColor:'#fff3e0', border:'1px solid #ffe0b2'}}>
                                <Typography variant="caption" color="textSecondary">باقیمانده</Typography>
                                <Typography variant="h6" style={{color:'#ef6c00', fontWeight:'bold'}}>{totalRemInst.toLocaleString()}</Typography>
                            </Paper>
                        </Grid>
                        <Grid item xs={4}>
                            <Paper style={{padding:'10px', textAlign:'center', backgroundColor:'#ffebee', border:'1px solid #ffcdd2'}}>
                                <Typography variant="caption" color="textSecondary">اقساط معوق (تاخیر)</Typography>
                                <Typography variant="h6" style={{color:'#c62828', fontWeight:'bold'}}>{delayedInst} قسط</Typography>
                            </Paper>
                        </Grid>
                    </Grid>

                    <TableContainer component={Paper} variant="outlined">
                        <Table size="small">
                            <TableHead style={{backgroundColor: '#eceff1'}}>
                                <TableRow>
                                    <TableCell>قسط</TableCell>
                                    <TableCell>سررسید</TableCell>
                                    <TableCell>مبلغ (تومان)</TableCell>
                                    <TableCell align="center">وضعیت پرداخت</TableCell>
                                    <TableCell>تاریخ واریز</TableCell>
                                    <TableCell>عملیات</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {installments.map((inst) => {
                                    const isDelayed = !inst.is_paid && new Date(inst.due_date) < new Date();
                                    return (
                                        <TableRow key={inst.id} style={{ backgroundColor: isDelayed ? '#fff8f8' : 'inherit' }}>
                                            <TableCell><strong>{inst.number}</strong></TableCell>
                                            <TableCell dir="ltr" style={{color: isDelayed ? 'red' : 'inherit'}}>{new Date(inst.due_date).toLocaleDateString('fa-IR')}</TableCell>
                                            
                                            <TableCell>
                                                <InstallmentInput inst={inst} installments={installments} setInstallments={setInstallments} />
                                            </TableCell>
                                            
                                            <TableCell align="center">
                                                <Checkbox checked={inst.is_paid} onChange={() => toggleInstallmentStatus(inst)} color="success" />
                                            </TableCell>
                                            <TableCell dir="ltr">{inst.paid_date ? new Date(inst.paid_date).toLocaleDateString('fa-IR') : '---'}</TableCell>
                                            <TableCell>
                                                <Button size="small" variant="outlined" color="primary" onClick={() => saveInstallmentAmount(inst)}>ذخیره مبلغ</Button>
                                            </TableCell>
                                        </TableRow>
                                    )
                                })}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setOpenInstallmentsDialog(false)} color="primary" variant="contained">بستن پنجره</Button>
                </DialogActions>
            </Dialog>

            {/* مودال تایید و ویرایش وام (جراحی فیلد مدت زمان بازپرداخت) */}
            <Dialog open={openApproveDialog} onClose={() => setOpenApproveDialog(false)} fullWidth maxWidth="xs" dir="rtl" PaperProps={{ style: { overflow: 'visible' } }}>
                <DialogTitle style={{fontFamily:'Tahoma', fontWeight:'bold'}}>{selectedLoan?.status === 'PENDING' ? 'تعیین وضعیت پرونده' : 'ویرایش پرونده وام'}</DialogTitle>
                <DialogContent style={{ overflow: 'visible', minHeight: '350px' }}>
                    <FormControl fullWidth style={{marginBottom: '20px', marginTop:'10px'}}>
                        <InputLabel>وضعیت پرونده</InputLabel>
                        <Select value={approveData.status} label="وضعیت پرونده" onChange={(e) => setApproveData({...approveData, status: e.target.value})}>
                            <MenuItem value="PENDING">در انتظار بررسی</MenuItem>
                            <MenuItem value="APPROVED">تایید و معرفی به بانک</MenuItem>
                            <MenuItem value="REJECTED">رد درخواست</MenuItem>
                        </Select>
                    </FormControl>

                    {approveData.status === 'APPROVED' && (
                        <>
                            {/* فیلد ورودی آزاد جایگزین منوی کشویی شد */}
                            <TextField 
                                fullWidth 
                                label="مدت بازپرداخت (تعداد ماه‌ها)" 
                                type="number"
                                inputProps={{ min: 1 }}
                                value={approveData.duration_months} 
                                onChange={(e) => setApproveData({...approveData, duration_months: parseInt(e.target.value) || 1})} 
                                style={{ marginBottom: '15px' }}
                            />
                            
                            <DatePicker
                                calendar={persian}
                                locale={persian_fa}
                                value={new Date(approveData.granted_date)}
                                onChange={(date) => handleDateChange(date, setApproveData, approveData, 'granted_date')}
                                render={(value, openCalendar) => (
                                    <TextField fullWidth label="تاریخ معرفی به بانک (شمسی)" value={value} onClick={openCalendar} style={{ marginTop: '10px' }} />
                                )}
                            />
                        </>
                    )}
                </DialogContent>
                <DialogActions style={{padding:'15px', justifyContent:'flex-start'}}>
                    <Button variant="contained" color="primary" onClick={submitApprove}>ذخیره تغییرات</Button>
                    <Button variant="outlined" onClick={() => setOpenApproveDialog(false)}>انصراف</Button>
                </DialogActions>
            </Dialog>

            {/* مودال وام دستی (جراحی فیلد مدت زمان بازپرداخت) */}
            <Dialog open={openManualDialog} onClose={() => setOpenManualDialog(false)} fullWidth maxWidth="sm" dir="rtl" PaperProps={{ style: { overflow: 'visible' } }}>
                <DialogTitle style={{fontFamily:'Tahoma', fontWeight:'bold'}}>ثبت وام دستی (بدون کسر امتیاز)</DialogTitle>
                <DialogContent style={{ overflow: 'visible', minHeight: '350px' }}>
                    <Grid container spacing={2} style={{marginTop:'5px'}}>
                        <Grid item xs={12} sm={6}>
                            <TextField fullWidth label="کد عضویت متقاضی" value={manualData.target_membership_code} onChange={(e) => setManualData({...manualData, target_membership_code: e.target.value})} />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField fullWidth label="مبلغ وام (تومان)" value={manualData.amount ? Number(manualData.amount).toLocaleString() : ''} onChange={(e) => handleAmountChange(e, setManualData, manualData, 'amount')} />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            {/* فیلد ورودی آزاد جایگزین منوی کشویی شد */}
                            <TextField 
                                fullWidth 
                                label="مدت بازپرداخت (تعداد ماه‌ها)" 
                                type="number"
                                inputProps={{ min: 1 }}
                                value={manualData.duration_months} 
                                onChange={(e) => setManualData({...manualData, duration_months: parseInt(e.target.value) || 1})} 
                                style={{ marginTop: '10px' }}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <DatePicker
                                calendar={persian}
                                locale={persian_fa}
                                value={new Date(manualData.granted_date)}
                                onChange={(date) => handleDateChange(date, setManualData, manualData, 'granted_date')}
                                render={(value, openCalendar) => (
                                    <TextField fullWidth label="تاریخ اعطا (شمسی)" value={value} onClick={openCalendar} style={{ marginTop: '10px' }} />
                                )}
                            />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions style={{padding:'15px', justifyContent:'flex-start'}}>
                    <Button variant="contained" color="success" onClick={submitManualLoan}>ثبت وام</Button>
                    <Button variant="outlined" onClick={() => setOpenManualDialog(false)}>انصراف</Button>
                </DialogActions>
            </Dialog>

        </Container>
    );
};

export default LoanManagerDashboard;