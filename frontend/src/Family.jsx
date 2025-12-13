import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Paper, Typography, TextField, Button, Box, List, ListItem, ListItemText, ListItemAvatar, Avatar, Divider, Chip } from '@mui/material';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import FaceIcon from '@mui/icons-material/Face';
import { useNavigate } from 'react-router-dom';
import { toEnglishDigits } from './utils';

function Family() {
  const navigate = useNavigate();
  const [members, setMembers] = useState([]);
  const [formData, setFormData] = useState({ full_name: '', national_code: '' });
  const [loading, setLoading] = useState(false);

  // دریافت لیست اعضا
  const fetchMembers = async () => {
    const token = localStorage.getItem('token');
    const res = await axios.get('https://sandogh-server.liara.run/api/users/family/', {
       headers: { Authorization: `Token ${token}` }
    });
    setMembers(res.data);
  };

  useEffect(() => { fetchMembers(); }, []);

  const handleAdd = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    try {
        await axios.post('https://sandogh-server.liara.run/api/users/family/', formData, {
            headers: { Authorization: `Token ${token}` }
        });
        alert("✅ عضو جدید اضافه شد!");
        setFormData({ full_name: '', national_code: '' });
        fetchMembers(); // رفرش لیست
    } catch (e) {
        alert("خطا در افزودن عضو (کد ملی تکراری یا اشتباه)");
    }
    setLoading(false);
  };

  return (
    <Container maxWidth="sm" style={{ marginTop: '30px' }}>
      <Paper elevation={3} style={{ padding: '20px' }}>
        <Typography variant="h5" gutterBottom>مدیریت اعضای خانواده</Typography>
        
        {/* فرم افزودن */}
        <Box component="form" sx={{ p: 2, border: '1px dashed #ccc', borderRadius: 2, mb: 3 }}>
            <Typography variant="subtitle2">افزودن عضو جدید (زیرمجموعه)</Typography>
            <TextField label="نام و نام خانوادگی" fullWidth margin="dense" size="small"
                value={formData.full_name} 
                onChange={(e) => setFormData({...formData, full_name: e.target.value})} 
            />
            <TextField label="کد ملی" fullWidth margin="dense" size="small" dir="ltr"
                value={formData.national_code} 
                onChange={(e) => setFormData({...formData, national_code: toEnglishDigits(e.target.value)})} 
            />
            <Button variant="contained" startIcon={<PersonAddIcon />} fullWidth onClick={handleAdd} disabled={loading}>
                {loading ? '...' : 'افزودن به خانواده'}
            </Button>
        </Box>

        {/* لیست اعضا */}
        <List>
            {members.map((m) => (
                <div key={m.id}>
                    <ListItem button onClick={() => navigate(`/dashboard?user_id=${m.id}`)}>
                        <ListItemAvatar><Avatar><FaceIcon /></Avatar></ListItemAvatar>
                        <ListItemText 
                            primary={m.full_name} 
                            secondary={`کد عضویت: ${m.membership_code} | کد ملی: ${m.national_code}`} 
                        />
                        <Chip label="مشاهده پنل" size="small" color="primary" variant="outlined" />
                    </ListItem>
                    <Divider />
                </div>
            ))}
        </List>
      </Paper>
    </Container>
  );
}
export default Family;