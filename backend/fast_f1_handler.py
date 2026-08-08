from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import fastf1
import pandas as pd
    
app = FastAPI(title = "F1 Telemetry API", description = "API for fetching F1 telemetry data", version = "1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

fastf1.Cache.enable_cache('cache')  # Enable caching for FastF1 data

# Fetch the fastest lap for a given driver in a session
def get_fastest_lap(driver, session):
    laps = session.laps
    fastest_lap = laps.pick_drivers(driver).pick_fastest()

    return fastest_lap

# Format timedelta to a string representation
def format_time(td):
    if pd.isna(td):
        return "-"
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}" if minutes > 0 else f"{seconds:.3f}"

# Fetch and process the fastest lap data for selected drivers in a session
@app.get("/api/fastest-lap-data")
def fetch_historic_fastest_lap_data(
    year: int = Query(..., description="Year of the F1 season"),
    event: str = Query(..., description="Event name"),
    session: str = Query(..., description="Session type"),
    drivers: list[str] = Query(..., description="List of driver abbreviations")
):

    processed_data = {}
    existing_colors = set()

    try:

        
        session = fastf1.get_session(year, event, session)
        session.load(telemetry=True, laps=True, weather=False)

        for driver in drivers:
            # Get driver obj
            driver_obj = session.get_driver(driver)
            fastest_lap = get_fastest_lap(driver, session)

            # Ensure unique line style for each driver
            if driver_obj['TeamColor'] in existing_colors:
                line_style = 'dash'
            else:
                existing_colors.add(driver_obj['TeamColor'])
                line_style = 'solid'

            line_config = {'color': f'#{driver_obj["TeamColor"]}', 'dash': line_style}
            
            # Get telemetry
            
            if fastest_lap is None:
                print("Fastest lap not found for driver:", driver)
            else:
                telemetry = fastest_lap.get_telemetry()

            telemetry_points = telemetry[['Distance', 'Speed', 'Throttle', 'Brake', 'nGear']].to_dict(orient="records")
            
            processed_data[driver] = {
                'line_config': line_config,
                'telemetry': telemetry_points,
                # Extract and format the times directly from the `fastest_lap` object
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
