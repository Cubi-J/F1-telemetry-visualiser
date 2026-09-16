import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
import fastf1
import pandas as pd

router = APIRouter(prefix="/api", tags=["historic"])

# Enable FastF1 disk caching in backend/cache
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

# In-memory caches to make repeated queries instant
_CATALOG_CACHE = {}
_DRIVERS_CACHE = {}


# ---------------------------------------------------------------------------
# CATALOG ENDPOINT: GET /api/f1-catalog
# ---------------------------------------------------------------------------
@router.get("/f1-catalog")
def get_f1_catalog(start_year: int = 2018, end_year: int = None):
    if end_year is None:
        end_year = datetime.date.today().year

    cache_key = f"{start_year}_{end_year}"
    if cache_key in _CATALOG_CACHE:
        return _CATALOG_CACHE[cache_key]

    years = list(range(end_year, start_year - 1, -1))
    seasons_data = {}

    try:
        for year in years:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            season_events = []

            for _, row in schedule.iterrows():
                event_name = row.get("EventName")
                if pd.isna(event_name) or not str(event_name).strip():
                    continue

                sessions = []
                for s_idx in range(1, 6):
                    s_name = row.get(f"Session{s_idx}")
                    if pd.notna(s_name) and str(s_name).strip():
                        sessions.append(str(s_name).strip())

                season_events.append({
                    "name": str(event_name).strip(),
                    "round": int(row.get("RoundNumber", 0)) if pd.notna(row.get("RoundNumber")) else 0,
                    "country": str(row.get("Country", "")).strip(),
                    "location": str(row.get("Location", "")).strip(),
                    "sessions": sessions
                })

            seasons_data[str(year)] = {
                "events": season_events
            }

        response = {
            "status": "success",
            "data": {
                "years": years,
                "seasons": seasons_data
            }
        }
        _CATALOG_CACHE[cache_key] = response
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load catalog: {str(e)}")


# ---------------------------------------------------------------------------
# DRIVERS ENDPOINT: GET /api/drivers
# ---------------------------------------------------------------------------
@router.get("/drivers")
def get_drivers(
    year: int = Query(..., description="Season year"),
    event: str = Query(..., description="Event name or location"),
    session: str = Query(..., description="Session name")
):
    """
    Returns participating drivers for the selected session.
    """
    cache_key = f"{year}_{event}_{session}"
    if cache_key in _DRIVERS_CACHE:
        return _DRIVERS_CACHE[cache_key]

    try:
        session_obj = fastf1.get_session(year, event, session)
        session_obj.load(telemetry=False, weather=False, messages=False)

        drivers_list = []
        if hasattr(session_obj, 'results') and session_obj.results is not None and not session_obj.results.empty:
            for _, row in session_obj.results.iterrows():
                abbr = str(row.get("Abbreviation", "")).strip()
                if not abbr or abbr.lower() == "nan":
                    continue
                team_color = str(row.get("TeamColor", "00CED5"))
                if pd.isna(team_color) or not team_color or team_color.lower() == "nan":
                    team_color = "00CED5"
                if not team_color.startswith("#"):
                    team_color = f"#{team_color}"

                drivers_list.append({
                    "code": abbr,
                    "name": str(row.get("FullName", abbr)),
                    "team": str(row.get("TeamName", "")),
                    "color": team_color
                })
        elif hasattr(session_obj, 'laps') and session_obj.laps is not None and not session_obj.laps.empty:
            for d in session_obj.laps['Driver'].dropna().unique():
                try:
                    d_info = session_obj.get_driver(d)
                    abbr = str(d_info.get("Abbreviation", d))
                    full_name = str(d_info.get("FullName", abbr))
                    team_name = str(d_info.get("TeamName", ""))
                    team_color = str(d_info.get("TeamColor", "00CED5"))
                    if pd.isna(team_color) or not team_color or str(team_color).lower() == "nan":
                        team_color = "00CED5"
                    if not team_color.startswith("#"):
                        team_color = f"#{team_color}"
                except Exception:
                    abbr = str(d)
                    full_name = str(d)
                    team_name = ""
                    team_color = "#00CED5"

                drivers_list.append({
                    "code": abbr,
                    "name": full_name,
                    "team": team_name,
                    "color": team_color
                })

        drivers_list.sort(key=lambda x: x["code"])
        res = {"status": "success", "data": drivers_list}
        _DRIVERS_CACHE[cache_key] = res
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load drivers: {str(e)}")


# ---------------------------------------------------------------------------
# FASTEST LAP TELEMETRY: GET /api/fastest-lap-data
# ---------------------------------------------------------------------------
def format_time(td):
    if pd.isna(td):
        return "-"
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}" if minutes > 0 else f"{seconds:.3f}"


@router.get("/fastest-lap-data")
def fetch_historic_fastest_lap_data(
    year: int = Query(..., description="Year of the F1 season"),
    event: str = Query(..., description="Event name"),
    session: str = Query(..., description="Session type"),
    drivers: list[str] = Query(..., description="List of driver abbreviations")
):
    processed_data = {}
    existing_colors = set()

    try:
        session_data = fastf1.get_session(year, event, session)
        session_data.load(telemetry=True, laps=True, weather=False)

        for driver in drivers:
            driver_obj = session_data.get_driver(driver)
            fastest_lap = session_data.laps.pick_drivers(driver).pick_fastest()

            if fastest_lap is None:
                print("Fastest lap not found for driver:", driver)
                continue

            telemetry = fastest_lap.get_telemetry()
            telemetry_points = telemetry[['Distance', 'Speed', 'Throttle', 'Brake', 'nGear']].to_dict(orient="records")

            if driver_obj['TeamColor'] in existing_colors:
                line_style = 'dash'
            else:
                existing_colors.add(driver_obj['TeamColor'])
                line_style = 'solid'

            line_config = {'color': f'#{driver_obj["TeamColor"]}', 'dash': line_style}

            processed_data[driver] = {
                'line_config': line_config,
                'telemetry': telemetry_points,
                'timing_data': {
                    'LapTime': format_time(fastest_lap['LapTime']),
                    'Sector1': format_time(fastest_lap['Sector1Time']),
                    'Sector2': format_time(fastest_lap['Sector2Time']),
                    'Sector3': format_time(fastest_lap['Sector3Time']),
                }
            }

        return {'status': 'success', 'data': processed_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
