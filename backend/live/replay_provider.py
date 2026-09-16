import time
import bisect
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .models import (
    DashboardFrame,
    SessionInfo,
    LeaderboardRow,
    DriverSectorTimes,
    DriverLocation,
    TrackStatus,
    WeatherInfo,
    PlaybackState,
)
from .session_provider import SessionDataProvider
from .openf1_client import OpenF1Client

logger = logging.getLogger(__name__)


def parse_iso_to_epoch(iso_str: str) -> float:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.timestamp()


def format_epoch_to_iso(epoch: float) -> str:
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return dt.isoformat()


def format_lap_time(seconds: Optional[float]) -> Optional[str]:
    if seconds is None or seconds <= 0:
        return None
    mins = int(seconds // 60)
    secs = seconds % 60
    if mins > 0:
        return f"{mins}:{secs:06.3f}"
    return f"{secs:06.3f}"


class ReplaySessionProvider(SessionDataProvider):
    """
    SessionDataProvider implementation that simulates a live session by replaying
    historical OpenF1 data at realistic or accelerated speeds.
    """

    def __init__(self, session_key: int = 9523, duration_minutes: int = 10, speed: float = 1.0):
        self.session_key = session_key
        self.duration_minutes = duration_minutes
        self.speed = speed
        self.is_playing = True
        self.client = OpenF1Client()

        # Raw & indexed data
        self.bundle: Dict[str, Any] = {}
        self.drivers_by_num: Dict[int, Dict[str, Any]] = {}
        self.locations_by_driver: Dict[int, List[Dict[str, Any]]] = {}
        self.positions_by_driver: Dict[int, List[Dict[str, Any]]] = {}
        self.intervals_by_driver: Dict[int, List[Dict[str, Any]]] = {}
        self.laps_by_driver: Dict[int, List[Dict[str, Any]]] = {}
        self.stints_by_driver: Dict[int, List[Dict[str, Any]]] = {}
        self.weather_events: List[Dict[str, Any]] = []
        self.race_control_events: List[Dict[str, Any]] = []

        # Timestamps (Epoch seconds)
        self.start_epoch: float = 0.0
        self.end_epoch: float = 0.0
        self.current_epoch: float = 0.0
        self.last_real_tick: float = time.monotonic()
        self.initialized = False

    async def initialize(self) -> None:
        self.bundle = await self.client.load_or_fetch_replay_bundle(
            session_key=self.session_key,
            duration_minutes=self.duration_minutes,
        )

        # Index drivers
        drivers = self.bundle.get("drivers", [])
        self.drivers_by_num = {d["driver_number"]: d for d in drivers}

        # Index locations per driver with timestamps
        self.locations_by_driver = {}
        for loc in self.bundle.get("locations", []):
            d_num = loc.get("driver_number")
            date_str = loc.get("date")
            if d_num is not None and date_str:
                loc_entry = {
                    "epoch": parse_iso_to_epoch(date_str),
                    "x": float(loc.get("x", 0)),
                    "y": float(loc.get("y", 0)),
                    "z": float(loc.get("z", 0)),
                }
                self.locations_by_driver.setdefault(d_num, []).append(loc_entry)

        for d_num in self.locations_by_driver:
            self.locations_by_driver[d_num].sort(key=lambda x: x["epoch"])

        # Index positions per driver
        self.positions_by_driver = {}
        for pos in self.bundle.get("positions", []):
            d_num = pos.get("driver_number")
            date_str = pos.get("date")
            if d_num is not None and date_str:
                self.positions_by_driver.setdefault(d_num, []).append({
                    "epoch": parse_iso_to_epoch(date_str),
                    "position": pos.get("position", 20),
                })
        for d_num in self.positions_by_driver:
            self.positions_by_driver[d_num].sort(key=lambda x: x["epoch"])

        # Index intervals per driver
        self.intervals_by_driver = {}
        for item in self.bundle.get("intervals", []):
            d_num = item.get("driver_number")
            date_str = item.get("date")
            if d_num is not None and date_str:
                self.intervals_by_driver.setdefault(d_num, []).append({
                    "epoch": parse_iso_to_epoch(date_str),
                    "gap_to_leader": item.get("gap_to_leader"),
                    "interval": item.get("interval"),
                })
        for d_num in self.intervals_by_driver:
            self.intervals_by_driver[d_num].sort(key=lambda x: x["epoch"])

        # Index laps per driver
        self.laps_by_driver = {}
        for lap in self.bundle.get("laps", []):
            d_num = lap.get("driver_number")
            date_str = lap.get("date_start")
            if d_num is not None and date_str:
                self.laps_by_driver.setdefault(d_num, []).append({
                    "epoch": parse_iso_to_epoch(date_str),
                    "lap_number": lap.get("lap_number", 1),
                    "lap_duration": lap.get("lap_duration"),
                    "s1": lap.get("duration_sector_1"),
                    "s2": lap.get("duration_sector_2"),
                    "s3": lap.get("duration_sector_3"),
                    "is_pit_out_lap": lap.get("is_pit_out_lap", False),
                })
        for d_num in self.laps_by_driver:
            self.laps_by_driver[d_num].sort(key=lambda x: x["epoch"])

        # Index stints per driver
        self.stints_by_driver = {}
        for stint in self.bundle.get("stints", []):
            d_num = stint.get("driver_number")
            if d_num is not None:
                self.stints_by_driver.setdefault(d_num, []).append({
                    "lap_start": stint.get("lap_start") or 1,
                    "lap_end": stint.get("lap_end") or 999,
                    "compound": stint.get("compound") or "UNKNOWN",
                    "tyre_age_at_start": stint.get("tyre_age_at_start") or 0,
                    "stint_number": stint.get("stint_number") or 1,
                })
        for d_num in self.stints_by_driver:
            self.stints_by_driver[d_num].sort(key=lambda x: x["lap_start"])

        # Weather & Race Control
        self.weather_events = [
            {**w, "epoch": parse_iso_to_epoch(w["date"])}
            for w in self.bundle.get("weather", [])
            if w.get("date")
        ]
        self.weather_events.sort(key=lambda x: x["epoch"])

        self.race_control_events = [
            {**rc, "epoch": parse_iso_to_epoch(rc["date"])}
            for rc in self.bundle.get("race_control", [])
            if rc.get("date")
        ]
        self.race_control_events.sort(key=lambda x: x["epoch"])

        self.start_epoch = parse_iso_to_epoch(self.bundle["start_time"])
        self.end_epoch = parse_iso_to_epoch(self.bundle["end_time"])
        self.current_epoch = self.start_epoch
        self.last_real_tick = time.monotonic()
        self.initialized = True
        logger.info(f"ReplaySessionProvider initialized for session {self.session_key}.")

    def _advance_clock(self) -> None:
        now_real = time.monotonic()
        delta_real = now_real - self.last_real_tick
        self.last_real_tick = now_real

        if self.is_playing and self.initialized:
            self.current_epoch += delta_real * self.speed
            if self.current_epoch > self.end_epoch:
                # Loop playback to start
                self.current_epoch = self.start_epoch

    async def get_current_frame(self) -> DashboardFrame:
        if not self.initialized:
            await self.initialize()

        self._advance_clock()
        curr_t = self.current_epoch

        # Build Weather
        weather_info = WeatherInfo()
        if self.weather_events:
            idx = bisect.bisect_right([w["epoch"] for w in self.weather_events], curr_t) - 1
            if idx >= 0:
                latest_w = self.weather_events[idx]
                weather_info = WeatherInfo(
                    air_temp=latest_w.get("air_temperature"),
                    track_temp=latest_w.get("track_temperature"),
                    humidity=latest_w.get("humidity"),
                    rainfall=latest_w.get("rainfall"),
                    wind_speed=latest_w.get("wind_speed"),
                    wind_direction=latest_w.get("wind_direction"),
                )

        # Build Track Status / Flags
        track_status = TrackStatus(status="1", flag="GREEN", message="TRACK CLEAR")
        if self.race_control_events:
            idx = bisect.bisect_right([rc["epoch"] for rc in self.race_control_events], curr_t) - 1
            if idx >= 0:
                rc = self.race_control_events[idx]
                flag = rc.get("flag", "GREEN") or "GREEN"
                msg = rc.get("message", "TRACK CLEAR") or ""
                cat = rc.get("category", "") or ""
                status_code = "1"
                if flag == "YELLOW":
                    status_code = "2"
                elif "SAFETY CAR" in msg.upper() or "SafetyCar" in cat:
                    status_code = "4"
                    flag = "SAFETY CAR"
                elif "VIRTUAL SAFETY CAR" in msg.upper() or "VSC" in msg.upper():
                    status_code = "6"
                    flag = "VSC"
                elif flag == "RED":
                    status_code = "5"
                elif flag == "CHEQUERED":
                    status_code = "1"
                track_status = TrackStatus(status=status_code, flag=flag, message=msg if msg else "TRACK CLEAR")

        # Build Leaderboard & Driver Locations
        leaderboard_rows: List[LeaderboardRow] = []
        driver_locations: List[DriverLocation] = []

        for d_num, driver_info in self.drivers_by_num.items():
            team_color = driver_info.get("team_colour", "00CED5") or "00CED5"
            if not team_color.startswith("#"):
                team_color = f"#{team_color}"
            code = driver_info.get("name_acronym") or f"D{d_num}"
            name = driver_info.get("broadcast_name") or driver_info.get("full_name") or f"Driver {d_num}"
            team = driver_info.get("team_name") or "F1 Team"
            headshot = driver_info.get("headshot_url")

            # Position
            pos = 20
            pos_list = self.positions_by_driver.get(d_num, [])
            if pos_list:
                idx = bisect.bisect_right([p["epoch"] for p in pos_list], curr_t) - 1
                if idx >= 0:
                    pos = pos_list[idx]["position"]

            # Intervals
            gap_to_leader = "+0.000" if pos == 1 else "+10.000"
            interval_str = "LEADER" if pos == 1 else "+1.000"
            inv_list = self.intervals_by_driver.get(d_num, [])
            if inv_list:
                idx = bisect.bisect_right([i["epoch"] for i in inv_list], curr_t) - 1
                if idx >= 0:
                    gap_val = inv_list[idx]["gap_to_leader"]
                    inv_val = inv_list[idx]["interval"]
                    if gap_val is not None:
                        gap_to_leader = f"+{gap_val:.3f}" if isinstance(gap_val, (int, float)) else str(gap_val)
                    if inv_val is not None:
                        interval_str = f"+{inv_val:.3f}" if isinstance(inv_val, (int, float)) else str(inv_val)

            # Laps
            curr_lap_num = 1
            last_lap_sec: Optional[float] = None
            best_lap_sec: Optional[float] = None
            s1_val: Optional[float] = None
            s2_val: Optional[float] = None
            s3_val: Optional[float] = None
            in_pit = False

            laps_list = self.laps_by_driver.get(d_num, [])
            if laps_list:
                idx = bisect.bisect_right([l["epoch"] for l in laps_list], curr_t) - 1
                if idx >= 0:
                    curr_lap_item = laps_list[idx]
                    curr_lap_num = curr_lap_item.get("lap_number") or 1
                    s1_val = curr_lap_item.get("s1")
                    s2_val = curr_lap_item.get("s2")
                    s3_val = curr_lap_item.get("s3")
                    in_pit = curr_lap_item.get("is_pit_out_lap", False)

                    # Compute last completed lap & best lap so far
                    for l in laps_list[: idx + 1]:
                        duration = l.get("lap_duration")
                        if duration and duration > 30.0:
                            last_lap_sec = duration
                            if best_lap_sec is None or duration < best_lap_sec:
                                best_lap_sec = duration

            # Tyre Stint
            compound = "UNKNOWN"
            tyre_age = 0
            pit_stops = 0
            stints_list = self.stints_by_driver.get(d_num, [])
            if stints_list:
                for s in stints_list:
                    l_start = s.get("lap_start") or 1
                    if l_start <= curr_lap_num:
                        compound = s.get("compound") or "UNKNOWN"
                        age_at_start = s.get("tyre_age_at_start") or 0
                        tyre_age = age_at_start + (curr_lap_num - l_start)
                        stint_num = s.get("stint_number") or 1
                        pit_stops = max(0, stint_num - 1)

            # Location (X, Y)
            locs = self.locations_by_driver.get(d_num, [])
            if locs:
                idx = bisect.bisect_right([loc["epoch"] for loc in locs], curr_t) - 1
                if idx >= 0:
                    pt = locs[idx]
                    driver_locations.append(
                        DriverLocation(
                            driver_number=d_num,
                            code=code,
                            team_color=team_color,
                            x=pt["x"],
                            y=pt["y"],
                            z=pt["z"],
                        )
                    )

            row = LeaderboardRow(
                position=pos,
                driver_number=d_num,
                code=code,
                name=name,
                team=team,
                team_color=team_color,
                headshot_url=headshot,
                gap_to_leader=gap_to_leader,
                interval=interval_str,
                last_lap_time=format_lap_time(last_lap_sec),
                best_lap_time=format_lap_time(best_lap_sec),
                current_lap=curr_lap_num,
                tyre_compound=compound,
                tyre_age=tyre_age,
                pit_stops=pit_stops,
                in_pit=in_pit,
                sectors=DriverSectorTimes(s1=s1_val, s2=s2_val, s3=s3_val),
            )
            leaderboard_rows.append(row)

        # Sort leaderboard by position
        leaderboard_rows.sort(key=lambda r: r.position)

        # Session metadata
        s_info = self.bundle.get("session_info", {})
        session_info = SessionInfo(
            session_key=self.session_key,
            session_name=s_info.get("session_name", "Race"),
            meeting_name=s_info.get("location") or s_info.get("country_name") or "Grand Prix",
            circuit_key=s_info.get("circuit_key"),
            circuit_short_name=s_info.get("circuit_short_name") or "Circuit",
            country_name=s_info.get("country_name") or "",
            year=s_info.get("year") or 2024,
            date_start=s_info.get("date_start"),
            date_end=s_info.get("date_end"),
        )

        # Playback state
        total_span = max(1.0, self.end_epoch - self.start_epoch)
        elapsed_span = max(0.0, min(total_span, curr_t - self.start_epoch))
        progress = (elapsed_span / total_span) * 100.0

        playback_state = PlaybackState(
            mode="replay",
            is_playing=self.is_playing,
            speed=self.speed,
            current_time=format_epoch_to_iso(curr_t),
            start_time=format_epoch_to_iso(self.start_epoch),
            end_time=format_epoch_to_iso(self.end_epoch),
            progress_pct=round(progress, 2),
        )

        return DashboardFrame(
            timestamp=format_epoch_to_iso(curr_t),
            session_info=session_info,
            track_status=track_status,
            weather=weather_info,
            leaderboard=leaderboard_rows,
            driver_locations=driver_locations,
            playback=playback_state,
        )

    async def play(self) -> None:
        self.is_playing = True
        self.last_real_tick = time.monotonic()

    async def pause(self) -> None:
        self.is_playing = False

    async def seek(self, target_iso_time: str) -> None:
        target_epoch = parse_iso_to_epoch(target_iso_time)
        self.current_epoch = max(self.start_epoch, min(self.end_epoch, target_epoch))
        self.last_real_tick = time.monotonic()

    async def set_speed(self, speed: float) -> None:
        self.speed = max(0.1, min(10.0, speed))
        self.last_real_tick = time.monotonic()

    def get_playback_state(self) -> PlaybackState:
        total_span = max(1.0, self.end_epoch - self.start_epoch)
        elapsed_span = max(0.0, min(total_span, self.current_epoch - self.start_epoch))
        progress = (elapsed_span / total_span) * 100.0

        return PlaybackState(
            mode="replay",
            is_playing=self.is_playing,
            speed=self.speed,
            current_time=format_epoch_to_iso(self.current_epoch),
            start_time=format_epoch_to_iso(self.start_epoch),
            end_time=format_epoch_to_iso(self.end_epoch),
            progress_pct=round(progress, 2),
        )

    async def cleanup(self) -> None:
        self.is_playing = False
