import React, { useState } from 'react';
import axios from 'axios';
import { PlotlyGraph } from '../components/PlotlyGraph';


// ---------------------------------------------------------------------------
// INTERFACES
// ---------------------------------------------------------------------------
interface TelemetryPoint {
  Distance: number;
  Speed: number;
  Throttle: number;
  Brake: number;
}

interface TimingData {
  Driver: string;
  LapTime: string;
  Sector1: string;
  Sector2: string;
  Sector3: string;
}

interface DriverData {
  line_config: { color: string; dash: string };
  telemetry: TelemetryPoint[];
  timing_data: TimingData;
}

type ApiResponse = Record<string, DriverData>;

// ---------------------------------------------------------------------------
// PAGE
// ---------------------------------------------------------------------------

export const HistoricDataPage: React.FC = () => {
  
  const [year, setYear] = useState<number>(2026);
  const [event, setEvent] = useState<string>('Silverstone');
  const [session, setSession] = useState<string>('Q');
  const [driversInput, setDriversInput] = useState<string>('VER, HAM');

  const [telemetryData, setTelemetryData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // FETCH DATA
  // ---------------------------------------------------------------------------
  const handleFetchData = async (e: React.SubmitEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const driversArray = driversInput.split(',').map((d) => d.trim().toUpperCase());

    try {
      const response = await axios.get<ApiResponse>('http://localhost:8000/api/fastest-lap-data', {
        params: {
          year,
          event,
          session,
          drivers: driversArray,
        },
      });

      setTelemetryData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch telemetry data.');
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // PLOTLY TRACE
  // ---------------------------------------------------------------------------
  const plotlyTraces: any[] = [];
  const lapTimeTableRows: TimingData[] = [];

  if (telemetryData) {
    Object.keys(telemetryData).forEach((driver) => {
      const driverData = telemetryData[driver];
      const telemetry = driverData.telemetry;
      const lineColor = driverData.line_config.color;
      const lineDash = driverData.line_config.dash === 'dash' ? 'dash' : 'solid';

      lapTimeTableRows.push(driverData.timing_data);

      const distances = telemetry.map((pt) => pt.Distance);
      const speeds = telemetry.map((pt) => pt.Speed);
      const throttles = telemetry.map((pt) => pt.Throttle);
      const brakes = telemetry.map((pt) => pt.Brake);

      plotlyTraces.push({
        x: distances,
        y: speeds,
        name: `Speed - ${driver}`,
        type: 'scatter',
        mode: 'lines',
        line: { color: lineColor, dash: lineDash },
        legendgroup: driver,
        xaxis: 'x',
        yaxis: 'y',
      });

      plotlyTraces.push({
        x: distances,
        y: throttles,
        name: `Throttle - ${driver}`,
        type: 'scatter',
        mode: 'lines',
        line: { color: lineColor, dash: lineDash },
        legendgroup: driver,
        showlegend: false,
        xaxis: 'x',
        yaxis: 'y2',
      });

      plotlyTraces.push({
        x: distances,
        y: brakes,
        name: `Brake - ${driver}`,
        type: 'scatter',
        mode: 'lines',
        line: { color: lineColor, dash: lineDash },
        legendgroup: driver,
        showlegend: false,
        xaxis: 'x',
        yaxis: 'y3',
      });
    });
  }

  // ---------------------------------------------------------------------------
  // JSX LAYOUT
  // ---------------------------------------------------------------------------
  return (
    <div style={{ backgroundColor: '#111111', color: '#00CED5', padding: '20px', minHeight: '100vh' }}>
      <h2>Historic Fastest Lap</h2>

      <form onSubmit={handleFetchData} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input
          type="number"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          style={{ backgroundColor: '#222', color: '#00CED5', border: '1px solid #333', padding: '8px' }}
        />
        <input
          type="text"
          value={event}
          onChange={(e) => setEvent(e.target.value)}
          placeholder="Event"
          style={{ backgroundColor: '#222', color: '#00CED5', border: '1px solid #333', padding: '8px' }}
        />
        <input
          type="text"
          value={session}
          onChange={(e) => setSession(e.target.value)}
          placeholder="Session"
          style={{ backgroundColor: '#222', color: '#00CED5', border: '1px solid #333', padding: '8px' }}
        />
        <input
          type="text"
          value={driversInput}
          onChange={(e) => setDriversInput(e.target.value)}
          placeholder="Drivers (e.g. VER, HAM)"
          style={{ backgroundColor: '#222', color: '#00CED5', border: '1px solid #333', padding: '8px' }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{ backgroundColor: '#00CED5', color: '#111', fontWeight: 'bold', border: 'none', padding: '8px 16px', cursor: 'pointer' }}
        >
          {loading ? 'Loading...' : 'Fetch Telemetry'}
        </button>
      </form>

      {error && <div style={{ color: '#ff4d4d', marginBottom: '15px' }}>{error}</div>}

      {lapTimeTableRows.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '20px', color: '#00CED5' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #333', textAlign: 'left' }}>
              <th style={{ padding: '8px' }}>Driver</th>
              <th style={{ padding: '8px' }}>Lap Time</th>
              <th style={{ padding: '8px' }}>Sector 1</th>
              <th style={{ padding: '8px' }}>Sector 2</th>
              <th style={{ padding: '8px' }}>Sector 3</th>
            </tr>
          </thead>
          <tbody>
            {lapTimeTableRows.map((row) => (
              <tr key={row.Driver} style={{ borderBottom: '1px solid #222' }}>
                <td style={{ padding: '8px', fontWeight: 'bold' }}>{row.Driver}</td>
                <td style={{ padding: '8px' }}>{row.LapTime}</td>
                <td style={{ padding: '8px' }}>{row.Sector1}</td>
                <td style={{ padding: '8px' }}>{row.Sector2}</td>
                <td style={{ padding: '8px' }}>{row.Sector3}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div style={{ width: '100%' }}>
        <PlotlyGraph
          data={plotlyTraces}
          layout={{
            title: { text: 'Fastest Lap Telemetry' },
            template: 'plotly_dark' as any,
            plot_bgcolor: '#111111',
            paper_bgcolor: '#111111',
            font: { color: '#00CED5' },
            grid: { rows: 3, columns: 1, pattern: 'independent' },
            yaxis: { title: { text: 'Speed (km/h)' }, gridcolor: '#333' },
            yaxis2: { title: { text: 'Throttle (%)' }, gridcolor: '#333', range: [-5, 105] },
            yaxis3: { title: { text: 'Brake (on/off)' }, gridcolor: '#333', range: [0, 1] },
            xaxis: { title: { text: 'Distance (m)' }, gridcolor: '#333' },
            autosize: true,
          }}
        />
      </div>
    </div>
  );
};