import React from 'react';
import { Link } from 'react-router-dom';

export const HomePage: React.FC = () => {
  return (
    <div style={{ backgroundColor: '#111111', color: '#00CED5', padding: '40px', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <h1>F1 Telemetry Dashboard</h1>
      <p style={{ color: '#aaa' }}>Welcome! Select a module below to analyze F1 data.</p>

      <div style={{ display: 'flex', gap: '20px', marginTop: '30px' }}>
        {/* Navigation Card for Historic Data */}
        <div style={{ border: '1px solid #333', padding: '20px', borderRadius: '8px', width: '280px', backgroundColor: '#1a1a1a' }}>
          <h3>Historic Telemetry</h3>
          <p style={{ color: '#888', fontSize: '14px' }}>
            Compare driver speed, throttle, and brake traces for past Grand Prix sessions.
          </p>
          <Link 
            to="/historic" 
            style={{ 
              display: 'inline-block', 
              marginTop: '10px', 
              padding: '10px 16px', 
              backgroundColor: '#00CED5', 
              color: '#111', 
              fontWeight: 'bold', 
              textDecoration: 'none', 
              borderRadius: '4px' 
            }}
          >
            Launch Visualizer →
          </Link>
        </div>

        {/* Placeholder Navigation Card for Live Data */}
        <div style={{ border: '1px solid #333', padding: '20px', borderRadius: '8px', width: '280px', backgroundColor: '#1a1a1a', opacity: 0.6 }}>
          <h3>Live Session (WS)</h3>
          <p style={{ color: '#888', fontSize: '14px' }}>
            Connect to live WebSocket stream during active race weekends.
          </p>
          <span style={{ color: '#666', fontSize: '12px' }}>Coming soon</span>
        </div>
      </div>
    </div>
  );
};