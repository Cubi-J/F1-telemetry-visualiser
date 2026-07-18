
import fastf1
import pandas as pd

# Fetch the fastest lap for a given driver in a session
def get_fastest_lap(driver, session):
    laps = session.laps
    fastest_lap = laps.pick_drivers(driver).pick_fastest()

    return fastest_lap


# Fetch telemetry for a given lap
def get_telemetry_for_lap(lap):
    telemetry = lap.get_telemetry()
    return telemetry

# Fetch and process the fastest lap data for selected drivers in a session
def fetch_historic_fastest_lap_data(session_info):
    processed_drivers = {}
    existing_colors = set()

    session = fastf1.get_session(session_info['year'], session_info['event'], session_info['session'])
    session.load(telemetry=True, laps=True, weather=False)

    for driver in session_info['drivers']:
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
        telemetry = get_telemetry_for_lap(fastest_lap)
        if telemetry is None:
            print("No telemetry data available for driver:", driver)
        
        processed_drivers[driver] = {
            'line_config': line_config,
            'telemetry': telemetry,
            # Extract and format the times directly from the `fastest_lap` object
            'timing_data': {
                'Driver': driver,
                'LapTime': format_time(fastest_lap['LapTime']),
                'Sector1': format_time(fastest_lap['Sector1Time']),
                'Sector2': format_time(fastest_lap['Sector2Time']),
                'Sector3': format_time(fastest_lap['Sector3Time']),
            }
        }

    return processed_drivers


def format_time(td):
    if pd.isna(td):
        return "-"
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}" if minutes > 0 else f"{seconds:.3f}"