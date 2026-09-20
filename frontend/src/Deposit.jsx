import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, MenuItem, Box, Alert, Checkbox, FormControlLabel, Select, InputLabel, FormControl, Divider } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DatePicker from "react-multi-date-picker";
import persian from "react-date-object/calendars/persian";
import persian_fa from "react-date-object/locales/persian_fa";
import CurrencyInput from './CurrencyInput';

function Deposit() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date());

  const [userName, setUserName] = useState(''); 
  
  // --- جراحی: استخراج هوشمند آیدی زیرمجموعه از آدرس مرورگر ---
  const queryParams = new URLSearchParams(window.location.search);
  const targetUserId = queryParams.get('user_id');
  
  const [waqfIntent, setWaqfIntent] = useState('WAQF_GEN');
  const [waqfAccepted, setWaqfAccepted] = useState(false);
  
  const [formData, setFormData] = useState({
    amount: '',
    transaction_type: 'SHORT_TERM',
    description: '',
    receipt_image: null
  });

  const transactionTypes = [
    { value: 'SHORT_TERM', label: 'پس‌انداز کوتاه‌مدت (روزشمار)' },
    { value: 'LONG_TERM', label: 'پس‌انداز بلندمدت (۳ ماهه)' },
    { value: 'LOAN_SAVING', label: 'پس‌انداز وام' },
    { value: 'QARD', label: 'قرض‌الحسنه' },
    { value: 'FEE', label: 'حق عضویت' },
    { value: 'SADAQAH', label: 'صدقه' },
    { value: 'SACRIFICE', label: 'قربانی' },
    { value: 'BOOK', label: 'امور کتاب ' },
    { value: 'KHOMS_IMAM', label: 'سهم امام' },
    { value: 'KHOMS_SADAT', label: 'سهم سادات' },
    { value: 'WAQF_FORM', label: '📜 وقف ماندگار ' }, 
  ];

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const checkProfile = async () => {
        try {
            const res = await axios.get('/api/users/profile/', { headers: { Authorization: `Token ${token}` } });
            
            if (!res.data.national_code || !res.data.card_number || !res.data.shaba_number) {
                alert("⛔ کاربر گرامی، برای انجام امور مالی ابتدا باید پروفایل خود (کد ملی، شماره کارت و شماره شبا) را تکمیل کنید.");
                navigate('/profile');
            } else {
                setUserName(res.data.full_name);
            }
        } catch (e) { console.error(e); }
    };

    checkProfile();
  }, [navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    let newData = { ...formData, [name]: value };

    if (name === 'transaction_type' && value === 'FEE') {
        newData.amount = '1000000';
        newData.description = 'پرداخت حق عضویت ثابت';
    } else if (name === 'transaction_type' && value !== 'FEE') {
        newData.amount = '';
        newData.description = '';
    }
    setFormData(newData);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData({ ...formData, receipt_image: file });
      setPreview(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);
    
    let actualTransactionType = formData.transaction_type;
    if (actualTransactionType === 'WAQF_FORM') {
        if (!waqfAccepted) {
            setMessage({ type: 'error', text: '⛔ برای ثبت وقف، باید شرایط و متن وقف‌نامه را با زدن تیک پایین صفحه امضا کنید.' });
            setLoading(false);
            return;
        }
        if (!formData.amount) {
            setMessage({ type: 'error', text: '⛔ مبلغ وقف را مشخص نکرده‌اید.' });
            setLoading(false);
            return;
        }
        actualTransactionType = waqfIntent; 
    }

    const token = localStorage.getItem('token');
    let finalDate = selectedDate ? (selectedDate.toDate ? selectedDate.toDate().toISOString().split('T')[0] : new Date().toISOString().split('T')[0]) : "";

    const dataToSend = new FormData();
    dataToSend.append('amount', formData.amount);
    dataToSend.append('transaction_type', actualTransactionType);
    dataToSend.append('date', finalDate);
    dataToSend.append('description', formData.description);
    
    // --- جراحی: الحاق نامرئیِ آیدی زیرمجموعه در صورت وجود ---
    if (targetUserId) {
        dataToSend.append('target_user_id', targetUserId);
    }
    
    if (formData.receipt_image) dataToSend.append('receipt_image', formData.receipt_image);

    try {
      await axios.post('/api/accounting/transactions/', dataToSend, { headers: { 'Authorization': `Token ${token}` } });
      setMessage({ type: 'success', text: '✅ واریزی با موفقیت ثبت شد. اجرکم عند الله!' });
      
      // هدایت به داشبوردِ همان شخص (اصلی یا زیرمجموعه)
      setTimeout(() => navigate(targetUserId ? `/dashboard?user_id=${targetUserId}` : '/dashboard', { replace: true }), 2000);
    } catch (error) {
      const errorMsg = error.response?.data?.receipt_image ? "لطفا تصویر فیش را انتخاب کنید." : "خطا در ثبت اطلاعات.";
      setMessage({ type: 'error', text: errorMsg });
    } finally {
        setLoading(false);
    }
  };

  const isWaqfMode = formData.transaction_type === 'WAQF_FORM';
  const culturalTypes = ['SADAQAH', 'SACRIFICE', 'BOOK', 'KHOMS_IMAM', 'KHOMS_SADAT'];

  return (
    <Container maxWidth="sm" style={{ marginTop: '50px', marginBottom: '50px', fontFamily: 'Tahoma' }}>
      <Paper elevation={isWaqfMode ? 6 : 3} style={{ padding: '30px', border: isWaqfMode ? '1px solid #c5a059' : 'none' }}>
        
        {/* --- جراحی: تغییر تیتر بالای صفحه برای نشان دادن حساب مقصد --- */}
        <Typography variant="h5" gutterBottom align={isWaqfMode ? "center" : "right"} style={{ color: isWaqfMode ? '#5d4037' : 'inherit', fontWeight: 'bold' }}>
            {isWaqfMode ? 'سند وقف ماندگار' : `ثبت واریزی جدید ${targetUserId ? '(زیرمجموعه)' : ''}`}
        </Typography>
        
        <Box component="form" noValidate autoComplete="off">
          
          <TextField select label="نوع واریز" name="transaction_type" value={formData.transaction_type} onChange={handleChange} fullWidth margin="normal" style={{backgroundColor: isWaqfMode ? '#fff8e1' : 'transparent'}}>
            {transactionTypes.map((option) => (
              <MenuItem key={option.value} value={option.value} style={{fontWeight: option.value === 'WAQF_FORM' ? 'bold' : 'normal'}}>{option.label}</MenuItem>
            ))}
          </TextField>

          {/* ========================================================= */}
          {/* ================= فرم اختصاصی و زیبای وقف‌نامه ================= */}
          {/* ========================================================= */}
          {isWaqfMode ? (
            <Paper elevation={0} style={{ padding: '25px 20px', backgroundColor: '#fdfbf7', border: '2px solid #e0d4b5', borderRadius: '10px', marginTop: '15px', marginBottom: '20px' }}>
                <Typography variant="h6" align="center" style={{fontFamily: 'IranNastaliq, Tahoma', color: '#5d4037', marginBottom: '10px'}}>بسم الله الرحمن الرحیم</Typography>
                <Typography variant="subtitle1" align="center" style={{fontWeight: 'bold', marginBottom: '25px', color: '#8d6e63'}}>عقد وقف نقدی برای صندوق «ثنای حق»</Typography>
                
                <Typography variant="body1" style={{lineHeight: 2.2, textAlign: 'justify', fontSize: '0.95rem'}}>
                    اینجانب <strong>{userName}</strong> با قصد قربت الی الله و با رضایت کامل، مبلغ:
                </Typography>
                
                <CurrencyInput label="مبلغ وقف" name="amount" value={formData.amount} onChange={handleChange} fullWidth margin="normal" />

                <Typography variant="body1" style={{lineHeight: 2.2, textAlign: 'justify', fontSize: '0.95rem', marginTop: '10px'}}>
                    از اموال خود را وقف نمودم. بدین وسیله این مبلغ را به‌عنوان وقف شرعی و دائمی در اختیار صندوق ثنای حق قرار دادم، به این نحو که اصل سرمایه به صورت وقف، حبس شده و غیرقابل تملک، فروش یا مصرف بوده و منافع و عوائد حاصل از آن در امور خیریه و فرهنگی مطابق نیت واقف مصرف گردد. <br/> 
                    <strong>نیت اینجانب از وقف مذکور عبارت است از:</strong>
                </Typography>

                <FormControl fullWidth margin="normal" style={{marginTop: '20px', marginBottom: '20px'}}>
                    <InputLabel>نیت وقف را انتخاب کنید</InputLabel>
                    <Select value={waqfIntent} label="نیت وقف را انتخاب کنید" onChange={(e) => setWaqfIntent(e.target.value)} style={{backgroundColor: '#fff'}}>
                        <MenuItem value="WAQF_GEN">وقف عام (مصرف در امور دینی و تربیتی به تشخیص صندوق)</MenuItem>
                        <MenuItem value="WAQF_BOOK">وقف خاص (حمایت از نشر کتاب)</MenuItem>
                        <MenuItem value="WAQF_MEDIA">وقف خاص (تولید محتوای معرفتی و رسانه‌ای)</MenuItem>
                        <MenuItem value="WAQF_INFRA">وقف خاص (زیرساخت و سخت‌افزار جهت ترویج معارف)</MenuItem>
                    </Select>
                </FormControl>

                <div style={{backgroundColor: '#efebe3', padding: '15px', borderRadius: '8px', marginBottom: '20px'}}>
                    <Typography variant="subtitle2" style={{fontWeight: 'bold', marginBottom: '10px', color: '#5d4037'}}>شرایط شرعی وقف:</Typography>
                    <ul style={{fontSize: '0.85rem', lineHeight: 2, margin: 0, paddingRight: '20px', color: '#4e342e'}}>
                        <li>اصل سرمایه وقفی باید همواره حفظ شود و فقط منافع آن مصرف گردد.</li>
                        <li>مدیریت و نگهداری سرمایه وقفی بر عهده صندوق به عنوان امین وقف خواهد بود.</li>
                        <li>مصرف منافع وقف باید دقیقاً مطابق نیت انتخاب‌شده توسط واقف انجام گیرد.</li>
                        <li>در صورت تعذر اجرای دقیق نیت واقف، منافع در نزدیک‌ترین مورد به نیت مصرف شود.</li>
                        <li>اینجانب با علم به احکام شرعی، این مال را وقف مؤبد و غیرقابل رجوع قرار دادم.</li>
                    </ul>
                </div>

                <Divider style={{marginBottom: '15px'}} />
                
                <FormControlLabel
                    control={<Checkbox checked={waqfAccepted} onChange={(e) => setWaqfAccepted(e.target.checked)} color="success" />}
                    label={<Typography variant="body2" style={{fontWeight: 'bold', color: '#2e7d32'}}> اینجانب با علم به احکام شرعی، شرایط بالا را خوانده و با قصد انشاء، آن را امضا می‌کنم.</Typography>}
                    style={{alignItems: 'flex-start', marginTop: '10px'}}
                />
            </Paper>

          ) : (
          /* ================= فرم واریز عادی ================= */
          <>
            {/* فیلد انتخاب کاربر به طور کامل حذف شد */}

            {formData.transaction_type === 'SHORT_TERM' && (<Alert severity="info" style={{ marginTop: '5px', marginBottom: '10px' }}><strong>کوتاه‌مدت:</strong> برداشت آزاد. سود علی‌الحساب: <strong>۲٪ ماهیانه</strong></Alert>)}
            {formData.transaction_type === 'LONG_TERM' && (<Alert severity="warning" style={{ marginTop: '5px', marginBottom: '10px' }}><strong>بلندمدت:</strong> قفل ۳ ماهه. سود علی‌الحساب: <strong>۳٪ ماهیانه</strong></Alert>)}
            {culturalTypes.includes(formData.transaction_type) && (<Alert severity="success" style={{ marginTop: '5px', marginBottom: '10px' }}>این مبلغ مستقیماً به حساب مورد نظر در صندوق منتقل می‌شود.</Alert>)}

            <CurrencyInput label="مبلغ (تومان)" name="amount" value={formData.amount} onChange={handleChange} fullWidth margin="normal" disabled={formData.transaction_type === 'FEE'} />
          </>
          )}

          {/* فیلدهای مشترک (تاریخ، توضیحات، آپلود فیش) */}
          <div style={{ marginTop: '16px', marginBottom: '8px' }}>
            <Typography variant="caption" color="textSecondary" style={{display: 'block', marginBottom: '5px'}}>تاریخ واریز فیش (شمسی)</Typography>
            <DatePicker value={selectedDate} onChange={setSelectedDate} calendar={persian} locale={persian_fa} calendarPosition="bottom-right" style={{ width: "100%", height: "56px", borderRadius: "4px", border: "1px solid #c4c4c4", padding: "0 14px", fontFamily: "Tahoma" }} />
          </div>

          <TextField label="توضیحات فیش (اختیاری)" name="description" value={formData.description} onChange={handleChange} fullWidth margin="normal" multiline rows={2} />

          <div style={{ margin: '20px 0', textAlign: 'center' }}>
            <input accept="image/*" style={{ display: 'none' }} id="raised-button-file" type="file" onChange={handleFileChange} />
            <label htmlFor="raised-button-file">
              <Button variant="outlined" component="span" startIcon={<CloudUploadIcon />}>آپلود تصویر فیش بانکی</Button>
            </label>
            {preview && <div style={{ marginTop: '10px' }}><img src={preview} alt="fich" style={{ maxWidth: '100%', maxHeight: '200px', borderRadius: '8px' }} /></div>}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <Button variant="contained" color={isWaqfMode ? "success" : "primary"} fullWidth onClick={handleSubmit} disabled={loading} style={{ padding: '10px', fontWeight: 'bold' }}>
                {loading ? 'درحال ارسال...' : (isWaqfMode ? 'امضای وقف‌نامه و ثبت نهایی' : 'ثبت نهایی')}
            </Button>
            <Button variant="outlined" color="inherit" fullWidth onClick={() => navigate(targetUserId ? `/dashboard?user_id=${targetUserId}` : '/dashboard')}>انصراف</Button>
          </div>
        </Box>
        {message && <Alert severity={message.type} style={{ marginTop: '20px' }}>{message.text}</Alert>}
      </Paper>
    </Container>
  );
}

export default Deposit;