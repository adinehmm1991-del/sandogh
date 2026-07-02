import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
  Container, Paper, Typography, Grid, Card, CardContent, Button, Divider, Box,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, FormControl, InputLabel, Select, MenuItem,
  IconButton, Tooltip
} from '@mui/material';

// ایمپورت آیکون‌ها
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import CallMadeIcon from '@mui/icons-material/CallMade'; // برای تزریق پول
import CallReceivedIcon from '@mui/icons-material/CallReceived'; // برای خروج پول
import MonetizationOnIcon from '@mui/icons-material/MonetizationOn'; // برای سود
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import ShowChartIcon from '@mui/icons-material/ShowChart';

// تقویم شمسی
import DatePicker from "react-multi-date-picker";
import persian from "react-date-object/calendars/persian";
import persian_fa from "react-date-object/locales/persian_fa";
import LockIcon from '@mui/icons-material/Lock';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import CurrencyInput from './CurrencyInput';

const InvestmentDashboard = () => {
    const [dashboardData, setDashboardData] = useState(null);
    const [investments, setInvestments] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    // استیت‌های مودال پروژه جدید
    const [openProjectDialog, setOpenProjectDialog] = useState(false);
    const [projectData, setProjectData] = useState({
        title: '', investment_type: 'RISK_FREE', start_date: new Date().toISOString().split('T')[0], status: 'ACTIVE', description: ''
    });

    // استیت‌های مودال تراکنش (تزریق/برداشت/سود)
    const [openTransDialog, setOpenTransDialog] = useState(false);
    const [transData, setTransData] = useState({
        investment: '', transaction_type: '', amount: '', date: new Date().toISOString().split('T')[0], description: ''
    });
    const [selectedProjectName, setSelectedProjectName] = useState('');

    useEffect(() => {
        fetchDashboardData();
        fetchInvestments();
    }, []);

    const fetchDashboardData = async () => {
        try {
            const token = localStorage.getItem('token');
            const config = { headers: { Authorization: `Token ${token}` } };
            const response = await axios.get(`/api/accounting/manager/investment-dashboard/?_t=${Date.now()}`, config);
            setDashboardData(response.data);
            setLoading(false);
        } catch (err) { setLoading(false); }
    };

    const fetchInvestments = async () => {
        try {
            const token = localStorage.getItem('token');
            const config = { headers: { Authorization: `Token ${token}` } };
            const response = await axios.get(`/api/accounting/manager/investments/?_t=${Date.now()}`, config);
            setInvestments(response.data);
        } catch (err) {}
    };

    // --- توابع ثبت اطلاعات ---
    const submitProject = async () => {
        if(!projectData.title) { alert('عنوان پروژه الزامی است!'); return; }
        try {
            const token = localStorage.getItem('token');
            const config = { headers: { Authorization: `Token ${token}` } };
            await axios.post(`/api/accounting/manager/investments/`, projectData, config);
            alert('✅ پروژه جدید با موفقیت ثبت شد.');
            setOpenProjectDialog(false);
            setProjectData({ ...projectData, title: '', description: ''});
            fetchInvestments();
        } catch (err) { alert('❌ خطا در ثبت پروژه!'); }
    };

    const closeProject = async (project) => {
        if (project.active_balance > 0) {
            alert('❌ خطا: این پروژه هنوز سرمایه درگیر دارد. ابتدا باید تمام پول را آزادسازی کنید.');
            return;
        }
        if (window.confirm(`آیا از بستن کامل پرونده "${project.title}" مطمئن هستید؟ پس از بسته شدن امکان ثبت تراکنش برای آن وجود نخواهد داشت.`)) {
            try {
                const token = localStorage.getItem('token');
                await axios.patch(`/api/accounting/manager/investments/${project.id}/`, { status: 'CLOSED' }, { headers: { Authorization: `Token ${token}` } });
                alert('✅ پرونده با موفقیت بسته شد.');
                fetchInvestments();
            } catch (err) { alert('❌ خطا در بستن پرونده!'); }
        }
    };

    const settleProfits = async () => {
        if (window.confirm('⚠️ آیا مطمئن هستید؟\nبا این کار، سودهای فعلی در داشبورد "صفر" می‌شوند تا سیستم برای سال جدید آماده شود. (معمولاً بعد از تقسیم سود در پایان سال این گزینه را می‌زنند)')) {
            try {
                const token = localStorage.getItem('token');
                await axios.post(`/api/accounting/manager/investment-profits/settle/`, {}, { headers: { Authorization: `Token ${token}` } });
                alert('✅ سودها با موفقیت تسویه و صفر شدند.');
                fetchDashboardData();
                fetchInvestments();
            } catch (err) { alert('❌ خطا در صفر کردن سودها!'); }
        }
    };

    const submitTransaction = async () => {
        if(!transData.amount || transData.amount === '0') { alert('مبلغ الزامی است!'); return; }
        try {
            const token = localStorage.getItem('token');
            const config = { headers: { Authorization: `Token ${token}` } };
            
            const payload = { ...transData, amount: transData.amount.replace(/,/g, '') };
            await axios.post(`/api/accounting/manager/investment-transactions/`, payload, config);
            
            alert('✅ تراکنش با موفقیت ثبت شد.');
            setOpenTransDialog(false);
            setTransData({ ...transData, amount: '', description: ''});
            fetchDashboardData();
            fetchInvestments();
        } catch (err) { 
            alert(err.response?.data?.error || '❌ خطا در ثبت تراکنش!'); 
        }
    };

    // --- توابع کمکی ---
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

    const openTransactionModal = (project, type) => {
        setSelectedProjectName(project.title);
        setTransData({
            ...transData, 
            investment: project.id, 
            transaction_type: type,
            amount: '', description: ''
        });
        setOpenTransDialog(true);
    };

    if (loading) return <div style={{textAlign: 'center', marginTop: '50px', direction: 'rtl', fontFamily: 'Tahoma'}}>در حال بارگذاری داشبورد...</div>;
    if (!dashboardData) return null;

    return (
        <Container maxWidth="xl" style={{ marginTop: '40px', marginBottom: '50px', direction: 'rtl', fontFamily: 'Tahoma' }}>
            <Paper elevation={4} style={{ padding: '30px', borderRadius: '15px' }}>
                
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                    <Typography variant="h5" style={{ fontWeight: 'bold', color: '#4527a0' }}>
                        <ShowChartIcon style={{ verticalAlign: 'middle', marginLeft: '10px' }} />
                        داشبورد کلان مدیریت سرمایه‌گذاری
                    </Typography>
                    <Button variant="outlined" startIcon={<ArrowBackIcon style={{marginLeft:'8px'}} />} onClick={() => navigate('/dashboard')}>بازگشت</Button>
                </Box>
                <Divider style={{ marginBottom: '25px' }} />

                {/* --- کارت‌های آماری (قانون دو جیب) --- */}
                <Grid container spacing={3} mb={5}>
                    {/* ردیف اول: پول مردم و درگیری‌ها */}
                    <Grid item xs={12} md={3}>
                        <Card style={{ borderLeft: '5px solid #1976d2', backgroundColor: '#f5f5f5' }}>
                            <CardContent>
                                <Typography variant="caption" color="textSecondary">کل منابع مالی صندوق (اصل پول)</Typography>
                                <Typography variant="h5" style={{ fontWeight: 'bold', color: '#1565c0', marginTop:'5px' }}>
                                    {dashboardData.total_fund_capital?.toLocaleString()} <span style={{fontSize:'0.6em', color:'gray', fontWeight:'normal'}}>تومان</span>
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Card style={{ borderLeft: '5px solid #f57c00', backgroundColor: '#fff3e0' }}>
                            <CardContent>
                                <Typography variant="caption" color="textSecondary">سرمایه درگیر در وام اعضا</Typography>
                                <Typography variant="h5" style={{ fontWeight: 'bold', color: '#e65100', marginTop:'5px' }}>
                                    {dashboardData.active_loans_debt?.toLocaleString()} <span style={{fontSize:'0.6em', color:'gray', fontWeight:'normal'}}>تومان</span>
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Card style={{ borderLeft: '5px solid #7b1fa2', backgroundColor: '#f3e5f5' }}>
                            <CardContent>
                                <Typography variant="caption" color="textSecondary">سرمایه درگیر در پروژه‌های بیرون</Typography>
                                <Typography variant="h5" style={{ fontWeight: 'bold', color: '#6a1b9a', marginTop:'5px' }}>
                                    {dashboardData.active_investments_debt?.toLocaleString()} <span style={{fontSize:'0.6em', color:'gray', fontWeight:'normal'}}>تومان</span>
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Card style={{ backgroundColor: dashboardData.free_main_capital >= 0 ? '#e8f5e9' : '#ffebee', border: `2px solid ${dashboardData.free_main_capital >= 0 ? '#4caf50' : '#ef5350'}` }}>
                            <CardContent>
                                <Typography variant="caption" style={{color: dashboardData.free_main_capital >= 0 ? '#2e7d32' : '#c62828', fontWeight:'bold'}}>نقدینگی آزادِ سرمایه (جیب اول)</Typography>
                                <Typography variant="h5" style={{ fontWeight: '900', color: dashboardData.free_main_capital >= 0 ? '#1b5e20' : '#b71c1c', marginTop:'5px' }}>
                                    {dashboardData.free_main_capital?.toLocaleString()} <span style={{fontSize:'0.6em', fontWeight:'normal'}}>تومان</span>
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    
                    {/* ردیف دوم: جیب دوم (سودها) */}
                    <Grid item xs={12} md={12}>
                        <Card style={{ background: 'linear-gradient(135deg, #00b4db 0%, #0083b0 100%)', color: 'white' }}>
                            <CardContent style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Box>
                                    <Box display="flex" alignItems="center">
                                        <MonetizationOnIcon style={{ marginLeft: '10px', fontSize: '2rem', opacity: 0.9 }} />
                                        <Typography variant="h6" style={{fontWeight: 'bold'}}>کل سود محقق شده در بانک (جیب دوم)</Typography>
                                    </Box>
                                    <Typography variant="body2" style={{ opacity: 0.8, marginTop: '5px' }}>
                                        این مبلغ از پروژه‌ها نقد شده است اما هنوز بین اعضا تقسیم نشده و به منابع اصلی اضافه نگردیده است.
                                    </Typography>
                                    {/* دکمه جدید برای صفر کردن سود */}
                                    <Button 
                                        variant="outlined" size="small" 
                                        startIcon={<DeleteSweepIcon style={{marginLeft: '5px'}}/>}
                                        onClick={settleProfits}
                                        style={{color: 'white', borderColor: 'rgba(255,255,255,0.5)', marginTop: '8px'}}
                                    >
                                        صفر کردن سودها (شروع دوره جدید)
                                    </Button>
                                </Box>
                                <Typography variant="h4" style={{ fontWeight: 'bold' }}>
                                    {dashboardData.total_realized_profit?.toLocaleString()} <span style={{fontSize:'0.5em', opacity: 0.8, fontWeight:'normal'}}>تومان</span>
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>

                {/* --- جدول پروژه‌های سرمایه‌گذاری --- */}
                <Box display="flex" justifyContent="space-between" mb={2} mt={4}>
                    <Typography variant="h6" style={{fontWeight:'bold'}}>لیست پرونده‌های سرمایه‌گذاری</Typography>
                    <Button variant="contained" color="primary" startIcon={<AddCircleOutlineIcon />} onClick={() => setOpenProjectDialog(true)}>ثبت پروژه جدید</Button>
                </Box>
                
                <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                        <TableHead style={{backgroundColor: '#eceff1'}}>
                            <TableRow>
                                <TableCell>عنوان پروژه</TableCell>
                                <TableCell>نوع</TableCell>
                                <TableCell>تاریخ شروع</TableCell>
                                <TableCell>وضعیت</TableCell>
                                <TableCell>سرمایه درگیر (موجود)</TableCell>
                                <TableCell>سود تولید شده</TableCell>
                                <TableCell align="center">عملیات مالی</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {investments.map((inv) => (
                                <TableRow key={inv.id} hover>
                                    <TableCell style={{fontWeight:'bold', color:'#37474f'}}>{inv.title}</TableCell>
                                    <TableCell>
                                        <Chip label={inv.investment_type_display} size="small" variant="outlined" color={inv.investment_type === 'RISKY' ? 'warning' : 'info'}/>
                                    </TableCell>
                                    <TableCell dir="ltr" style={{fontSize: '0.85rem'}}>{new Date(inv.start_date).toLocaleDateString('fa-IR')}</TableCell>
                                    <TableCell>
                                        {inv.status === 'ACTIVE' ? <Chip label="فعال" color="success" size="small"/> : <Chip label="بسته شده" color="default" size="small"/>}
                                    </TableCell>
                                    <TableCell style={{fontWeight:'bold', color: '#1565c0'}} dir="ltr">{inv.active_balance.toLocaleString()}</TableCell>
                                    <TableCell style={{fontWeight:'bold', color: '#2e7d32'}} dir="ltr">{inv.total_profit.toLocaleString()}</TableCell>
                                    <TableCell align="center">
                                        <Tooltip title="تزریق پول به پروژه">
                                            <IconButton color="primary" onClick={() => openTransactionModal(inv, 'DEPOSIT')} disabled={inv.status === 'CLOSED'}><CallMadeIcon /></IconButton>
                                        </Tooltip>
                                        <Tooltip title="آزادسازی/برگشت پول">
                                            <IconButton color="error" onClick={() => openTransactionModal(inv, 'WITHDRAWAL')} disabled={inv.active_balance === 0}><CallReceivedIcon /></IconButton>
                                        </Tooltip>
                                        <Tooltip title="ثبت سود نقد شده">
                                            <IconButton color="success" onClick={() => openTransactionModal(inv, 'PROFIT')} disabled={inv.status === 'CLOSED'}><MonetizationOnIcon /></IconButton>
                                        </Tooltip>
                                        <Tooltip title={inv.status === 'CLOSED' ? "پرونده بسته شده است" : "بستن کامل پرونده"}>
                                            <IconButton color="default" onClick={() => closeProject(inv)} disabled={inv.status === 'CLOSED' || inv.active_balance > 0}>
                                                <LockIcon style={{color: inv.status === 'CLOSED' ? 'gray' : '#607d8b'}}/>
                                            </IconButton>
                                        </Tooltip>
                                    </TableCell>
                                </TableRow>
                            ))}
                            {investments.length === 0 && <TableRow><TableCell colSpan={7} align="center">هیچ پروژه‌ای ثبت نشده است.</TableCell></TableRow>}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>

            {/* --- مودال ثبت پروژه جدید --- */}
            <Dialog open={openProjectDialog} onClose={() => setOpenProjectDialog(false)} fullWidth maxWidth="sm" dir="rtl" PaperProps={{ style: { overflow: 'visible' } }}>
                <DialogTitle style={{fontFamily:'Tahoma', fontWeight:'bold'}}>ثبت بستر سرمایه‌گذاری جدید</DialogTitle>
                <DialogContent style={{ overflow: 'visible', minHeight: '350px' }}>
                    <Grid container spacing={2} style={{marginTop:'5px'}}>
                        <Grid item xs={12} sm={6}>
                            <TextField fullWidth label="عنوان (مثلاً: بورس، طلا، بانک رسالت)" value={projectData.title} onChange={(e) => setProjectData({...projectData, title: e.target.value})} />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth>
                                <InputLabel>نوع سرمایه‌گذاری</InputLabel>
                                <Select value={projectData.investment_type} label="نوع سرمایه‌گذاری" onChange={(e) => setProjectData({...projectData, investment_type: e.target.value})}>
                                    <MenuItem value="RISK_FREE">بدون ریسک (سپرده/اوراق)</MenuItem>
                                    <MenuItem value="RISKY">ریسک‌پذیر (بورس/طلا/املاک)</MenuItem>
                                    <MenuItem value="SHORT_TERM">کوتاه‌مدت</MenuItem>
                                    <MenuItem value="LONG_TERM">بلندمدت</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <DatePicker
                                calendar={persian}
                                locale={persian_fa}
                                value={new Date(projectData.start_date)}
                                onChange={(date) => handleDateChange(date, setProjectData, projectData, 'start_date')}
                                render={(value, openCalendar) => (
                                    <TextField fullWidth label="تاریخ شروع (شمسی)" value={value} onClick={openCalendar} style={{ marginTop: '10px' }} />
                                )}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth style={{ marginTop: '10px' }}>
                                <InputLabel>وضعیت</InputLabel>
                                <Select value={projectData.status} label="وضعیت" onChange={(e) => setProjectData({...projectData, status: e.target.value})}>
                                    <MenuItem value="ACTIVE">فعال (در جریان)</MenuItem>
                                    <MenuItem value="CLOSED">بسته شده</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12}>
                            <TextField fullWidth label="توضیحات تکمیلی (اختیاری)" multiline rows={2} value={projectData.description} onChange={(e) => setProjectData({...projectData, description: e.target.value})} />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions style={{padding:'15px', justifyContent:'flex-start'}}>
                    <Button variant="contained" color="primary" onClick={submitProject}>ذخیره پروژه</Button>
                    <Button variant="outlined" onClick={() => setOpenProjectDialog(false)}>انصراف</Button>
                </DialogActions>
            </Dialog>

            {/* --- مودال تراکنش (تزریق/برداشت/سود) --- */}
            <Dialog open={openTransDialog} onClose={() => setOpenTransDialog(false)} fullWidth maxWidth="xs" dir="rtl" PaperProps={{ style: { overflow: 'visible' } }}>
                <DialogTitle style={{fontFamily:'Tahoma', fontWeight:'bold'}}>
                    {transData.transaction_type === 'DEPOSIT' && '↗️ تزریق پول به پروژه'}
                    {transData.transaction_type === 'WITHDRAWAL' && '↙️ آزادسازی پول از پروژه'}
                    {transData.transaction_type === 'PROFIT' && '💰 ثبت سود نقد شده'}
                </DialogTitle>
                <DialogContent style={{ overflow: 'visible', minHeight: '300px' }}>
                    <Typography variant="body2" color="textSecondary" style={{marginBottom: '15px'}}>پروژه انتخابی: <strong>{selectedProjectName}</strong></Typography>
                    
                    {/* جراحی: استفاده از ابزار ضدپرش برای موبایل */}
                    <div style={{ marginBottom: '15px' }}>
                        <CurrencyInput 
                            fullWidth 
                            label="مبلغ (تومان)" 
                            name="amount" 
                            value={transData.amount} 
                            onChange={(e) => handleAmountChange(e, setTransData, transData, 'amount')} 
                        />
                    </div>                    
                    <DatePicker
                        calendar={persian}
                        locale={persian_fa}
                        value={new Date(transData.date)}
                        onChange={(date) => handleDateChange(date, setTransData, transData, 'date')}
                        render={(value, openCalendar) => (
                            <TextField fullWidth label="تاریخ وقوع (شمسی)" value={value} onClick={openCalendar} style={{ marginBottom: '15px' }} />
                        )}
                    />

                    <TextField fullWidth label="توضیحات (اختیاری)" value={transData.description} onChange={(e) => setTransData({...transData, description: e.target.value})} />
                </DialogContent>
                <DialogActions style={{padding:'15px', justifyContent:'flex-start'}}>
                    <Button variant="contained" color={transData.transaction_type === 'WITHDRAWAL' ? 'error' : (transData.transaction_type === 'PROFIT' ? 'success' : 'primary')} onClick={submitTransaction}>ثبت تراکنش</Button>
                    <Button variant="outlined" onClick={() => setOpenTransDialog(false)}>انصراف</Button>
                </DialogActions>
            </Dialog>

        </Container>
    );
};

export default InvestmentDashboard;