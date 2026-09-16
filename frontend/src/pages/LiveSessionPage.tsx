import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Play, Pause, RotateCcw, Radio, Wifi, WifiOff } from 'lucide-react';

interface SessionItem {
  session_key: number;
  country_name: string;
  circuit_short_name: string;
  location: string;
  date_start: string;
  year: number;
}

interface DriverSectorTimes {
  s1?: number | null;
  s2?: number | null;
  s3?: number | null;
}

interface LeaderboardRow {
  position: number;
  driver_number: number;
  code: string;
  name: string;
  team: string;
  team_color: string;
  headshot_url?: string | null;
  gap_to_leader: string;
  interval: string;
  last_lap_time?: string | null;
  best_lap_time?: string | null;
  current_lap: number;
  tyre_compound: string;
  tyre_age: number;
  pit_stops: number;
  in_pit: boolean;
  sectors: DriverSectorTimes;
}

interface SessionInfo {
  session_key: number;
  session_name: string;
  meeting_name: string;
  circuit_key?: number | null;
  circuit_short_name: string;
  country_name: string;
  year: number;
  date_start?: string | null;
  date_end?: string | null;
}

interface TrackStatus {
  status: string;
  flag: string;
  message: string;
}

interface WeatherInfo {
  air_temp?: number | null;
  track_temp?: number | null;
  humidity?: number | null;
  rainfall?: number | null;
  wind_speed?: number | null;
  wind_direction?: number | null;
}

interface PlaybackState {
  mode: string;
  is_playing: boolean;
  speed: number;
  current_time: string;
  start_time: string;
  end_time: string;
  progress_pct: number;
}

interface DashboardFrame {
  timestamp: string;
  session_info: SessionInfo;
  track_status: TrackStatus;
  weather: WeatherInfo;
  leaderboard: LeaderboardRow[];
  playback: PlaybackState;
}

export const LiveSessionPage: React.FC = () => {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [selectedSessionKey, setSelectedSessionKey] = useState<number>(9523);
  const [frame, setFrame] = useState<DashboardFrame | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  // Load available sessions catalog
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await axios.get<SessionItem[]>('http://localhost:8000/api/live/sessions');
        setSessions(res.data);
      } catch (err) {
        console.error('Failed to load available sessions:', err);
      }
    };
    fetchSessions();
  }, []);

  // Fetch initial state via REST
  useEffect(() => {
    const fetchInitialState = async () => {
      try {
        setLoading(true);
        const res = await axios.get<DashboardFrame>('http://localhost:8000/api/live/state');
        setFrame(res.data);
        if (res.data.session_info?.session_key) {
          setSelectedSessionKey(res.data.session_info.session_key);
        }
      } catch (err) {
        setError('Failed to fetch initial live dashboard state.');
      } finally {
        setLoading(false);
      }
    };
    fetchInitialState();
  }, []);

  // Connect WebSocket for real-time stream
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: number | null = null;

    const connectWebSocket = () => {
      ws = new WebSocket('ws://localhost:8000/api/live/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.session_info && data.leaderboard) {
            setFrame(data as DashboardFrame);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket frame:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt reconnect after 2 seconds
        reconnectTimeout = window.setTimeout(connectWebSocket, 2000);
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        ws.close();
      }
    };
  }, []);

  // Control Actions
  const handleControl = async (action: string, params: Record<string, any> = {}) => {
    try {
      await axios.post('http://localhost:8000/api/live/control', {
        action,
        ...params,
      });
    } catch (err) {
      console.error(`Control action ${action} failed:`, err);
    }
  };

  const handleSessionChange = async (newSessionKey: number) => {
    setSelectedSessionKey(newSessionKey);
    setLoading(true);
    await handleControl('load_session', { session_key: newSessionKey });
    setLoading(false);
  };

  const getTyreBadgeStyle = (compound: string) => {
    const cmp = compound.toUpperCase();
    switch (cmp) {
      case 'SOFT':
        return { bg: '#E8002D', text: '#fff', border: '#E8002D' };
      case 'MEDIUM':
        return { bg: '#FFD700', text: '#111', border: '#FFD700' };
      case 'HARD':
        return { bg: '#FFFFFF', text: '#111', border: '#FFFFFF' };
      case 'INTERMEDIATE':
        return { bg: '#39B54A', text: '#fff', border: '#39B54A' };
      case 'WET':
        return { bg: '#00AEEF', text: '#fff', border: '#00AEEF' };
      default:
        return { bg: '#444444', text: '#ccc', border: '#666' };
    }
  };

  const getFlagColor = (flag: string) => {
    switch (flag.toUpperCase()) {
      case 'GREEN':
        return '#00D26A';
      case 'YELLOW':
        return '#F5D10D';
      case 'SAFETY CAR':
      case 'VSC':
        return '#FF8C00';
      case 'RED':
        return '#FF2A43';
      case 'CHEQUERED':
        return '#FFFFFF';
      default:
        return '#00CED5';
    }
  };

  return (
    <div style={{ backgroundColor: '#0e0e10', color: '#f0f0f0', minHeight: '100vh', padding: '24px', boxSizing: 'border-box', fontFamily: 'system-ui, sans-serif' }}>
      
      {/* Top Header & Replay Controls */}
      <div style={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '10px', padding: '16px 20px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          
          {/* Title & Connection Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 'bold', color: '#00CED5', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Radio size={20} color="#00CED5" />
              Live / Replay Session
            </h1>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: isConnected ? 'rgba(0, 206, 213, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: isConnected ? '#00CED5' : '#ef4444',
                border: `1px solid ${isConnected ? 'rgba(0, 206, 213, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
              }}
            >
              {isConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
              {isConnected ? 'LIVE WS' : 'DISCONNECTED'}
            </div>
          </div>

          {/* Session Selector & Playback Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            
            {/* Session Dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '13px', color: '#a1a1aa', fontWeight: 600 }}>Replay Session:</span>
              <select
                value={selectedSessionKey}
                onChange={(e) => handleSessionChange(Number(e.target.value))}
                style={{
                  backgroundColor: '#27272a',
                  color: '#fff',
                  border: '1px solid #3f3f46',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '13px',
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                {sessions.map((s) => (
                  <option key={s.session_key} value={s.session_key}>
                    {s.year} {s.circuit_short_name || s.location} ({s.country_name})
                  </option>
                ))}
              </select>
            </div>

            {/* Play/Pause Button */}
            <button
              onClick={() => handleControl(frame?.playback.is_playing ? 'pause' : 'play')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: frame?.playback.is_playing ? '#3f3f46' : '#00CED5',
                color: frame?.playback.is_playing ? '#fff' : '#111',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 14px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {frame?.playback.is_playing ? <Pause size={15} /> : <Play size={15} />}
              {frame?.playback.is_playing ? 'Pause' : 'Play'}
            </button>

            {/* Speed Multiplier Buttons */}
            <div style={{ display: 'flex', border: '1px solid #3f3f46', borderRadius: '6px', overflow: 'hidden' }}>
              {[0.5, 1.0, 2.0, 5.0].map((spd) => (
                <button
                  key={spd}
                  onClick={() => handleControl('set_speed', { speed: spd })}
                  style={{
                    backgroundColor: frame?.playback.speed === spd ? '#00CED5' : '#27272a',
                    color: frame?.playback.speed === spd ? '#111' : '#a1a1aa',
                    border: 'none',
                    padding: '6px 10px',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                  }}
                >
                  {spd}x
                </button>
              ))}
            </div>

            {/* Reset to Start */}
            <button
              onClick={() => frame && handleControl('seek', { timestamp: frame.playback.start_time })}
              title="Reset to beginning"
              style={{
                backgroundColor: '#27272a',
                color: '#a1a1aa',
                border: '1px solid #3f3f46',
                borderRadius: '6px',
                padding: '6px 8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <RotateCcw size={15} />
            </button>
          </div>
        </div>

        {/* Playback Progress Bar */}
        {frame?.playback && (
          <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '11px', color: '#71717a', fontFamily: 'monospace' }}>
              {new Date(frame.playback.start_time).toLocaleTimeString()}
            </span>
            <div
              style={{
                flex: 1,
                height: '6px',
                backgroundColor: '#27272a',
                borderRadius: '3px',
                position: 'relative',
                cursor: 'pointer',
              }}
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const pct = Math.max(0, Math.min(1, clickX / rect.width));
                const start = new Date(frame.playback.start_time).getTime();
                const end = new Date(frame.playback.end_time).getTime();
                const targetTime = new Date(start + (end - start) * pct).toISOString();
                handleControl('seek', { timestamp: targetTime });
              }}
            >
              <div
                style={{
                  width: `${frame.playback.progress_pct}%`,
                  height: '100%',
                  backgroundColor: '#00CED5',
                  borderRadius: '3px',
                  transition: 'width 0.2s linear',
                }}
              />
            </div>
            <span style={{ fontSize: '11px', color: '#00CED5', fontFamily: 'monospace', fontWeight: 'bold' }}>
              {new Date(frame.playback.current_time).toLocaleTimeString()}
            </span>
            <span style={{ fontSize: '11px', color: '#71717a', fontFamily: 'monospace' }}>
              {new Date(frame.playback.end_time).toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>

      {/* Session Banner: Track Status & Weather */}
      {frame && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '12px',
            marginBottom: '20px',
          }}
        >
          {/* Circuit Info */}
          <div style={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px', padding: '12px 16px' }}>
            <div style={{ fontSize: '11px', color: '#71717a', textTransform: 'uppercase', fontWeight: 'bold' }}>Session</div>
            <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#fff', marginTop: '2px' }}>
              {frame.session_info.meeting_name}
            </div>
            <div style={{ fontSize: '13px', color: '#00CED5' }}>
              {frame.session_info.session_name} • {frame.session_info.year}
            </div>
          </div>

          {/* Track Status / Flag */}
          <div
            style={{
              backgroundColor: '#18181b',
              border: `1px solid ${getFlagColor(frame.track_status.flag)}40`,
              borderRadius: '8px',
              padding: '12px 16px',
            }}
          >
            <div style={{ fontSize: '11px', color: '#71717a', textTransform: 'uppercase', fontWeight: 'bold' }}>Track Status</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <div
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  backgroundColor: getFlagColor(frame.track_status.flag),
                  boxShadow: `0 0 8px ${getFlagColor(frame.track_status.flag)}`,
                }}
              />
              <span style={{ fontSize: '15px', fontWeight: 'bold', color: getFlagColor(frame.track_status.flag) }}>
                {frame.track_status.flag}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#a1a1aa', marginTop: '2px' }}>
              {frame.track_status.message}
            </div>
          </div>

          {/* Weather */}
          <div style={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px', padding: '12px 16px' }}>
            <div style={{ fontSize: '11px', color: '#71717a', textTransform: 'uppercase', fontWeight: 'bold' }}>Weather Conditions</div>
            <div style={{ display: 'flex', gap: '16px', marginTop: '4px', fontSize: '13px' }}>
              <div>
                <span style={{ color: '#71717a' }}>Air: </span>
                <span style={{ color: '#fff', fontWeight: 'bold' }}>{frame.weather.air_temp ?? '--'}°C</span>
              </div>
              <div>
                <span style={{ color: '#71717a' }}>Track: </span>
                <span style={{ color: '#00CED5', fontWeight: 'bold' }}>{frame.weather.track_temp ?? '--'}°C</span>
              </div>
              <div>
                <span style={{ color: '#71717a' }}>Rain: </span>
                <span style={{ color: frame.weather.rainfall ? '#38bdf8' : '#fff', fontWeight: 'bold' }}>
                  {frame.weather.rainfall ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Driver Leaderboard Table */}
      <div style={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '10px', overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #27272a', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 'bold', color: '#fff' }}>
            Driver Standings ({frame?.leaderboard.length || 0} Drivers)
          </h2>
          <span style={{ fontSize: '12px', color: '#71717a' }}>
            Updated {frame ? new Date(frame.timestamp).toLocaleTimeString() : '--:--:--'}
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#121214', color: '#71717a', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <th style={{ padding: '10px 14px', width: '50px' }}>Pos</th>
                <th style={{ padding: '10px 14px' }}>Driver</th>
                <th style={{ padding: '10px 14px' }}>Gap / Interval</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>Lap</th>
                <th style={{ padding: '10px 14px' }}>Last Lap</th>
                <th style={{ padding: '10px 14px' }}>Best Lap</th>
                <th style={{ padding: '10px 14px' }}>Tyre Compound</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>Stops</th>
                <th style={{ padding: '10px 14px' }}>Sectors (S1 / S2 / S3)</th>
              </tr>
            </thead>
            <tbody>
              {!frame || frame.leaderboard.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ padding: '30px', textAlign: 'center', color: '#71717a' }}>
                    {loading ? 'Loading live session data...' : error || 'No live session active.'}
                  </td>
                </tr>
              ) : (
                frame.leaderboard.map((row) => {
                  const tyreStyle = getTyreBadgeStyle(row.tyre_compound);
                  return (
                    <tr
                      key={row.driver_number}
                      style={{
                        borderBottom: '1px solid #27272a',
                        transition: 'background-color 0.15s',
                        backgroundColor: row.in_pit ? 'rgba(239, 68, 68, 0.05)' : 'transparent',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#202024')}
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.backgroundColor = row.in_pit ? 'rgba(239, 68, 68, 0.05)' : 'transparent')
                      }
                    >
                      {/* Position */}
                      <td style={{ padding: '10px 14px', fontWeight: 'bold', color: row.position <= 3 ? '#00CED5' : '#fff' }}>
                        {row.position}
                      </td>

                      {/* Driver & Team */}
                      <td style={{ padding: '10px 14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div
                            style={{
                              width: '4px',
                              height: '24px',
                              backgroundColor: row.team_color || '#00CED5',
                              borderRadius: '2px',
                            }}
                          />
                          <div>
                            <div style={{ fontWeight: 'bold', color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span>{row.code}</span>
                              <span style={{ fontWeight: 'normal', color: '#a1a1aa', fontSize: '12px' }}>
                                #{row.driver_number}
                              </span>
                              {row.in_pit && (
                                <span
                                  style={{
                                    backgroundColor: '#ef4444',
                                    color: '#fff',
                                    fontSize: '10px',
                                    padding: '1px 5px',
                                    borderRadius: '3px',
                                    fontWeight: 'bold',
                                  }}
                                >
                                  PIT
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: '11px', color: '#71717a' }}>{row.team}</div>
                          </div>
                        </div>
                      </td>

                      {/* Gap / Interval */}
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace' }}>
                        <div style={{ color: '#fff', fontWeight: 600 }}>{row.gap_to_leader}</div>
                        <div style={{ fontSize: '11px', color: '#71717a' }}>{row.interval}</div>
                      </td>

                      {/* Current Lap */}
                      <td style={{ padding: '10px 14px', textAlign: 'center', fontWeight: 600, color: '#e4e4e7' }}>
                        {row.current_lap}
                      </td>

                      {/* Last Lap Time */}
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: '#e4e4e7' }}>
                        {row.last_lap_time || '--:--.---'}
                      </td>

                      {/* Best Lap Time */}
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: '#00CED5', fontWeight: 600 }}>
                        {row.best_lap_time || '--:--.---'}
                      </td>

                      {/* Tyre Compound & Age */}
                      <td style={{ padding: '10px 14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span
                            style={{
                              backgroundColor: tyreStyle.bg,
                              color: tyreStyle.text,
                              border: `1px solid ${tyreStyle.border}`,
                              borderRadius: '4px',
                              padding: '2px 6px',
                              fontSize: '11px',
                              fontWeight: 'bold',
                              textTransform: 'uppercase',
                            }}
                          >
                            {row.tyre_compound[0] || 'U'}
                          </span>
                          <span style={{ color: '#a1a1aa', fontSize: '12px' }}>
                            {row.tyre_age} {row.tyre_age === 1 ? 'lap' : 'laps'}
                          </span>
                        </div>
                      </td>

                      {/* Pit Stops */}
                      <td style={{ padding: '10px 14px', textAlign: 'center', color: '#a1a1aa' }}>
                        {row.pit_stops}
                      </td>

                      {/* Sectors */}
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace', fontSize: '12px' }}>
                        <span style={{ color: row.sectors.s1 ? '#e4e4e7' : '#52525b' }}>
                          {row.sectors.s1 ? row.sectors.s1.toFixed(3) : '--.---'}
                        </span>
                        <span style={{ color: '#52525b' }}> / </span>
                        <span style={{ color: row.sectors.s2 ? '#e4e4e7' : '#52525b' }}>
                          {row.sectors.s2 ? row.sectors.s2.toFixed(3) : '--.---'}
                        </span>
                        <span style={{ color: '#52525b' }}> / </span>
                        <span style={{ color: row.sectors.s3 ? '#e4e4e7' : '#52525b' }}>
                          {row.sectors.s3 ? row.sectors.s3.toFixed(3) : '--.---'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
