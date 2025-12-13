import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Alert, Grid } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CurrencyInput from './CurrencyInput';

function LoanRequest() {
  const navigate = useNavigate();
  const [requests, setRequests] = useState([]);
  const [amount, setAmount] = useState('');
  const [desc, setDesc] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  const BASE_URL = 'https://sandogh-server.liara.run';

  useEffect(() => {
    fetchLoans();
  }, []);

  const fetchLoans = async () => {
    const token = localStorage.getItem('token');
    try {
      const res = await axios.get(`${BASE_URL}/api/accounting/loans/`, {
         headers: { Authorization: `Token ${token}` }
      });
      setRequests(res.data);
    } catch (err) { console.error(err); }
  };

  const handleSubmit = async () => {
    setLoading(true); setMsg(null);
    const token = localStorage.getItem('token');
    try {
      await axios.post(`${BASE_URL}/api/accounting/loans/`, { amount, description: desc }, {
        headers: { Authorization: `Token ${token}` }
      });
      setMsg({ type: 'success', text: 'درخواست وام ثبت شد.' });
      setAmount(''); setDesc(''); fetchLoans();
    } catch (err) {
      setMsg({ type: 'error', text: 'خطا در ثبت درخواست.' });
    } finally { setLoading(false); }
  };

  return (
    <Container maxWidth="md" style={{ marginTop: '30px', marginBottom: '50px' }}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px'}}>
            <Typography variant="h5" style={{fontWeight:'bold', color:'#ef6c00'}}>درخواست وام جدید</Typography>
            <Button variant="outlined" onClick={() => navigate('/dashboard')}>بازگشت به داشبورد</Button>
        </div>

        <Paper elevation={3} style={{ padding: '20px', marginBottom: '30px', background: '#fff3e0' }}>
            <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} md={5}>
                    <CurrencyInput label="مبلغ وام (تومان)" value={amount} onChange={(e) => setAmount(e.target.value)} fullWidth />
                </Grid>
                <Grid item xs={12} md={5}>
                    <TextField label="توضیحات (اختیاری)" value={desc} onChange={(e) => setDesc(e.target.value)} fullWidth />
                </Grid>
                <Grid item xs={12} md={2}>
                    <Button variant="contained" color="warning" fullWidth onClick={handleSubmit} disabled={loading} style={{height:'55px'}}>
                        {loading ? '...' : 'ثبت'}
                    </Button>
                </Grid>
            </Grid>
            {msg && <Alert severity={msg.type} style={{marginTop:'10px'}}>{msg.text}</Alert>}
        </Paper>

        <Typography variant="h6" gutterBottom>تاریخچه درخواست‌ها</Typography>
        <TableContainer component={Paper}>
            <Table>
                <TableHead style={{backgroundColor:'#eee'}}>
                    <TableRow><TableCell>مبلغ</TableCell><TableCell>تاریخ</TableCell><TableCell>وضعیت</TableCell><TableCell>امتیاز کسر شده</TableCell></TableRow>
                </TableHead>
                <TableBody>
                    {requests.length === 0 ? (
                        <TableRow><TableCell colSpan={4} align="center">موردی یافت نشد</TableCell></TableRow>
                    ) : (
                        requests.map((r) => (
                            <TableRow key={r.id}>
                                <TableCell>{Number(r.amount).toLocaleString()}</TableCell>
                                <TableCell dir="ltr">{new Date(r.created_at).toLocaleDateString('fa-IR')}</TableCell>
                                <TableCell>
                                    <Chip 
                                        label={r.status === 'APPROVED' ? 'تایید شده' : r.status === 'REJECTED' ? 'رد شده' : 'در انتظار'} 
                                        color={r.status === 'APPROVED' ? 'success' : r.status === 'REJECTED' ? 'error' : 'warning'} 
                                        size="small" 
                                    />
                                </TableCell>
                                <TableCell>{r.points_cost > 0 ? `${r.points_cost.toLocaleString()} امتیاز` : '-'}</TableCell>
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>
        </TableContainer>
    </Container>
  );
}

export default LoanRequest;