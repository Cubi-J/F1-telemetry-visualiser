from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SessionInfo(BaseModel):
    session_key: int
    session_name: str
    meeting_name: str
    circuit_key: Optional[int] = None
    circuit_short_name: str
    country_name: str
    year: int
    date_start: Optional[str] = None
    date_end: Optional[str] = None


class DriverSectorTimes(BaseModel):
    s1: Optional[float] = None
    s2: Optional[float] = None
    s3: Optional[float] = None


class LeaderboardRow(BaseModel):
    position: int
    driver_number: int
    code: str
    name: str
    team: str
    team_color: str
    headshot_url: Optional[str] = None
    gap_to_leader: str = "+0.000"
    interval: str = "LEADER"
    last_lap_time: Optional[str] = None
    best_lap_time: Optional[str] = None
    current_lap: int = 1
    tyre_compound: str = "UNKNOWN"
    tyre_age: int = 0
    pit_stops: int = 0
    in_pit: bool = False
    sectors: DriverSectorTimes = Field(default_factory=DriverSectorTimes)


class DriverLocation(BaseModel):
    driver_number: int
    code: str
    team_color: str
    x: float
    y: float
    z: float = 0.0


class TrackStatus(BaseModel):
    status: str = "1"  # Status code (AllClear, Yellow, SC, Red, VSC)
    flag: str = "GREEN"  # GREEN, YELLOW, RED, CHEQUERED
    message: str = "TRACK CLEAR"


class WeatherInfo(BaseModel):
    air_temp: Optional[float] = None
    track_temp: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[int] = None


class PlaybackState(BaseModel):
    mode: str = "replay"  # 'replay' or 'live'
    is_playing: bool = True
    speed: float = 1.0
    current_time: str
    start_time: str
    end_time: str
    progress_pct: float = 0.0


class DashboardFrame(BaseModel):
    timestamp: str
    session_info: SessionInfo
    track_status: TrackStatus = Field(default_factory=TrackStatus)
    weather: WeatherInfo = Field(default_factory=WeatherInfo)
    leaderboard: List[LeaderboardRow] = Field(default_factory=list)
    driver_locations: List[DriverLocation] = Field(default_factory=list)
    playback: PlaybackState


class ControlRequest(BaseModel):
    action: str  # 'play', 'pause', 'seek', 'set_speed', 'load_session'
    speed: Optional[float] = None
    timestamp: Optional[str] = None
    session_key: Optional[int] = None
