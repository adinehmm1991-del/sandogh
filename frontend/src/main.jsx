import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { BrowserRouter } from 'react-router-dom' // <--- این خط باید باشد

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>  {/* <--- این تگ شروع باید باشد */}
      <App />
    </BrowserRouter> {/* <--- این تگ پایان باید باشد */}
  </React.StrictMode>,
)