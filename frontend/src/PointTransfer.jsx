import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Alert, Divider } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';

function PointTransfer() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [targetCode, setTargetCode] = useState('');
  const [points, setPoints] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  const BASE_URL = 'https://sandogh-server.liara.run';

  useEffect(() => { fetchLogs(); }, []);

  const fetchLogs = async () => {
    const token = localStorage.getItem('token');
    try {
        const res = await axios.get(`${BASE_URL}/api/accounting/points/logs/`, { headers: { Authorization: `Token ${token}` } });
        setLogs(res.data);
    } catch (err) { console.error(err); }
  };

  const handleTransfer = async () => {
    setLoading(true); setMsg(null);
    const token = localStorage.getItem('token');
    try {
      await axios.post(`${BASE_URL}/api/accounting/points/transfer/`, 
        { target_membership_code: targetCode, points: points }, 
        { headers: { Authorization: `Token ${token}` } }
      );
      setMsg({ type: 'success', text: '✅ انتقال امتیاز با موفقیت انجام شد.' });
      setTargetCode(''); setPoints(''); fetchLogs();
    } catch (err) {
      setMsg({ type: 'error', text: err.response?.data?.error || 'خطا در انتقال.' });
    } finally { setLoading(false); }
  };

  return (
    <Container maxWidth="md" style={{ marginTop: '30px' }}>
      <Paper elevation={3} style={{ padding: '25px', borderRadius: '15px' }}>
        <div style={{textAlign:'center', marginBottom:'20px'}}>
            <SwapHorizIcon style={{fontSize: 50, color: '#673ab7'}} />
            <Typography variant="h5" style={{fontWeight:'bold', color: '#673ab7'}}>انتقال امتیاز وام</Typography>
            <Typography variant="caption" color="textSecondary">امتیاز خود را به سایر اعضا هدیه دهید</Typography>
        </div>
        
        <div style={{ maxWidth: '400px', margin: '0 auto' }}>
            <TextField label="کد عضویت گیرنده" value={targetCode} onChange={(e) => setTargetCode(e.target.value)} fullWidth margin="normal" />
            <TextField label="میزان امتیاز" type="number" value={points} onChange={(e) => setPoints(e.target.value)} fullWidth margin="normal" />
            
            <Button variant="contained" style={{backgroundColor:'#673ab7', color:'white'}} fullWidth size="large" onClick={handleTransfer} disabled={loading}>
                {loading ? 'در حال انتقال...' : 'انتقال امتیاز'}
            </Button>
            {msg && <Alert severity={msg.type} style={{marginTop:'15px'}}>{msg.text}</Alert>}
        </div>

        <Divider style={{margin:'40px 0'}} />

        <Typography variant="h6" gutterBottom>تاریخچه تراکنش‌های امتیاز</Typography>
        <TableContainer>
            <Table size="small">
                <TableHead>
                    <TableRow><TableCell>نوع</TableCell><TableCell>امتیاز</TableCell><TableCell>توضیحات</TableCell><TableCell>تاریخ</TableCell></TableRow>
                </TableHead>
                <TableBody>
                    {logs.map((log) => (
                        <TableRow key={log.id}>
                            <TableCell>
                                <Chip 
                                    label={log.log_type === 'SENT' ? 'ارسال' : log.log_type === 'RECEIVED' ? 'دریافت' : 'مصرف وام'} 
                                    color={log.log_type === 'RECEIVED' ? 'success' : 'default'} 
                                    size="small" variant="outlined"
                                />
                            </TableCell>
                            <TableCell style={{fontWeight:'bold', color: log.points > 0 ? 'green' : 'red', direction:'ltr'}}>
                                {log.points > 0 ? `+${log.points.toLocaleString()}` : log.points.toLocaleString()}
                            </TableCell>
                            <TableCell style={{fontSize:'0.9em'}}>{log.description}</TableCell>
                            <TableCell dir="ltr" style={{fontSize:'0.8em', color:'#888'}}>{new Date(log.created_at).toLocaleDateString('fa-IR')}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
        <Button onClick={() => navigate('/dashboard')} fullWidth style={{marginTop:'20px'}}>بازگشت به داشبورد</Button>
      </Paper>
    </Container>
  );
}

export default PointTransfer;