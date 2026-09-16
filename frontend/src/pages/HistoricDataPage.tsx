import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { PlotlyGraph } from '../components/PlotlyGraph';
import { DriverMultiSelect, type DriverOption } from '../components/DriverMultiSelect';

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
  LapTime: string;
  Sector1: string;
  Sector2: string;
  Sector3: string;
}

interface TableRowData extends TimingData {
  Driver: string;
}

interface DriverData {
  line_config: { color: string; dash: string };
  telemetry: TelemetryPoint[];
  timing_data: TimingData;
}

type ApiResponse = Record<string, DriverData>;

interface EventInfo {
  name: string;
  round: number;
  country: string;
  location: string;
  sessions: string[];
}

interface SeasonData {
  events: EventInfo[];
}

interface CatalogData {
  years: number[];
  seasons: Record<string, SeasonData>;
}

const CATALOG_STORAGE_KEY = 'f1_catalog_cache';
const DRIVERS_CACHE_PREFIX = 'f1_drivers_cache_';

// ---------------------------------------------------------------------------
// PAGE
// ---------------------------------------------------------------------------

export const HistoricDataPage: React.FC = () => {
  // Catalog & options state
  const [catalog, setCatalog] = useState<CatalogData | null>(null);
  const [catalogLoading, setCatalogLoading] = useState<boolean>(true);

  // Selected values
  const [year, setYear] = useState<number>(2024);
  const [event, setEvent] = useState<string>('');
  const [session, setSession] = useState<string>('');
  const [selectedDrivers, setSelectedDrivers] = useState<string[]>([]);

  // Driver options for selected session
  const [availableDrivers, setAvailableDrivers] = useState<DriverOption[]>([]);
  const [driversLoading, setDriversLoading] = useState<boolean>(false);

  // Telemetry fetch state
  const [telemetryData, setTelemetryData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const loadCatalog = async () => {
      setCatalogLoading(true);

      // Check sessionStorage for cached catalog
      const cached = sessionStorage.getItem(CATALOG_STORAGE_KEY);
      if (cached) {
        try {
          const parsedCatalog: CatalogData = JSON.parse(cached);
          setCatalog(parsedCatalog);
          if (parsedCatalog.years && parsedCatalog.years.length > 0) {
            setYear(parsedCatalog.years[0]);
          }
          setCatalogLoading(false);
          return;
        } catch (e) {
          sessionStorage.removeItem(CATALOG_STORAGE_KEY);
        }
      }

      try {
        const response = await axios.get<{ status: string; data: CatalogData }>('http://localhost:8000/api/f1-catalog');
        const data = response.data.data;
        setCatalog(data);
        sessionStorage.setItem(CATALOG_STORAGE_KEY, JSON.stringify(data));

        if (data.years && data.years.length > 0) {
          setYear(data.years[0]);
        }
      } catch (err: any) {
        setError('Failed to load F1 season catalog. Please ensure the backend is running.');
      } finally {
        setCatalogLoading(false);
      }
    };

    loadCatalog();
  }, []);

  // ---------------------------------------------------------------------------
  // GET EVENTS AND SESSIONS FOR YEAR
  // ---------------------------------------------------------------------------
  const eventsForYear: EventInfo[] = useMemo(() => {
    if (!catalog || !catalog.seasons[String(year)]) return [];
    return catalog.seasons[String(year)].events;
  }, [catalog, year]);

  useEffect(() => {
    if (eventsForYear.length > 0) {
      const exists = eventsForYear.some((e) => e.name === event);
      if (!exists) {
        setEvent(eventsForYear[0].name);
      }
    } else {
      setEvent('');
    }
  }, [eventsForYear, event]);

  const currentEventInfo = useMemo(() => {
    return eventsForYear.find((e) => e.name === event);
  }, [eventsForYear, event]);

  const sessionsForEvent: string[] = useMemo(() => {
    return currentEventInfo?.sessions || [];
  }, [currentEventInfo]);

  useEffect(() => {
    if (sessionsForEvent.length > 0) {
      if (!sessionsForEvent.includes(session)) {
        if (sessionsForEvent.includes('Qualifying')) {
          setSession('Qualifying');
        } else {
          setSession(sessionsForEvent[sessionsForEvent.length - 1]);
        }
      }
    } else {
      setSession('');
    }
  }, [sessionsForEvent, session]);

  // ---------------------------------------------------------------------------
  // FETCH DRIVERS 
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!year || !event || !session) {
      setAvailableDrivers([]);
      return;
    }

    const cacheKey = `${DRIVERS_CACHE_PREFIX}${year}_${event}_${session}`;
    const cachedDrivers = sessionStorage.getItem(cacheKey);

    if (cachedDrivers) {
      try {
        const parsedDrivers: DriverOption[] = JSON.parse(cachedDrivers);
        setAvailableDrivers(parsedDrivers);
        setSelectedDrivers((prev) =>
          prev.filter((code) => parsedDrivers.some((d) => d.code === code))
        );
        return;
      } catch (e) {
        sessionStorage.removeItem(cacheKey);
      }
    }

    let isCancelled = false;
    const fetchDrivers = async () => {
      setDriversLoading(true);
      try {
        const response = await axios.get<{ status: string; data: DriverOption[] }>(
          'http://localhost:8000/api/drivers',
          {
            params: { year, event, session },
          }
        );
        if (!isCancelled) {
          const drivers = response.data.data;
          setAvailableDrivers(drivers);
          sessionStorage.setItem(cacheKey, JSON.stringify(drivers));

          setSelectedDrivers((prev) =>
            prev.filter((code) => drivers.some((d) => d.code === code))
          );
        }
      } catch (err: any) {
        if (!isCancelled) {
          console.error('Failed to load drivers for session:', err);
        }
      } finally {
        if (!isCancelled) {
          setDriversLoading(false);
        }
      }
    };

    fetchDrivers();

    return () => {
      isCancelled = true;
    };
  }, [year, event, session]);

  // ---------------------------------------------------------------------------
  // FETCH TELEMETRY DATA
  // ---------------------------------------------------------------------------
  const handleFetchData = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedDrivers.length === 0) {
      setError('Please select at least one driver.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.get<{ status: string; data: ApiResponse }>(
        'http://localhost:8000/api/fastest-lap-data',
        {
          params: {
            year,
            event,
            session,
            drivers: selectedDrivers,
          },
          paramsSerializer: {
            indexes: null,
          },
        }
      );

      setTelemetryData(response.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch telemetry data.');
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // BUILD PLOTLY TRACES & LAP TIMES
  // ---------------------------------------------------------------------------
  const plotlyTraces: any[] = [];
  const lapTimeTableRows: TableRowData[] = [];

  if (telemetryData) {
    Object.keys(telemetryData).forEach((driver) => {
      const driverData = telemetryData[driver];
      const telemetry = driverData.telemetry;
      const lineColor = driverData.line_config.color;
      const lineDash = driverData.line_config.dash === 'dash' ? 'dash' : 'solid';

      lapTimeTableRows.push({
        Driver: driver,
        ...driverData.timing_data,
      });

      const distances = telemetry.map((pt) => pt.Distance);
      const speeds = telemetry.map((pt) => pt.Speed);
      const throttles = telemetry.map((pt) => pt.Throttle);
      const brakes = telemetry.map((pt) => (pt.Brake ? 1 : 0));

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
    <div style={{ backgroundColor: '#111111', color: '#00CED5', padding: '24px', minHeight: '100vh', boxSizing: 'border-box' }}>
      <h2 style={{ margin: '0 0 20px 0', fontSize: '24px', fontWeight: 'bold' }}>Historic Fastest Lap</h2>

      {/* Control Panel / Dropdowns */}
      <form
        onSubmit={handleFetchData}
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '16px',
          alignItems: 'flex-end',
          backgroundColor: '#191919',
          padding: '16px 20px',
          borderRadius: '8px',
          border: '1px solid #282828',
          marginBottom: '24px',
        }}
      >
        {/* Year Dropdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '110px' }}>
          <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#888', textTransform: 'uppercase' }}>Year</label>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            disabled={catalogLoading || loading}
            style={{
              backgroundColor: '#222',
              color: '#fff',
              border: '1px solid #333',
              borderRadius: '6px',
              padding: '8px 12px',
              fontSize: '14px',
              cursor: 'pointer',
              outline: 'none',
              height: '38px',
            }}
          >
            {catalog?.years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>

        {/* Event Dropdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '220px', flex: 1 }}>
          <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#888', textTransform: 'uppercase' }}>Event / Grand Prix</label>
          <select
            value={event}
            onChange={(e) => setEvent(e.target.value)}
            disabled={catalogLoading || eventsForYear.length === 0 || loading}
            style={{
              backgroundColor: '#222',
              color: '#fff',
              border: '1px solid #333',
              borderRadius: '6px',
              padding: '8px 12px',
              fontSize: '14px',
              cursor: 'pointer',
              outline: 'none',
              height: '38px',
            }}
          >
            {eventsForYear.map((ev) => (
              <option key={ev.name} value={ev.name}>
                {ev.round > 0 ? `R${ev.round} - ` : ''}{ev.name}
              </option>
            ))}
          </select>
        </div>

        {/* Session Dropdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '160px' }}>
          <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#888', textTransform: 'uppercase' }}>Session</label>
          <select
            value={session}
            onChange={(e) => setSession(e.target.value)}
            disabled={catalogLoading || sessionsForEvent.length === 0 || loading}
            style={{
              backgroundColor: '#222',
              color: '#fff',
              border: '1px solid #333',
              borderRadius: '6px',
              padding: '8px 12px',
              fontSize: '14px',
              cursor: 'pointer',
              outline: 'none',
              height: '38px',
            }}
          >
            {sessionsForEvent.map((sess) => (
              <option key={sess} value={sess}>
                {sess}
              </option>
            ))}
          </select>
        </div>

        {/* Driver Multi-Select */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 2, minWidth: '260px' }}>
          <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#888', textTransform: 'uppercase' }}>
            Drivers ({selectedDrivers.length} selected)
          </label>
          <DriverMultiSelect
            drivers={availableDrivers}
            selectedDrivers={selectedDrivers}
            onChange={setSelectedDrivers}
            loading={driversLoading}
            disabled={catalogLoading || loading}
          />
        </div>

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            disabled={loading || catalogLoading || selectedDrivers.length === 0}
            style={{
              backgroundColor: loading || catalogLoading || selectedDrivers.length === 0 ? '#444' : '#00CED5',
              color: '#111',
              fontWeight: 'bold',
              border: 'none',
              borderRadius: '6px',
              padding: '0 20px',
              height: '38px',
              cursor: loading || catalogLoading || selectedDrivers.length === 0 ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
            }}
          >
            {loading ? 'Fetching...' : 'Fetch Telemetry'}
          </button>
        </div>
      </form>

      {/* Error Alert */}
      {error && (
        <div
          style={{
            backgroundColor: '#3b1219',
            border: '1px solid #f85149',
            color: '#ff7b72',
            padding: '12px 16px',
            borderRadius: '6px',
            marginBottom: '20px',
            fontSize: '14px',
          }}
        >
          {error}
        </div>
      )}

      {/* Lap Time Table */}
      {lapTimeTableRows.length > 0 && (
        <div style={{ backgroundColor: '#191919', borderRadius: '8px', border: '1px solid #282828', padding: '16px', marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', color: '#fff' }}>Lap Timing Comparison</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', color: '#e0e0e0', fontSize: '14px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #333', textAlign: 'left', color: '#888', fontSize: '12px', textTransform: 'uppercase' }}>
                  <th style={{ padding: '10px 12px' }}>Driver</th>
                  <th style={{ padding: '10px 12px' }}>Lap Time</th>
                  <th style={{ padding: '10px 12px' }}>Sector 1</th>
                  <th style={{ padding: '10px 12px' }}>Sector 2</th>
                  <th style={{ padding: '10px 12px' }}>Sector 3</th>
                </tr>
              </thead>
              <tbody>
                {lapTimeTableRows.map((row) => (
                  <tr key={row.Driver} style={{ borderBottom: '1px solid #242424' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 'bold', color: '#00CED5' }}>{row.Driver}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>{row.LapTime}</td>
                    <td style={{ padding: '10px 12px', color: '#aaa' }}>{row.Sector1}</td>
                    <td style={{ padding: '10px 12px', color: '#aaa' }}>{row.Sector2}</td>
                    <td style={{ padding: '10px 12px', color: '#aaa' }}>{row.Sector3}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Telemetry Charts */}
      <div style={{ backgroundColor: '#191919', borderRadius: '8px', border: '1px solid #282828', padding: '16px' }}>
        <PlotlyGraph
          data={plotlyTraces}
          layout={{
            title: { text: 'Fastest Lap Telemetry' },
            template: 'plotly_dark' as any,
            plot_bgcolor: '#191919',
            paper_bgcolor: '#191919',
            font: { color: '#00CED5' },
            hovermode: 'x unified',
            yaxis: { title: { text: 'Speed (km/h)' }, gridcolor: '#282828', domain: [0.68, 1.0] },
            yaxis2: { title: { text: 'Throttle (%)' }, gridcolor: '#282828', range: [-5, 105], domain: [0.34, 0.64] },
            yaxis3: {
              title: { text: 'Brake (on/off)' },
              gridcolor: '#282828',
              range: [-0.1, 1.1],
              domain: [0.0, 0.3],
              tickvals: [0, 1],
              ticktext: ['Off', 'On'],
            },
            xaxis: { title: { text: 'Distance (m)' }, gridcolor: '#282828', anchor: 'y3' },
            autosize: true,
          }}
        />
      </div>
    </div>
  );
};