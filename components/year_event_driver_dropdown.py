from dash import html, dcc, callback, Input, Output, State
import dash
import fastf1
import pandas as pd

def year_event_driver_dropdown():

    layout = html.Div(style={
        'display': 'flex', 
        'flexWrap': 'wrap', 
        'gap': '20px', 
        'padding': '15px', 
        'backgroundColor': '#1a1a1a', 
        'borderRadius': '10px',
        'marginBottom': '20px',
        'alignItems': 'end'
        }, children=[

        # Year selection
        html.Div([
            html.Label("YEAR", style={'fontSize': '10px', 'display': 'block'}),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': str(yr), 'value': yr} for yr in range (2018, 2027)],
                value=2025,
                clearable=False,
                style={'width': '200px', 'color': 'black'}
            ),
        ]),

        # Event Selection
        html.Div([
            html.Label("GRAND PRIX", style={'fontSize': '10px', 'display': 'block'}),
            dcc.Dropdown(id='event-dropdown', placeholder="Select Event", options=[], clearable=False, style={'width': '200px', 'color': 'black'})
        ]),

        # Session Selection
        html.Div([
            html.Label("SESSION", style={'fontSize': '10px', 'display': 'block'}),
            dcc.Dropdown(
                id='session-dropdown', 
                options=[
                    {'label': 'Practice 1', 'value': 'FP1'},
                    {'label': 'Practice 2', 'value': 'FP2'},
                    {'label': 'Practice 3', 'value': 'FP3'},
                    {'label': 'Qualifying', 'value': 'Q'},
                    {'label': 'Race', 'value': 'R'}
                ], 
                placeholder="Select Session", 
                clearable=False, 
                style={'width': '120px', 'color': 'black'}
            )
        ]),

        # Driver Selection
        html.Div([
            html.Label("SELECT DRIVER", style={'color': '#00CED5', 'fontSize': '12px'}),
            dcc.Dropdown(
                id='driver-dropdown',
                options=[],
                placeholder="Select Driver",
                clearable=False,
                multi=True,
                style={'width': '200px', 'color': 'black'}
            ),
        ]),

        # Apply Selections
        html.Button('APPLY CHANGES', id='apply-btn', n_clicks=0, style={
            'backgroundColor': '#00CED5', 
            'color': '#111', 
            'border': 'none', 
            'padding': '10px 20px', 
            'fontWeight': 'bold',
            'cursor': 'pointer',
            'borderRadius': '5px'
        })
    ])

    return layout


# Update events based on chosen year
@callback(
    Output('event-dropdown', 'options'),
    Input('year-dropdown', 'value')
)
def update_events_dropdown(year):
    print(f"Updating Events Dropdown...")

    # Get Events for given year
    events = fastf1.get_event_schedule(year)
    now = pd.Timestamp.now(tz='UTC')
    options = []
    for index, row in events.iterrows():
        if pd.notna(row.Session5Date) and row.Session5Date < now:
            options.append(row.EventName)
    return options

# Update drivers based stored session
@callback(
    Output('driver-dropdown', 'options'),
    [Input('year-dropdown', 'value'),
    Input('event-dropdown', 'value'),
    Input('session-dropdown', 'value')]
)
def update_driver_dropdown(year, event, session_type):
    if not year or not event or not session_type:
        return []

    print(f"Pre-loading drivers for {event} {year}...")

    try:
        session = fastf1.get_session(year, event, session_type)
        session.load(laps=True, telemetry=False, weather=False, messages=False)

        driver_options = []
        for drv in session.drivers:
            info = session.get_driver(drv)
            driver_options.append({
                'label': f"{info['FullName']} ({info['Abbreviation']})", 
                'value': info['Abbreviation']
            })
        
        return driver_options

    except Exception as e:
        print(f"Error loading drivers: {e}")
        return []

# Sync all dropdown choices to store
@callback(
Output('session-store', 'data'),
Input('apply-btn', 'n_clicks'),
State('year-dropdown', 'value'),
State('event-dropdown', 'value'),
State('session-dropdown', 'value'),
State('driver-dropdown', 'value'),
prevent_initial_call=True
)
def sync_to_store(n_clicks, year, event, session, drivers):
    if not all([year, event, session, drivers]):
        return dash.no_update

    return {
        'year': year, 
        'event': event, 
        'session': session, 
        'drivers': drivers
    }