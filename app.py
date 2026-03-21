import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import fastf1
import polars as pl
import os


## HELPER METHODS

### Enable data chaching to reduce network load
if not os.path.exists('cache'):
    os.makedirs('cache')

fastf1.Cache.enable_cache('cache')

# Fetch the fastest lap
def get_fastest_lap(driver_code, session):
    laps = session.laps
    fastest_lap = laps.pick_drivers(driver_code).pick_fastest()

    return fastest_lap

# Fetch telemetry for a given lap
def get_telemetry_for_lap(lap):
    telemetry = lap.get_telemetry()
    return telemetry


## APPLICATION CODE
app = dash.Dash(__name__)

app.layout = html.Div(style={
    'backgroundColor': '#111111', 'color': '#00CED5', 'padding': '20px',
    },
    children=[

        html.H1("F1 Telemetry", style={'textAlign': 'center', 'color': "#00CED5"}),

        dcc.Store(id='session-store'),

        # Header
        html.Div(style={
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

        ]),
        
        dcc.Loading(
            id="loading-telemetry",
            type="graph",
            children=
            dcc.Graph(
                id='live-telemetry-graph',
                responsive=True,
                figure={
                    'data': [],
                    'layout': {
                        'title': 'Select a driver to view telemetry',
                        'plot_bgcolor': '#111111',
                        'paper_bgcolor': '#111111',
                        'font': {'color': '#00CED5'},
                        'xaxis': {
                            'gridcolor': '#333', 
                            'title': {'text': 'Distance (m)', 'font': {'color': '#00CED5'}},
                            },
                        'yaxis': {
                            'gridcolor': '#333', 
                            'title': {'text': 'Speed (km/h)', 'font': {'color': '#00CED5'}}
                            }
                    }   
                }
            ),
        ),
    ])

# Callbacks
# Update events based on chosen year
@app.callback(
        Output('event-dropdown', 'options'),
        Input('year-dropdown', 'value')
)
def update_events_dropdown(year):
    print(f"Updating Events Dropdown...")
    
    # Get Events for given year
    events = fastf1.get_event_schedule(year)
    options = []
    for index, row in events.iterrows():
        options.append(row.EventName)

    return options

# Update drivers based stored session
@app.callback(
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
        return [], None

# Sync all dropdown choices to store
@app.callback(
    Output('session-store', 'data'),
    Input('apply-btn', 'n_clicks'),
    State('year-dropdown', 'value'),
    State('event-dropdown', 'value'),
    State('session-dropdown', 'value'),
    State('driver-dropdown', 'value'),
    prevent_initial_call=True
)
def sync_to_store(n_clicks, year, event, session, driver):
    if not all([year, event, session, driver]):
        return dash.no_update
    
    return {
        'year': year, 
        'event': event, 
        'session': session, 
        'driver': driver
    }


# Update the graph
@app.callback(
    Output('live-telemetry-graph', 'figure'),
    Input('session-store', 'data'),
)
def update_graph(session_info):
    
    if not session_info:
        return dash.no_update
    
    # Reload session
    session = fastf1.get_session(session_info['year'], session_info['event'], session_info['session'])
    session.load(telemetry=True, laps=True, weather=False)
    
    driver = session_info['driver']

    # Get telemetry
    telemetry = get_telemetry_for_lap(get_fastest_lap(driver, session))
    if telemetry is None:
        return dash.no_update
    
    fig = go.Figure()
    # Draw graph    
    fig.add_trace(go.Scatter(
        x=telemetry['Distance'],
        y=telemetry['Speed'],
        name=f'Speed over Distance - {driver}',
        line={'color': '#00CED5'}
    ))

    fig.update_layout(
        title=f"Fastest Lap Telemetry: {driver}",
        template="plotly_dark",
        plot_bgcolor='#111111',
        paper_bgcolor='#111111',
        xaxis_title="Distance (m)",
        yaxis_title="Speed (kn/h)"
    )

    return fig

if __name__ == '__main__':
    app.run(debug=True)