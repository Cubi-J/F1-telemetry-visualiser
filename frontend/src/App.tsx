import './App.css'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { HistoricDataPage } from './pages/HistoricDataPage'

function App() {

  return (
    <BrowserRouter>
      <nav
        style={{
          backgroundColor: '#1a1a1a', 
          borderBottom: '1px solid #333', 
          padding: '15px 30px', 
          display: 'flex', 
          gap: '20px',
          alignItems: 'center'
        }}
      >
        <div style={{ color: '#00CED5', fontWeight: 'bold', fontSize: '18px', marginRight: '20px' }}>
          F1 Telemetry Dashboard
        </div>
        <Link to="/" style={{ color: '#00CED5', textDecoration: 'none', fontWeight: 'bold' }}>Home</Link>
        <Link to="/historic" style={{ color: '#00CED5', textDecoration: 'none', fontWeight: 'bold' }}>Historic Data</Link>
      </nav>
    
    <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/historic" element={<HistoricDataPage />} />
    </Routes>
  
    </BrowserRouter>
  )
}

export default App
